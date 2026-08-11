#!/usr/bin/env python3
"""문서 정합 검사 — 눈으로는 안 보이고 grep 으로도 안 걸리는 것들.

**값어치가 확인된 검사만 둔다.** 두지 않는 것 — 사문화된 검사(어떤 입력에도 안 걸리는 것)와
유지비가 안 맞는 검사(손으로 적은 화이트리스트를 유지해야 하는 것).

구조 — 검사는 `@check` 로 등록한다. 등록하면 `--list` 에 뜨고,
`lint.test.py` 가 그 목록을 읽어 **픽스처 없는 검사를 실패로 만든다.**
검사를 더하고 테스트를 안 붙이는 길이 없다.

각 검사는 걸린 것과 함께 **본 대상 수**를 돌려준다. 대상이 0건이면 통과가 아니라
`대상 0건` 으로 따로 적는다 — 대상 0건과 전부 통과는 다른 것이다.

돌리는 법
  python3 scripts/lint.py                  repo 전체
  python3 scripts/lint.py --list           검사 목록 (JSON)
  python3 scripts/lint.py --only <id>      한 검사만 (여러 번 줄 수 있다)
  python3 scripts/lint.py --root <dir>     다른 루트에 대고 (`lint.test.py` 가 쓴다)
  python3 scripts/lint.py --json           결과를 JSON 으로
  python3 scripts/lint.py --strict-targets 대상 0건도 실패로 본다

exit code — **문서가 틀린 것과 검사기가 고장난 것을 구별한다.**
  0  통과
  1  문서가 틀렸다 (걸린 게 있다)
  2  사용법이 틀렸다 (없는 검사 id 등)
  3  **검사기 자체가 고장났다** — 검사가 예외를 냈거나 결과를 안 냈다.
     이때 판정은 믿을 수 없다. 문서가 맞는지와 무관하게 검사기를 먼저 고친다.
"""
import argparse
import glob
import json
import os
import re
import sys
import traceback
from difflib import SequenceMatcher
from fnmatch import fnmatchcase

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 표 구분선 — `|:--|:-:|--|`
SEP = re.compile(r'^\|[:\- |]+\|$')


# ── 검사 대상 범위 ──
# 두 범위가 있고 이유가 다르다.
#   INSTRUCTION — 런타임에 실리는 지시서. 절 이름·frontmatter 규약이 여기서만 뜻을 가진다.
#   RENDER      — 렌더되는 모든 문서. 깨진 표는 어느 문서에서든 문서를 깨뜨린다.
# `doc/` (설계 문서)은 렌더 범위에만 든다.
INSTRUCTION = ('plugins/**/*.md', 'guide/**/*.md', '.claude/rules/*.md',
               '.claude/skills/*/SKILL.md', 'README.md', 'CLAUDE.md')
RENDER = INSTRUCTION + ('doc/**/*.md',)

TPL = 'plugins/flow/project-template/doc/00.ref/03.templates'


class Result:
    """한 검사의 결과 — 걸린 것과 **본 대상 수**.

    `error` 가 채워지면 그 검사는 판정을 못 낸 것이다(고장). 통과도 실패도 아니다.
    """

    def __init__(self, unit='건'):
        self.unit = unit
        self.targets = 0
        self.findings = []
        self.error = None

    def fail(self, msg):
        self.findings.append(msg)


def broken(msg, unit='건'):
    """판정 대신 '검사기가 고장났다'를 돌려준다 — 크래시로 죽지 않는다."""
    r = Result(unit=unit)
    r.error = msg
    return r


class Check:
    def __init__(self, cid, title, why, fn):
        self.id, self.title, self.why, self.fn = cid, title, why, fn


CHECKS = []


def check(cid, title, why):
    """검사를 등록한다. 등록한 것은 `--list` 에 뜨고 테스트가 픽스처를 요구한다."""
    def deco(fn):
        if any(c.id == cid for c in CHECKS):
            raise SystemExit(f"검사 id 중복: {cid}")
        CHECKS.append(Check(cid, title, why, fn))
        return fn
    return deco


class Ctx:
    """검사가 파일을 읽는 창구. 루트를 갈아 끼울 수 있어야 테스트가 픽스처를 쓴다."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self._cache = {}

    def paths(self, *pats):
        out = set()
        for p in pats:
            for hit in glob.glob(os.path.join(self.root, p), recursive=True):
                if os.path.isfile(hit):
                    out.add(os.path.normpath(hit))
        return sorted(out)

    def render_files(self):
        return self.paths(*RENDER)

    def instruction_files(self):
        return self.paths(*INSTRUCTION)

    def commands(self):
        return self.paths('plugins/flow/commands/*.md')

    def skills(self):
        return self.paths('plugins/flow/skills/*/SKILL.md')

    def rel(self, p):
        return os.path.relpath(p, self.root).replace(os.sep, '/')

    def read(self, p):
        if p not in self._cache:
            with open(p, encoding='utf-8') as fh:
                self._cache[p] = fh.read()
        return self._cache[p]

    def lines(self, p):
        return self.read(p).split('\n')

    def tpl_dir(self, name):
        return os.path.join(self.root, TPL, name)


# ── 공통 도구 ──

def bar(line):
    r"""이스케이프한 `\|` 는 세지 않는다."""
    return line.replace('\\|', '').count('|')


def fenced_map(lines):
    """줄마다 '코드펜스 안인가' — 펜스 줄 자체도 True."""
    out, inside = [], False
    for l in lines:
        if l.lstrip().startswith('```'):
            out.append(True)
            inside = not inside
            continue
        out.append(inside)
    return out


def tables(lines, fenced=None):
    """(머리글 index, 본문 끝 index) 목록.

    머리글 다음 줄이 구분선인 것만 표다 — 그게 마크다운이 표로 렌더하는 조건이다.
    펜스 안은 렌더될 때 표가 아니라 글자라 대상이 아니다. 표 검사 넷 전부가 이걸 본다.
    """
    if fenced is None:
        fenced = fenced_map(lines)
    out, i = [], 0
    while i < len(lines):
        if (not fenced[i] and lines[i].startswith('|')
                and i + 1 < len(lines) and SEP.match(lines[i + 1])):
            j = i + 2
            while j < len(lines) and lines[j].startswith('|') and not fenced[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def norm(s):
    """절 이름에서 번호·괄호 주석을 뗀다 — `1. 사용 계약` → `사용 계약`."""
    s = re.sub(r'^\d+\.\s*', '', s)
    s = re.sub(r'\s*\(.*?\)\s*', '', s)
    return s.strip()


# ── 1. 표 열 수 ──
# 이스케이프 안 된 `|` 가 행을 깨뜨린다.
@check('table-columns', '표 열 수',
       '이스케이프 안 된 `|` 가 행을 깨뜨린다')
def _table_columns(ctx):
    r = Result(unit='표')
    for f in ctx.render_files():
        L = ctx.lines(f)
        for i, j in tables(L):
            r.targets += 1
            head = bar(L[i])
            for k in range(i + 2, j):
                if bar(L[k]) != head:
                    r.fail(f"표 열 수 {ctx.rel(f)}:{k+1} — 머리 {head-1}칸, "
                           f"이 행 {bar(L[k])-1}칸 (표 안의 `|` 는 `\\|` 로 escape)")
    return r


# ── 2. 끊긴 표 — 표 사이에 글이 껴 뒤 행이 고아가 됐나 ──
# 표 사이에 비-표 줄(문단·blockquote)이 끼면 뒤 행은 표가 아니라 파이프 문자열로 렌더된다.
# 열 수 검사는 끊긴 뒤 행을 아예 안 보므로 따로 본다.
@check('table-orphan-row', '끊긴 표 (고아 행)',
       '표 사이에 글이 껴 뒤 행이 표 밖으로 나간다')
def _table_orphan(ctx):
    r = Result(unit='표')
    for f in ctx.render_files():
        L = ctx.lines(f)
        fenced = fenced_map(L)
        for _, j in tables(L, fenced):
            r.targets += 1
            k = j
            while k < len(L) and not L[k].strip():
                k += 1
            if k >= len(L) or L[k].startswith('|'):
                continue
            m = k + 1
            while m < len(L) and L[m].strip():
                if L[m].startswith('|') and not fenced[m]:
                    nxt = L[m + 1] if m + 1 < len(L) else ''
                    # 구분선이 뒤따르면 **새 표의 머리글**이다 — 고아가 아니다
                    if not SEP.match(nxt):
                        r.fail(f"끊긴 표 {ctx.rel(f)}:{m+1} — 표 사이에 다른 줄이 끼어 "
                               f"이 행이 표 밖으로 나간다 (그 줄을 표 뒤로 옮긴다)")
                    break
                m += 1
    return r


# ── 3. 표 뒤 빈 줄 — 불릿·문단이 마지막 칸에 흡수되나 ──
# 표 마지막 행 다음 줄이 `-`·`*`·글자면 표 안으로 빨려 들어가 마지막 칸에 붙어 렌더된다.
# 고아 행 검사는 표 사이에 낀 것만 보고 이 경우를 안 본다.
@check('table-blank-line', '표 뒤 빈 줄',
       '표 바로 뒤 불릿·문단이 마지막 칸에 흡수된다')
def _table_blank_line(ctx):
    r = Result(unit='표')
    for f in ctx.render_files():
        L = ctx.lines(f)
        for _, j in tables(L):
            r.targets += 1
            if j >= len(L):
                continue
            nxt = L[j]
            if not nxt.strip() or nxt.lstrip().startswith('```'):
                continue
            if re.match(r'^\s*[-*]\s|^\S', nxt):
                r.fail(f"표 뒤 빈 줄 없음 {ctx.rel(f)}:{j+1} — 표 마지막 칸에 딸려 "
                       f"들어간다 ({nxt.strip()[:40]})")
    return r


# ── 4. 쪼개진 표 — 빈 줄로 끊겨 뒷조각이 머리글을 잃었나 ──
# 표 본문 → 빈 줄 → 다시 `|` 행인데 구분선이 없으면, 뒷조각은 머리글 없는 표로 깨져 렌더된다.
# 고아 행 검사는 표 사이에 **글이 낀** 경우만 보고 빈 줄 하나로 갈린 이 경우를 안 본다.
@check('table-split', '쪼개진 표 (머리글 상실)',
       '빈 줄로 끊겨 뒷조각이 머리글을 잃는다')
def _table_split(ctx):
    r = Result(unit='표')
    for f in ctx.render_files():
        L = ctx.lines(f)
        fenced = fenced_map(L)
        for _, j in tables(L, fenced):
            r.targets += 1
            k = j
            while k < len(L) and not L[k].strip():
                k += 1
            if not (j < k < len(L) and L[k].startswith('|') and not fenced[k]):
                continue
            nxt = L[k + 1] if k + 1 < len(L) else ''
            if not SEP.match(nxt):
                r.fail(f"쪼개진 표 {ctx.rel(f)}:{k+1} — 빈 줄로 끊겨 이 행부터 "
                       f"머리글이 없다 (빈 줄을 지운다)")
    return r


# ── 5. argument-hint 무따옴표 ──
# 안 감싸면 **파일이 통째로 안 뜬다.** yaml 파싱 검사와 따로 둔다 —
# 그쪽은 `import yaml` 이 실패하면 통째로 꺼진다. 여기서는 yaml 을 아예 안 쓴다.
@check('argument-hint-quoted', 'argument-hint 따옴표',
       '안 감싸면 커맨드 파일이 안 뜬다')
def _argument_hint(ctx):
    r = Result(unit='줄')
    for f in ctx.commands():
        for i, l in enumerate(ctx.lines(f)[:12], 1):
            m = re.match(r'^argument-hint:\s*(\S.*)$', l)
            if not m:
                continue
            r.targets += 1
            if m.group(1)[0] not in ("'", '"'):
                r.fail(f"argument-hint 무따옴표 {ctx.rel(f)}:{i} — {m.group(1)[:40]} "
                       f"(작은따옴표로 감싼다. 닫는 `]` 뒤에 무엇이 오면 파일이 안 뜬다)")
    return r


# ── topology 를 읽는 창구 ──
# 위상 정본이 없거나 깨진 것을 **이름으로 지목하는 것은 `topology-pending` 의 일이다.**
# 같은 실패를 다섯 검사가 다섯 번 적으면 무엇을 고쳐야 하는지 흐려진다.

TOPOLOGY = 'plugins/flow/flow.topology.json'


def _topo(ctx):
    p = os.path.join(ctx.root, TOPOLOGY)
    if not os.path.exists(p):
        return None
    try:
        t = json.loads(ctx.read(p))
    except json.JSONDecodeError:
        return None
    return t if isinstance(t, dict) else None


def _section(ctx, path, title):
    """`## <title>` 절의 본문. 없으면 None."""
    m = re.search(rf'^## {re.escape(title)}\s*$\n(.*?)(?=^## |\Z)',
                  ctx.read(path), re.S | re.M)
    return m.group(1) if m else None


def _table_rows(text):
    """(첫 칸, 줄 원문) — 구분선은 뺀다."""
    out = []
    for l in text.split('\n'):
        if not l.startswith('|') or SEP.match(l):
            continue
        first = l.strip('|').split('|')[0]
        out.append((re.sub(r'[`*]', '', first).strip(), l))
    return out


# 백틱으로 감싼 우리 이름 — `traceability` · `traceability/level`
NAME = re.compile(r'`([a-z][a-z0-9-]*(?:/[a-z0-9-]+)?)`')


def _agents(ctx):
    """에이전트 이름 — 배선 표에 `builder`·`gatekeeper` 처럼 함께 적힌다. 스킬이 아니지만 실재한다."""
    return {os.path.basename(p)[:-3] for p in ctx.paths('plugins/flow/agents/*.md')}


def _named_in_rows(text):
    """**표 행 안**의 이름만. 절의 산문은 배선이 아니라 설명이라 뺀다."""
    got = set()
    for _, line in _table_rows(text):
        got |= set(NAME.findall(line))
    return got


def _desc(ctx, path):
    """frontmatter 의 description. folded(`>-`) 도 이어 붙여 한 줄로.

    한 물리 줄만 읽으면 folded 에서는 `>-` 만 잡혀 **검사가 조용히 꺼진다.**
    """
    L = ctx.lines(path)
    if not L or L[0].strip() != '---':
        return None
    for i, l in enumerate(L[1:], 1):
        if l.strip() == '---':
            return None
        m = re.match(r'^description:\s*(.*)$', l)
        if not m:
            continue
        head = m.group(1).strip()
        if head not in ('>', '>-', '|', '|-'):
            return head
        out = []
        for nxt in L[i + 1:]:
            if nxt.strip() == '---' or not nxt.startswith('  '):
                break
            out.append(nxt.strip())
        return ' '.join(out)
    return None


# ── 출력 형식 ↔ 템플릿 왕복 ──
# 스킬의 `출력 형식` 절이 지시한 절 이름과 그 템플릿의 절이 어긋나면,
# 그대로 만든 문서가 `doc-verify` 채점에서 FAIL 이다. 그 인과가 실제로 있었다.
#
# 스킬↔템플릿 짝을 **스크립트 안에 손으로 열거하지 않는다** — 그러면 정본이 둘이다.
# 그게 diag-C 4절이 말하는 그 병이다 — 정본이 둘. 지금은 `flow.topology.json` 의
# `output_templates` 가 정본이고 검사기는 그걸 읽는다. 짝을 늘리는 비용이 데이터 한 줄이다.
#
#   "output_templates": {
#     "skills/code-review/references/layers.md": "06.review",                       ← 문서 한 편
#     "skills/theme-apply/references/apply.md": {"template": "15.theme",
#                                                "relation": "덧붙임"},             ← 남의 문서에 절을
#     "skills/doc-verify/references/scoring.md": {"relation": "콘솔"}                ← 문서가 아니다
#   }
#
# **관계를 나눈 이유** — 문서 한 편을 내는 것만 '템플릿의 필수 절이 다 있나'를 물을 수 있다.
# 덧붙이는 조각에 그걸 물으면 남의 문서의 필수 절까지 요구하게 된다. 그러나 이름 대조는 둘 다 받는다.
# `콘솔` 은 대조할 템플릿이 없다는 **선언**이다 — 짝을 안 적어서 조용히 꺼지는 것과 다르다.
#
# **`SKILL.md` 만 스캔하면 안 된다.** 출력 형식은 `references/` 조각에 있다 —
# SKILL.md 만 보면 템플릿이 생겨도 이 검사는 영구히 대상 0건이다.
OUT_SCAN = ('plugins/flow/skills/*/SKILL.md',
            'plugins/flow/skills/*/references/*.md',
            'plugins/flow/procedures/*/*.md')
RELATIONS = ('문서', '덧붙임', '콘솔')


def _out_candidates(ctx):
    """`## 출력 형식` 절을 가진 파일 — 스킬 본체·조각·절차 조각 전부."""
    return [p for p in ctx.paths(*OUT_SCAN) if '\n## 출력 형식' in ctx.read(p)]


def _out_decl(ctx):
    """{plugins/flow 기준 경로: (관계, [템플릿...])} — `$` 로 시작하는 키는 주석이다."""
    out = {}
    for rel, v in ((_topo(ctx) or {}).get('output_templates') or {}).items():
        if rel.startswith('$'):
            continue
        if isinstance(v, dict):
            rel_kind = v.get('relation') or '문서'
            tpl = v.get('template') or ''
        else:
            rel_kind, tpl = '문서', str(v)
        out[rel] = (rel_kind, [x.strip() for x in tpl.split(',') if x.strip()])
    return out


def _declared(ctx, relations=('문서',)):
    """(파일 경로, plugins/flow 기준 경로, [템플릿...]) — 그 관계로 짝지은 것만."""
    out = []
    for rel, (kind, tpls) in sorted(_out_decl(ctx).items()):
        p = os.path.normpath(os.path.join(ctx.root, 'plugins/flow', rel))
        if kind in relations and tpls and os.path.isfile(p):
            out.append((p, rel, tpls))
    return out


def _out_sections(ctx, p):
    """`출력 형식` 절의 펜스 안 `## ` 절 이름들 — 스킬이 만들라고 지시한 절."""
    got, inside, fence = [], False, False
    for l in ctx.lines(p):
        if l.lstrip().startswith('```'):
            fence = not fence
            continue
        if not fence and l.startswith('## '):
            inside = l[3:].strip() == '출력 형식'
            continue
        if inside and fence and l.startswith('## '):
            got.append(norm(re.sub(r'\s{2,}.*', '', l[3:].strip())))
    return got


def _out_blocks(ctx, p):
    """`출력 형식` 절의 펜스 블록 본문들 — 펜스 밖 `## ` 만 절 경계다."""
    out, inside, fence, cur = [], False, False, None
    for l in ctx.lines(p):
        if l.lstrip().startswith('```'):
            if not fence and inside:
                cur = []
            elif fence and cur is not None:
                out.append('\n'.join(cur))
                cur = None
            fence = not fence
            continue
        if not fence and l.startswith('## '):
            inside = l[3:].strip() == '출력 형식'
            continue
        if cur is not None:
            cur.append(l)
    return out


def _tpl_sections(ctx, *names):
    """템플릿의 절 이름 — 조건 표기·등급 표기를 떼고 이름만."""
    out = set()
    for n in names:
        for f in sorted(glob.glob(os.path.join(ctx.tpl_dir(n), '*.md'))):
            for l in ctx.lines(f):
                if re.match(r'^#{2,3} ', l):
                    x = re.sub(r'\s*\*\*\[.*', '', re.sub(r'^#+\s*', '', l)).strip()
                    out.add(norm(x).replace('*', '').strip())
    return out


def _tpl_required(ctx, name):
    """템플릿의 필수 절 → 등급."""
    req = {}
    for f in sorted(glob.glob(os.path.join(ctx.tpl_dir(name), '*.md'))):
        for l in ctx.lines(f):
            m = re.search(r'^##\s*(.+?)\s*\*\*\[(진행 필수|문서 필수)\]\*\*', l)
            if m:
                req[re.sub(r'^\d+\.\s*', '', m.group(1).strip())] = m.group(2)
    return req


@check('output-sections-exist', '출력 형식 절이 템플릿에 있나',
       '스킬이 이름을 지어내면 생성 문서가 채점에서 미등재다')
def _output_sections_exist(ctx):
    r = Result(unit='절')
    decl = _out_decl(ctx)
    for rel, (kind, tpls) in sorted(decl.items()):
        if not os.path.isfile(os.path.normpath(os.path.join(ctx.root, 'plugins/flow', rel))):
            r.targets += 1
            r.fail(f"낡은 짝 선언 — `output_templates` 의 `{rel}` 파일이 없다 "
                   f"(조각을 옮겼으면 선언도 옮긴다)")
        if kind not in RELATIONS:
            r.targets += 1
            r.fail(f"관계 이름 {rel} — `{kind}` (하나여야 한다: {' · '.join(RELATIONS)})")
        elif kind != '콘솔' and not tpls:
            r.targets += 1
            r.fail(f"템플릿 없음 {rel} — 관계가 `{kind}` 인데 `template` 이 비었다")

    paired = set(decl)
    for p, rel, tpls in _declared(ctx, ('문서', '덧붙임')):
        known = _tpl_sections(ctx, *tpls)
        for sec in _out_sections(ctx, p):
            r.targets += 1
            if sec not in known:
                r.fail(f"출력 형식 미등재 {ctx.rel(p)} — `{sec}` 이 템플릿"
                       f"({'·'.join(tpls)})에 없다 "
                       f"(템플릿이 기준이다 — 이름을 맞추거나 템플릿에 절을 추가한다)")

    # 짝을 안 적으면 이 검사가 조용히 꺼진다. **문서 한 편을 내는 출력 형식**만 문다 —
    # 콘솔 출력이나 남의 문서에 덧붙이는 조각은 대조할 템플릿이 없는 게 정상이다.
    for p in _out_candidates(ctx):
        rel = os.path.relpath(p, os.path.join(ctx.root, 'plugins/flow')).replace(os.sep, '/')
        if rel in paired or not _out_sections(ctx, p):
            continue
        r.targets += 1
        r.fail(f"짝 미선언 {ctx.rel(p)} — 출력 형식이 `## ` 절로 문서 한 편을 내는데 "
               f"`flow.topology.json` 의 `output_templates` 에 템플릿이 없다 "
               f"(대조할 기준이 없으면 이 검사가 꺼진다)")
    return r


@check('output-required-sections', '템플릿 필수 절이 출력 형식에 있나',
       '이름 대조만으로는 빠진 절을 못 본다')
def _output_required(ctx):
    r = Result(unit='필수 절')
    for p, name, tpls in _declared(ctx):
        name = ctx.rel(p)
        blocks = _out_blocks(ctx, p)
        for idx, t in enumerate(tpls):
            req = _tpl_required(ctx, t)
            if idx >= len(blocks):
                if req:
                    r.targets += len(req)
                    r.fail(f"왕복 {name} → {t} — 출력 형식에 코드블록 {idx} 가 없다 "
                           f"(`output-template` 순서와 블록 순서가 짝이다)")
                continue
            got = {norm(l[3:].strip()) for l in blocks[idx].split('\n')
                   if l.startswith('## ')}
            for sec, grade in req.items():
                r.targets += 1
                if norm(sec) not in got:
                    r.fail(f"왕복 {name} → {t} — 출력 형식에 `{sec}`[{grade}] 가 없다 "
                           f"(그대로 만들면 채점에서 FAIL 이다)")
    return r


# ── 규약 사본 ──
# 정본이 둘이 되면 한쪽만 고쳐진다. 이걸 기계로 지키는 유일한 장치다.
#
# **대상이 `SKILL.md` 14개가 아니다.** `ctx.skills()` 만 돌면 그 14개는 대부분 라우터다. 규약 내용은
# `references/` 조각으로 내렸으므로 그 14개는 대부분 라우터고, **조각 35개(약 1,900줄, 이 층의
# 82%)와 커맨드·절차 본문이 검사 밖**이었다 — 사본은 거기 살아 있다.
#
# **지시 층끼리는 대조하지 않는다.** 커맨드·절차 본문은 커맨드마다 자기 게이트·경계를 선언해야
# 해서 같은 문장이 겹치는 것이 정상이다(`내용 — 없다…` 가 네 커맨드에 있다). 게다가 둘 다 정본을
# **이름으로 가리키는** 정상 인용까지 사본으로 잡힌다(`publish` ↔ `verify` 의 위임 인용이 실측 예다).
# 잡아야 하는 것은 **규약(스킬 본체·조각)이 두 곳에 사는 것**과 **지시 층이 규약을 베낀 것**이다.
DUP_RATIO = 0.85
DUP_CANON = ('plugins/flow/skills/*/SKILL.md', 'plugins/flow/skills/*/references/*.md')
DUP_INSTRUCTION = ('plugins/flow/commands/*.md', 'plugins/flow/procedures/*/*.md')


def _outside(ctx, p):
    out, fence = [], False
    for i, l in enumerate(ctx.lines(p), 1):
        if l.lstrip().startswith('```'):
            fence = not fence
            continue
        if not fence:
            out.append((i, l))
    return out


def _nz(s):
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', s)


@check('skill-duplication', '규약 사본 (스킬·조각·커맨드)',
       '정본이 둘이 되면 한쪽만 고쳐진다')
def _skill_duplication(ctx):
    r = Result(unit='문서')
    canon = set(ctx.paths(*DUP_CANON))
    src = {}
    for p in sorted(canon | set(ctx.paths(*DUP_INSTRUCTION))):
        lines = [(i, _nz(re.sub(r'\s+', ' ', re.sub(r'[`*|]', '', l).strip(' -'))))
                 for i, l in _outside(ctx, p)
                 if l.strip().startswith(('- ', '| ')) and len(l.strip()) > 34]
        if lines:
            src[p] = lines
            r.targets += 1

    keys = sorted(src)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a not in canon and b not in canon:
                continue                       # 지시 층끼리는 대조하지 않는다 (위 주석)
            for ia, x in src[a]:
                for ib, y in src[b]:
                    # 길이만으로 상한이 정해진다 — ratio ≤ 2·min/(len+len)
                    if 2 * min(len(x), len(y)) < DUP_RATIO * (len(x) + len(y)):
                        continue
                    if SequenceMatcher(None, x, y).ratio() >= DUP_RATIO:
                        r.fail(f"규약 사본 {ctx.rel(a)}:{ia} ↔ {ctx.rel(b)}:{ib} — {x[:44]} "
                               f"(정본 하나를 정하고 다른 쪽은 이름으로 가리킨다)")
    return r


# ── 절 이름에 번호·라벨이 붙었나 ──
# 절을 하나 더하면 밖에서 번호로 가리킨 줄이 조용히 어긋난다.
# 산문·프롬프트 안의 번호는 대상이 아니다 — `N단계` 는 순서가 뜻이다.
# 템플릿(`03.templates/`)은 사람이 절 번호로 자리를 찾는 골격이라 뺀다.
LABELED = re.compile(r'^#{2,4}\s+(?:[0-9]+\s*[.)]|[①-⑳]|절차\s+[A-Z0-9])')
HEADING = re.compile(r'^#{2,4}\s+\S')


@check('section-label', '절 이름 번호·라벨 금지',
       '절을 하나 더하면 번호로 가리킨 참조가 조용히 어긋난다')
def _section_label(ctx):
    r = Result(unit='절')
    for f in ctx.instruction_files():
        rel = ctx.rel(f)
        if os.path.basename(f) == 'CLAUDE.md' or 'plugin-authoring' in rel or '03.templates' in rel:
            continue
        L = ctx.lines(f)
        fenced = fenced_map(L)
        for i, l in enumerate(L, 1):
            if fenced[i - 1] or not HEADING.match(l):
                continue
            r.targets += 1
            if LABELED.match(l) and '단계' not in l:
                r.fail(f"번호·라벨 절 {rel}:{i} — {l.strip()[:50]}  (이름만 쓴다)")
    return r


# ── 생성물 ↔ 정본 대조 ──
# 정본을 JSON 으로 내린 것은 손 동기화를 **없앤** 게 아니라 **검출기가 지키는 관계**로 바꾼 것이다.
# 검출기 실행이 약속이면 손 동기화가 데이터 층에서 반복된다 — 그래서 이 검사가 CI 에서 돈다.

@check('generated-up-to-date', '생성물 ↔ 정본 대조',
       '생성물을 손으로 고치는 것 (설계 "강제 지점" 표 · 리뷰 H3)')
def _generated_up_to_date(ctx):
    r = Result(unit='생성 자리')
    try:
        import gen_docs
    except Exception as e:
        return broken(f"gen-docs 를 불러올 수 없다 — {type(e).__name__}: {e}")

    # 정본이 없는 루트(픽스처 일부)에서는 대상 0건이다 — 통과라고 말하지 않는다
    if not os.path.exists(os.path.join(ctx.root, gen_docs.GUARD_RULES)):
        return r
    try:
        bad = gen_docs.check(ctx.root)
    except Exception as e:
        # 정본을 못 읽으면 생성물이 맞는지 **모른다**. 통과로 세면 안 된다
        return broken(f"정본을 읽을 수 없어 대조를 못 했다 — {type(e).__name__}: {e}")
    r.targets = len(gen_docs.BLOCKS) + 2          # 마커 블록들 + 매니페스트 description 둘
    for x in bad:
        r.fail(f"생성물 어긋남 — {x}")
    return r


# ── 셸 가드 머리말 ↔ 셸 본문 ──
# 차단 목록의 정본이 둘로 갈렸다(JSON 단순 규칙 / 셸 예외 로직). 갈라진 대가는 셸 쪽이 낡는 것이고,
# 그 병만 기계로 막는다 — 머리말이 규칙을 선언하고 본문이 `@rule` 로 표시하면 둘을 대조할 수 있다.

@check('shell-guard-header', '셸 가드 머리말 ↔ 본문',
       '갈라진 정본 중 셸 쪽이 낡는 것 (설계 "guard 데이터화는 단순 규칙까지다")')
def _shell_guard_header(ctx):
    r = Result(unit='셸 규칙')
    try:
        import gen_docs
    except Exception as e:
        return broken(f"gen-docs 를 불러올 수 없다 — {type(e).__name__}: {e}")

    p = os.path.join(ctx.root, gen_docs.GUARD_SH)
    if not os.path.exists(p):
        return r
    try:
        _, rules, limits, marks = gen_docs.shell_rules(ctx.root)
    except ValueError as e:
        # 형식이 깨진 것은 **문서 위반**이다(검사기 고장이 아니다) — 고칠 사람이 있다
        r.targets = 1
        r.fail(f"머리말 형식 {gen_docs.GUARD_SH} — {e}")
        return r

    declared = [x['id'] for x in rules]
    r.targets = len(declared) + len(limits)
    dup = {x for x in declared if declared.count(x) > 1}
    if dup:
        r.fail(f"셸 규칙 id 중복 — {', '.join(sorted(dup))}")
    for rid in declared:
        if rid not in marks:
            r.fail(f"머리말에만 있는 셸 규칙 `{rid}` — 본문에 `# @rule {rid}` 표시가 없다 "
                   f"(구현을 지웠나, 머리말이 낡았나)")
    for rid in sorted(set(marks)):
        if rid not in declared:
            r.fail(f"본문에만 있는 셸 규칙 `{rid}` — 머리말 `@flow-shell-rules` 에 없어서 "
                   f"문서 차단표에 실리지 않는다")
    # 한계는 **여기 적지 않는다.** 정본은 `guard-rules.json` 의 `limits` 고,
    # 겹침은 `limits-single-canon` 이 본다. 여기서는 셸에 남는 것만 막는다.
    if limits:
        r.fail(f"머리말에 `limit:` 줄이 {len(limits)}개 있다 — 한계의 정본은 "
               f"`guard-rules.json` 의 `limits` 다. 여기 두면 정본이 둘이 되고 "
               f"생성 표에 두 번 실린다 (실제로 6행이 겹치고 한 줄은 낡았다)")
    return r


# ── 두 매니페스트의 version 일치 ──
# 어긋난 채 올리면 **한쪽만 바뀌는데 스크립트는 성공했다고 말한다.** 설치측은 marketplace.json 을
# 보므로 업데이트가 전달되지 않는다. description 은 생성물이라 위 검사가 본다.

@check('manifest-version-parity', '두 매니페스트 version 일치',
       '어긋난 채 버전을 올리면 설치측에 업데이트가 전달되지 않는다')
def _manifest_parity(ctx):
    r = Result(unit='매니페스트')
    pj = os.path.join(ctx.root, 'plugins/flow/.claude-plugin/plugin.json')
    mp = os.path.join(ctx.root, '.claude-plugin/marketplace.json')
    if not (os.path.exists(pj) and os.path.exists(mp)):
        return r
    r.targets = 2
    try:
        a = json.loads(ctx.read(pj))
        b = json.loads(ctx.read(mp))
    except json.JSONDecodeError as e:
        r.fail(f"매니페스트 JSON 파싱 실패 — {e}")
        return r
    hit = next((x for x in b.get('plugins') or [] if x.get('name') == 'flow'), None)
    if hit is None:
        r.fail("marketplace.json 에 name=flow 항목이 없다")
        return r
    if a.get('version') != hit.get('version'):
        r.fail(f"version 어긋남 — plugin.json={a.get('version')} · "
               f"marketplace.json={hit.get('version')} (`scripts/bump-version.sh` 로 함께 올린다)")
    if not re.match(r'^\d+\.\d+\.\d+$', str(a.get('version') or '')):
        r.fail(f"version 이 semver 가 아니다 — {a.get('version')}")
    return r


# ── topology 의 '빈 것'과 '없는 것' ──
# 다른 층이 아직 안 채운 키를 `null` 로 두는 것과 키가 아예 없는 것은 다르다.
# 구별할 장치가 없으면 '아직'과 '까먹음'이 같아 보인다 — 그래서 pending 목록과 대조한다.
TOPO_CMD_KEYS = ('order', 'phase', 'after', 'next', 'entry', 'exit', 'loads', 'procedures')
TOPO_ENTRY_KEYS = ('machine', 'content', 'promise')
# `exit` 는 `content` 만이다. `machine` 은 훅이 도구 호출마다 보는 것이라 판정 시점이 도구
# 호출이고, `promise` 는 판정하는 자가 없는 상시 규칙이라 시점이 없다 — 없는 시점을 적으라
# 요구하면 빈 껍데기가 늘고, 그 껍데기가 다시 '적혀 있으니 있는 것'으로 읽힌다.
TOPO_EXIT_KEYS = ('content',)


@check('topology-pending', 'topology 빈 키 ↔ pending 목록',
       "'아직 안 채움'과 '키를 빠뜨림'을 구별한다")
def _topology_pending(ctx):
    r = Result(unit='커맨드')
    p = os.path.join(ctx.root, 'plugins/flow/flow.topology.json')
    if not os.path.exists(p):
        return r
    try:
        t = json.loads(ctx.read(p))
    except json.JSONDecodeError as e:
        r.targets = 1
        r.fail(f"flow.topology.json 파싱 실패 — {e}")
        return r

    pending = [str(x) for x in (t.get('pending') or [])]

    def allowed(dotted):
        return any(fnmatchcase(dotted, pat) for pat in pending)

    cmds = t.get('commands')
    if not isinstance(cmds, dict) or not cmds:
        r.targets = 1
        r.fail("commands 절이 없거나 비었다 — 위상 정본이 비면 게이트가 읽을 것이 없다")
        return r

    for name, c in cmds.items():
        r.targets += 1
        if not isinstance(c, dict):
            r.fail(f"commands.{name} 이 객체가 아니다")
            continue
        for k in TOPO_CMD_KEYS:
            dotted = f"commands.{name}.{k}"
            if k not in c:
                r.fail(f"키가 없다 — {dotted} "
                       f"(아직 안 채운 것이면 `null` 로 두고 pending 에 적는다. "
                       f"없는 것과 빈 것을 구별해야 한다)")
            elif c[k] is None and not allowed(dotted):
                r.fail(f"`null` 인데 pending 에 없다 — {dotted} "
                       f"(채우거나 pending 에 적는다)")
        for slot, keys, lab in (('entry', TOPO_ENTRY_KEYS, '진입'),
                                ('exit', TOPO_EXIT_KEYS, '퇴장')):
            s = c.get(slot)
            if isinstance(s, dict):
                for k in keys:
                    if k not in s:
                        r.fail(f"{lab} 조건 등급이 빠졌다 — commands.{name}.{slot}.{k} "
                               f"(없는 등급은 빈 배열로 적는다. 등급을 섞지 않는 것이 "
                               f"이 파일의 일이다)")
                for k in s:
                    if k not in keys and not k.startswith('$'):
                        r.fail(f"{lab} 조건에 없는 등급 — commands.{name}.{slot}.{k} "
                               f"(쓸 수 있는 것은 {' · '.join(keys)} 뿐이다)")
            elif slot in c:
                r.fail(f"commands.{name}.{slot} 이 객체가 아니다")

    # pending 이 가리키는 자리가 실제로 있나 — 낡은 pending 은 '아직'을 영구히 정당화한다
    for pat in pending:
        if pat.startswith('commands.'):
            if not any(fnmatchcase(f"commands.{n}.{k}", pat)
                       for n in cmds for k in TOPO_CMD_KEYS):
                r.fail(f"pending `{pat}` 이 가리키는 자리가 없다 — 채워졌으면 pending 에서 지운다")
        elif pat not in t:
            r.fail(f"pending `{pat}` 이 가리키는 최상위 키가 없다")
    return r


# ── 커맨드 `## 연결` ↔ topology `loads` ──
# 여기가 가장 어긋나기 쉬운 자리다 — `## 연결` 절이 본문과 어긋나는데 **존재 검사는 세 줄의
# 존재만 봤다**. 존재 검사는 어긋남을 못 본다. 그래서 정본과 낱낱이 대조한다.
#
# `modes` 가 있으면 모드마다 한 행이다 — 모드를 합쳐 적으면 "어느 모드에서 무엇을 싣나"가 사라진다.
# `conditional` 은 **적히기만 하면 안 되고 조건이 같은 줄에 있어야 한다** — 조건이 없으면
# 늘 읽는 것과 구별되지 않아서, 순수 신규 구현에서도 다 읽게 된다.

def _names(xs, cap=6):
    """이름 목록을 한 줄로 — 길면 앞부분만 적고 몇 개 더인지 밝힌다(조용히 자르지 않는다)."""
    head = ' · '.join(f'`{x}`' for x in xs[:cap])
    return head if len(xs) <= cap else f"{head} 외 {len(xs) - cap}건"


def _loads_rows(loads):
    """loads 를 행 단위로 정규화 — [(행 이름 또는 None, 늘 싣는 것, {조건부: 조건})]."""
    if not isinstance(loads, dict):
        return []

    def one(d):
        always = set(d.get('skills') or []) | set(d.get('fragments') or [])
        cond = dict(d.get('conditional') or {})
        cond.update(d.get('conditional_skills') or {})
        return always, cond

    if loads.get('modes'):
        return [(m, *one(v or {})) for m, v in loads['modes'].items()]
    return [(None, *one(loads))]


@check('command-loads-parity', '커맨드 연결 절 ↔ topology loads',
       '연결 절이 본문과 어긋나는 것 — 존재 검사는 그걸 못 본다')
def _command_loads_parity(ctx):
    r = Result(unit='배선')
    t = _topo(ctx)
    if not t:
        return r
    skills = t.get('skills') or {}
    ours = set(skills) | {f"{s}/{f}" for s, v in skills.items()
                          for f in ((v or {}).get('fragments') or [])}

    for name, c in (t.get('commands') or {}).items():
        p = os.path.join(ctx.root, f'plugins/flow/commands/{name}.md')
        rows = _loads_rows((c or {}).get('loads'))
        if not os.path.isfile(p) or not rows:
            continue
        sec = _section(ctx, p, '연결')
        if sec is None:
            r.targets += 1
            r.fail(f"연결 절 없음 {ctx.rel(p)} — `## 연결` 이 없어 topology 의 "
                   f"`loads` 를 대조할 자리가 없다")
            continue
        table = _table_rows(sec)

        for mode, always, cond in rows:
            if mode is None:
                scope, tag = sec, ''
            else:
                hit = [l for lab, l in table if lab == mode]
                if not hit:
                    r.targets += 1
                    r.fail(f"모드 행 없음 {ctx.rel(p)} — `{mode}` 행이 `## 연결` 에 없다 "
                           f"(topology 가 `loads.modes` 로 갈랐으면 본문도 모드별로 적는다)")
                    continue
                scope, tag = '\n'.join(hit), f"[{mode}] "
            named = set(NAME.findall(scope))
            # 한 뿌리에서 나온 어긋남은 한 줄로 모은다 — 같은 표 한 칸이 열 줄을 내면 읽지 않는다
            miss, cmiss, unmarked, extra, unknown = [], [], [], [], []

            for x in sorted(always):
                r.targets += 1
                if x not in named:
                    miss.append(x)
            for x, why in sorted(cond.items()):
                r.targets += 1
                line = next((l for l in scope.split('\n') if f'`{x}`' in l), None)
                if line is None:
                    cmiss.append(x)
                elif why not in line:
                    unmarked.append(f"{x}({why})")
            for x in sorted(named & ours):
                if x not in always and x not in cond:
                    r.targets += 1
                    extra.append(x)

            # **실재하지 않는 이름도 잡는다.** 예전에는 `named & ours` 라 실재 스킬일 때만
            # 걸렸고 `zzz-fake` 같은 오타·환각은 조용히 통과했다.
            # 배선 표는 **읽을 것의 목록**이라, 없는 이름은 그 자리에서 아무것도 안 읽힌다.
            #
            # 표 행만 본다 — 절의 산문은 배선이 아니라 설명이고, 거기까지 잡으면
            # `default-reference` 의 `delegation` 조각 같은 정상 서술이 오탐이 된다.
            known = ours | _agents(ctx)
            for x in sorted(_named_in_rows(scope) - known):
                r.targets += 1
                if x not in always and x not in cond:
                    unknown.append(x)

            if miss:
                r.fail(f"연결 누락 {ctx.rel(p)} — {tag}topology 가 싣는다고 적은 "
                       f"{_names(miss)} 가 `## 연결` 에 없다")
            if cmiss:
                r.fail(f"연결 누락 {ctx.rel(p)} — {tag}조건부 {_names(cmiss)} 가 "
                       f"`## 연결` 에 없다 (조건부도 적는다 — 안 적으면 안 읽는 것으로 읽힌다)")
            if unmarked:
                r.fail(f"조건 미표기 {ctx.rel(p)} — {tag}{_names(unmarked)} 를 조건 없이 "
                       f"적었다 (늘 읽는 것과 구별되지 않아 순수 신규에서도 다 읽게 된다. "
                       f"이름 옆 같은 줄에 조건을 적는다)")
            if extra:
                r.fail(f"연결 초과 {ctx.rel(p)} — {tag}{_names(extra)} 는 topology 의 "
                       f"`loads` 에 없다 (본문이 배선을 발명했다 — 정본에 먼저 적는다)")
            if unknown:
                r.fail(f"없는 이름 {ctx.rel(p)} — {tag}{_names(unknown)} 는 스킬·조각·"
                       f"에이전트 어디에도 없다 (오타나 환각이다. 그 자리에서는 "
                       f"아무것도 안 읽힌다 — 매 턴 실리는 거짓말이 된다)")
    return r


# ── 내용 조건을 두 시점에서 모은다 ──
# **`entry.content` 만 보면 안 된다.** 내용 조건 5개는 전부 퇴장 조건이라 `exit.content` 로
# 내려갔다(재설계 D5·T4). 여기를 `entry` 로만 두면 아래 검사들이 **대상 0건으로 조용히
# 통과한다** — 그게 사문화다. 두 자리를 union 으로 본다.
def _content_items(c):
    """[(시점, 항목)] — 시점은 'entry' 또는 'exit'."""
    out = []
    for slot in ('entry', 'exit'):
        for item in ((c or {}).get(slot) or {}).get('content') or []:
            out.append((slot, item))
    return out


# ── gatekeeper 위임 지시가 있나 ──
# 게이트를 여러 곳이 약속하고 실제로 거는 곳이 하나면 그것은 게이트가 아니다.
# 내용 조건은 **gatekeeper 가 판정하는 등급**이다. 그런데 부르는 것 자체는 약속이라
# 기계가 못 막는다. 막을 수 있는 것은 **부르라는 지시가 본문에 있나** 와
# **그 지시가 어느 항목을 넘기는지 id 로 적나** 까지다.
#
# 내용 조건이 빈 커맨드에는 걸지 않는다 — 부를 것이 없는 게 정상이고,
# 없는 것을 요구하면 커맨드가 게이트를 발명하게 된다.
GK_CALL = re.compile(r'gatekeeper`?\s*(?:에이전트)?\s*(?:에|에게|를|을)?\s*'
                     r'[^\n]{0,30}?(?:부른다|넘긴다|위임)')


@check('gatekeeper-delegation', 'gatekeeper 위임 지시',
       '게이트를 약속만 하고 아무도 안 부르는 것')
def _gatekeeper_delegation(ctx):
    r = Result(unit='커맨드')
    t = _topo(ctx)
    if not t:
        return r
    for name, c in (t.get('commands') or {}).items():
        items = _content_items(c)
        if not items:
            continue                       # 부를 것이 없다 — 대상이 아니다
        p = os.path.join(ctx.root, f'plugins/flow/commands/{name}.md')
        if not os.path.isfile(p):
            continue
        r.targets += 1
        if not GK_CALL.search(ctx.read(p)):
            ids = ', '.join(str((x or {}).get('id')) for _, x in items)
            r.fail(f"위임 지시 없음 {ctx.rel(p)} — 내용 조건({ids})이 있는데 "
                   f"`gatekeeper` 를 부르라는 지시가 본문에 없다 "
                   f"(약속만 남으면 게이트가 이름만 있는 것이다)")
    return r


# ── 위임 지시가 어느 항목을 넘기는지 적나 ──
# `gatekeeper-delegation` 은 **부르라는 지시가 있나** 까지다. 그것만 보면 *"gatekeeper 에
# 넘긴다"* 한 줄로 통과하고, **무엇을 넘길지는 넘기는 쪽이 그때 정하게 된다** — 그러면
# 판정 기준의 정본이 데이터가 아니라 그 순간의 판단이다. `gatekeeper.md` 는 스스로
# *"기준을 발명하지 않는다. 무엇을 볼지는 위임 지시가 준다"* 라고 적는다.
#
# **검사를 가른 이유** — 한 id 에 두 규칙을 묶으면 위반 픽스처가 하나만 건드려도 통과라
# 나머지가 사문화돼도 테스트가 못 잡는다(T1 이 검사를 넷으로 가른 것과 같은 이유다).
@check('gate-item-named', '위임 지시 ↔ 내용 조건 id',
       '무엇을 넘기는지 적지 않아 판정 기준이 데이터에서 오지 않는 것')
def _gate_item_named(ctx):
    r = Result(unit='내용 조건')
    t = _topo(ctx)
    if not t:
        return r
    for name, c in (t.get('commands') or {}).items():
        p = os.path.join(ctx.root, f'plugins/flow/commands/{name}.md')
        if not os.path.isfile(p):
            continue
        text = None
        for _, item in _content_items(c):
            r.targets += 1
            if text is None:
                text = ctx.read(p)
            iid = str((item or {}).get('id'))
            if iid not in text:
                r.fail(f"항목을 안 적었다 {ctx.rel(p)} — `{iid}` 를 `gatekeeper` 에 "
                       f"넘긴다고 topology 가 적는데 본문에 그 id 가 없다 "
                       f"(무엇을 넘기는지 본문이 지목해야 판정 기준이 데이터에서 온다)")
    return r


# ── entry.content 의 판정자가 진행하는 쪽인가 ──
# `gatekeeper-delegation` 은 content 가 **있나** 와 부르라는 지시가 **있나** 만 본다.
# 그래서 `who` 가 무엇이든 통과한다 — 실제로 `review` 의 `finding-severity` 가 `who=reviewer`
# 였다. **발견을 만든 쪽이 자기 발견의 severity 를 판정한다**.
# `00.concept.md` 의 능력 2(판정 독립성)와 `01.architecture.md` 의 `자기 검증 금지` 가 그 원칙이다.
#
# **어느 `who` 가 허용인가 — 근거.** 현 5건 중 4건이 `gatekeeper` 고 하나만 달랐다.
# 허용 목록을 이 스크립트에 손으로 열거하지 않는다 — 손으로 적은 화이트리스트는 사문화된다.
# 정본은 `flow.topology.json` 의 `grades.content.judges` 다 — 그 등급의 뜻을 적어 둔 바로 그 자리다.
#
# **선언만으로는 못 막는다.** 데이터라 누구든 늘릴 수 있으니 `machine` 이 `enforcedBy` 로
# 배선을 증명하듯, 판정자는 **도구 권한으로 증명한다.** 산출 도구(`Write`·`Edit`·`Bash`)를 가진
# 에이전트는 만들거나 돌리는 쪽이라 판정자가 될 수 없다 —
# `agents/gatekeeper.md` 가 *"`Bash` 가 없는 것은 의도다. 도구를 돌리는 쪽(`verifier`·`reviewer`)과
# 그 결과를 의심하는 쪽을 가른다"* 라고 스스로 적은 그 경계다.
#
# **못 잡는 것** — 쓰기·실행 도구가 없는 `explorer` 는 도구 축으로는 판정자와 구별되지 않는다.
# 그건 `judges` 에 적히지 않는 것으로만 막힌다(선언 축). 두 축 다 통과해야 판정자다.
PRODUCING_TOOLS = ('Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Bash')


def _agent_tools(ctx):
    """에이전트 이름 → frontmatter `tools` 목록. 파일이 없으면 키도 없다."""
    out = {}
    for p in ctx.paths('plugins/flow/agents/*.md'):
        m = re.search(r'^tools:\s*(.+)$', ctx.read(p), re.M)
        out[os.path.basename(p)[:-3]] = [x.strip() for x in (m.group(1) if m else '').split(',')
                                         if x.strip()]
    return out


@check('gate-judge-independence', '내용 조건 판정자 ↔ 진행하는 쪽',
       '발견을 만든 쪽이 자기 발견을 판정하는 것 (재설계 D3 · 능력 2 · 자기 검증 금지)')
def _gate_judge_independence(ctx):
    r = Result(unit='내용 조건')
    t = _topo(ctx)
    if not t:
        return r
    judges = ((t.get('grades') or {}).get('content') or {}).get('judges')
    judges = judges if isinstance(judges, list) else []
    tools = _agent_tools(ctx)

    # 선언 자체를 먼저 본다 — 판정자가 도구로 증명되지 않으면 목록이 늘어나기만 한다
    for who in judges:
        r.targets += 1
        if who not in tools:
            r.fail(f"없는 판정자 — `grades.content.judges` 의 `{who}` 에이전트가 없다 "
                   f"(`plugins/flow/agents/{who}.md` 가 없다)")
            continue
        bad = [x for x in tools[who] if x in PRODUCING_TOOLS]
        if bad:
            r.fail(f"판정자가 산출 도구를 갖는다 — `{who}` 의 `tools` 에 "
                   f"{' · '.join(bad)} 가 있다 (만들거나 돌리는 쪽은 자기 산출을 판정할 수 없다. "
                   f"판정자 선언을 지우거나 도구를 뗀다)")

    for name, c in (t.get('commands') or {}).items():
        for slot, item in _content_items(c):
            r.targets += 1
            iid = (item or {}).get('id')
            who = (item or {}).get('who')
            if not who:
                r.fail(f"판정자 없음 — commands.{name}.{slot}.content `{iid}` 에 `who` 가 없다 "
                       f"(안 적으면 진행하는 커맨드가 자기 조건을 판정한다 = 게이트가 없다)")
            elif who not in tools:
                r.fail(f"없는 판정자 — commands.{name}.{slot}.content `{iid}` 의 "
                       f"`who: {who}` 에이전트가 없다")
            elif who not in judges:
                r.fail(f"판정 독립성 위반 — commands.{name}.{slot}.content `{iid}` 의 판정자가 "
                       f"`{who}` 다. 그 국면을 진행하는 쪽이라 자기 산출을 자기가 판정한다 "
                       f"(판정자 정본은 `grades.content.judges` — 늘리려면 도구 권한으로 증명한다)")
    return r


# ── 내용 조건의 시점이 성립하나 ──
# **재설계 D5 가 여기다.** 내용 조건 5개가 전부 `entry.content` 에 있었는데 내용은 퇴장
# 조건이었다 — `contract-followed`(구현을 해 봐야 안다) · `coverage-gap`(감사 결과 자체) ·
# `requirement-covered`(설계를 해 봐야 안다). 진입 시점에는 판정할 대상이 없으니
# `next` 의 전환 게이트가 원리상 판정 불가였다. 이름은 있고 아무도 판정할 수 없는 상태 —
# *"게이트를 약속만 하고 아무도 안 부르는 것"* 의 변형이다.
#
# **기계가 볼 수 있는 것은 시점의 근거다.** 무엇이 언제 존재하는지는 못 읽지만,
# *"이 조건이 판정하는 대상을 누가 만들었나"* 는 데이터로 적히면 대조할 수 있다.
#
#   entry — `producedBy` 에 **앞 커맨드**를 적어야 한다. 그 커맨드가 `after` 안에 있어야
#           하고 자기 자신이면 안 된다. 못 적으면 그것은 자기가 만들 것을 판정하는 것,
#           즉 퇴장 조건이다.
#   exit  — 자기 산출을 판정하는 자리다. `producedBy` 를 적으면 자리가 틀렸다.
#
# **한계** — entry 쪽 규칙은 지금 repo 에서 대상이 0이다(내용 조건 5개가 전부 exit 로 갔다).
# 그 가지는 `lint.test.py` 의 위반 픽스처만 밟는다. 검사 전체의 대상은 exit 5건이라
# 0건은 아니지만, **entry 가지는 픽스처로만 살아 있다**는 것을 여기 적어 둔다.
@check('gate-timing', '내용 조건의 시점 ↔ 판정 대상',
       '진입에서 판정할 대상이 없는 조건을 진입이라 적는 것')
def _gate_timing(ctx):
    r = Result(unit='내용 조건')
    t = _topo(ctx)
    if not t:
        return r
    cmds = t.get('commands') or {}
    for name, c in cmds.items():
        after = [str(x) for x in ((c or {}).get('after') or [])]
        for slot, item in _content_items(c):
            r.targets += 1
            iid = (item or {}).get('id')
            made = (item or {}).get('producedBy')
            if slot == 'exit':
                if made:
                    r.fail(f"퇴장 조건에 `producedBy` — commands.{name}.exit.content "
                           f"`{iid}` 는 이 커맨드가 만든 것을 판정하는 자리다. 앞 커맨드가 "
                           f"만든 것을 판정한다면 `entry.content` 로 올린다")
                continue
            if not made:
                r.fail(f"진입에서 판정할 대상이 없다 — commands.{name}.entry.content "
                       f"`{iid}` 에 `producedBy` 가 없다. 시작할 때 무엇을 보고 판정하나 "
                       f"— 그 대상을 만든 앞 커맨드를 적는다. 못 적으면 이 커맨드가 만들 것을 "
                       f"판정하는 것이고, 그것은 `exit.content` 다 (D5)")
            elif made == name:
                r.fail(f"자기가 만든 것을 진입에서 판정한다 — commands.{name}.entry.content "
                       f"`{iid}` 의 `producedBy` 가 자기 자신이다 (`exit.content` 로 내린다)")
            elif made not in cmds:
                r.fail(f"없는 커맨드 — commands.{name}.entry.content `{iid}` 의 "
                       f"`producedBy: {made}` 가 위상에 없다")
            elif made not in after:
                r.fail(f"앞 커맨드가 아니다 — commands.{name}.entry.content `{iid}` 는 "
                       f"`{made}` 가 만든 것을 본다는데 `{made}` 가 `commands.{name}.after` "
                       f"({', '.join(after) or '없음'})에 없다. 오지 않는 국면의 산출은 "
                       f"진입 시점에 없다")
    return r


# ── SKILL.md 가 "반드시 읽는다" 한 조각이 실제로 배선됐나 ──
# `fragment-reference-exists` 는 가리킨 조각이 **실존하나** 만 본다. 실존하는데 아무도 안 실으면
# 그 지시는 죽은 지시다 — `code-graph/SKILL.md:27` 이 계약·MSA 면 `service-boundary` 를 반드시
# 읽으라 하는데 `build`·`design` 의 `loads` 에 없었다. `build.md` 는 *"조각은 여기 적힌 것만
# 읽는다"* 라 못 박으므로 어긋남이 아니라 **정면 충돌**이고, MSA 레거시에서 "영향 없음" 오보가 난다.
#
# **표 전체를 요구하지 않는다.** 스킬 하나가 조각 일곱을 갖기도 하는데 싣는 커맨드마다 전부
# 요구하면 컨텍스트 예산(능력 6)이 무너진다. 조각 고르기는 커맨드의 권한이다.
# 그래서 **고르기라는 변명이 성립하지 않는 세 자리만** 본다.
#
#   ① 조건부로 실은 스킬 — 그 상황일 때만 읽으므로 예산 논거가 없다. 상황이 오면 표가 정본이다
#   ② 본체만 실은 스킬 — SKILL.md 가 라우터고 내용이 조각에 있다. 조각을 하나도 안 실으면
#      그 스킬은 **이름만** 실린 것이다. 일부러 그런 것이면 `skills.<이름>.bodyOnly` 로 적는다
#   ③ 커맨드가 직접 읽는 문서(본문·절차 조각)가 **읽으라고 지시한** 조각 — 인용이 아니라 지시다
#
# **셋을 한 검사에 넣지 않는다.** `lint.test.py` 는 **검사 id 마다** 픽스처 한 쌍을 요구한다 —
# 셋을 묶으면 위반 픽스처가 하나만 건드려도 통과라, 나머지 둘이 사문화돼도 테스트가 못 잡는다.
# 표 렌더 검사를 넷으로 가른 것과 같은 이유다.
FRAG_CELL = re.compile(r'`(?:([a-z][a-z0-9-]*)/)?references/([a-z0-9-]+)\.md`')
FRAG_NAMED = (re.compile(r'`([a-z][a-z0-9-]*)/(?:references/)?([a-z0-9-]+)(?:\.md)?`'),
              re.compile(r'`([a-z][a-z0-9-]*)`\s*의\s*`([a-z0-9-]+)`'))
READ_ORDER = re.compile(r'읽는다|읽어라|읽고')


def _must_read(ctx):
    """스킬 → 그 SKILL.md 의 `어느 조각을 읽나` 표가 지시한 조각 [(조각, 줄)]."""
    out = {}
    for p in ctx.skills():
        s = os.path.basename(os.path.dirname(p))
        got, inside = [], False
        for i, l in enumerate(ctx.lines(p), 1):
            if l.startswith('## '):
                inside = l[3:].strip() == '어느 조각을 읽나'
                continue
            if not inside or not l.startswith('|') or SEP.match(l):
                continue
            cells = l.strip('|').split('|')
            if len(cells) < 2 or '반드시 읽는다' in cells[1]:
                continue                       # 머리글 행
            for m in FRAG_CELL.finditer(cells[1]):
                got.append((f"{m.group(1) or s}/{m.group(2)}", i))
        if got:
            out[s] = got
    return out


def _load_rows_of(ctx, t):
    """커맨드 → [(모드, 늘 싣는 것 ∪ 조건부, 조건부만)] — 세 검사가 같은 창구를 쓴다."""
    out = {}
    for name, c in (t.get('commands') or {}).items():
        rows = _loads_rows((c or {}).get('loads'))
        if rows:
            out[name] = [(m, set(a) | set(cd), set(cd)) for m, a, cd in rows]
    return out


@check('fragment-load-wired', '조건부로 실은 스킬의 반드시 조각',
       '조건부 적재가 표의 조각을 골라 실어 그 상황에서 반쪽만 읽는 것 — MSA 오보 경로 (D4)')
def _fragment_load_wired(ctx):
    # ① 조건부 적재에는 **예산 논거가 없다.** 그 상황일 때만 실리므로, 상황이 왔을 때 읽을 것을
    # 고를 이유가 없다. 그래서 여기서는 표를 그대로 요구한다.
    r = Result(unit='배선 요구')
    t = _topo(ctx)
    if not t:
        return r
    must = _must_read(ctx)
    for name, rows in _load_rows_of(ctx, t).items():
        for mode, have, cond in rows:
            tag = f"[{mode}] " if mode else ''
            for s in sorted(x for x in cond if '/' not in x):
                for frag, ln in must.get(s, []):
                    r.targets += 1
                    if frag not in have:
                        r.fail(f"조건부 배선 누락 commands.{name} — {tag}`{s}` 를 조건부로 "
                               f"싣는데 `{frag}` 가 없다 (SKILL.md:{ln} 이 그 상황이면 반드시 "
                               f"읽으라 한다. 조건부는 그 상황일 때만 실리니 예산 이유로 뺄 수 없다)")
    return r


@check('skill-loaded-body-only', '이름만 실린 스킬',
       '조각을 하나도 안 싣고 라우터만 실어 규약이 안 읽히는 것')
def _skill_loaded_body_only(ctx):
    # ② 규약은 조각에 있다 — `SKILL.md` 는 대부분 **어느 조각을 읽나** 를 정하는 라우터다.
    # 조각을 하나도 안 싣고 스킬만 실으면 그 자리에서 읽히는 것은 라우팅표뿐이다.
    # **일부러 그렇게 하는 자리가 있다**(`theme-apply` 는 설계 국면에 토큰 정본 한 줄만 준다) —
    # 그건 `skills.<이름>.bodyOnly` 로 적고 `$bodyOnly-why` 로 왜인지 남긴다. 안 적으면 빠뜨린 것과
    # 구별되지 않는다.
    r = Result(unit='스킬 적재')
    t = _topo(ctx)
    if not t:
        return r
    must = _must_read(ctx)
    meta = t.get('skills') or {}
    for name, rows in _load_rows_of(ctx, t).items():
        for mode, have, _ in rows:
            tag = f"[{mode}] " if mode else ''
            for s in sorted(x for x in have if '/' not in x):
                if s not in must:
                    continue
                r.targets += 1
                if (meta.get(s) or {}).get('bodyOnly'):
                    if not (meta.get(s) or {}).get('$bodyOnly-why'):
                        r.fail(f"본체만 싣는 이유가 없다 — skills.{s}.bodyOnly 에 "
                               f"`$bodyOnly-why` 가 없다 (왜 조각이 필요 없는지 못 적으면 "
                               f"빠뜨린 것과 구별되지 않는다)")
                    continue
                if not any(f in have for f, _ in must[s]):
                    r.fail(f"이름만 실린 스킬 commands.{name} — {tag}`{s}` 를 싣는데 그 조각을 "
                           f"하나도 안 싣는다 (내용은 {_names([f for f, _ in must[s]])} 에 있다. "
                           f"SKILL.md 는 라우터다 — 일부러 본체만 싣는 것이면 "
                           f"`skills.{s}.bodyOnly` 로 적는다)")
    return r


@check('read-order-wired', '읽으라 한 조각이 배선됐나',
       '커맨드·절차가 읽으라 지시한 조각이 loads 에 없어 읽을 수 없는 것 (D4 · W2)')
def _read_order_wired(ctx):
    # ③ 커맨드 본문과 그 커맨드의 절차 조각은 **커맨드가 실제로 읽는 문서**다. 거기서 어떤 조각을
    # 읽으라고 지시했는데 `loads` 에 없으면 그 자리에서는 읽을 수 없다.
    #
    # **인용과 지시를 가른다.** 같은 줄에 `읽는다`·`읽어라`·`읽고` 가 있어야 지시로 본다 —
    # *"그 사실은 `drift-check/rule` 에도 적혀 있다"* 같은 인용까지 배선을 요구하면 커맨드가
    # 남의 조각을 다 싣게 된다. 놓치는 쪽으로 틀린다.
    #
    # **모드로 가르지 않는다.** 어느 모드가 어느 절차를 읽나는 데이터에 없다. 한 모드라도 실으면
    # 통과다 — 여기서 엄격하면 없는 근거로 배선을 발명하게 된다.
    r = Result(unit='읽기 지시')
    t = _topo(ctx)
    if not t:
        return r
    frags = {f"{s}/{f}" for s, v in (t.get('skills') or {}).items()
             for f in ((v or {}).get('fragments') or [])}
    rows_of = _load_rows_of(ctx, t)
    for name, c in (t.get('commands') or {}).items():
        everywhere = set()
        for _, have, _c in rows_of.get(name, []):
            everywhere |= have
        reads = [os.path.join(ctx.root, f'plugins/flow/commands/{name}.md')]
        reads += [os.path.join(ctx.root, f'plugins/flow/procedures/{x}.md')
                  for x in ((c or {}).get('procedures') or [])]
        for p in reads:
            if not os.path.isfile(p):
                continue
            for i, l in enumerate(ctx.lines(p), 1):
                if not READ_ORDER.search(l):
                    continue
                seen = set()
                for pat in FRAG_NAMED:
                    for m in pat.finditer(l):
                        frag = f"{m.group(1)}/{m.group(2)}"
                        if frag not in frags or frag in seen:
                            continue
                        seen.add(frag)
                        r.targets += 1
                        if frag not in everywhere:
                            r.fail(f"읽으라 한 조각이 배선에 없다 {ctx.rel(p)}:{i} — "
                                   f"`{frag}` 를 읽으라 하는데 `commands.{name}.loads` 에 없다 "
                                   f"(읽을 수 없는 지시다 — 배선에 넣거나 지시를 내린다)")
    return r


# ── 절차 조각 배선 — topology ↔ 디스크 ↔ 커맨드 본문 ──
# **`read-order-wired` 는 없는 절차 파일을 조용히 건너뛴다**(`if not os.path.isfile(p): continue`).
# 그래서 `commands.*.procedures` 에 오타를 내면 그 커맨드는 절차를 하나도 안 읽는데 검사기는
# 전부 초록이다. 지금 배선 13건이 전부 디스크에 있는 것은 **지켜져서가 아니라 우연이다.**
#
# `command-loads-parity` 도 이 자리를 안 본다 — 그쪽이 대조하는 것은 `loads`(스킬·조각)뿐이고
# `procedures` 는 다른 키다. 그래서 **세 곳을 양방향으로 대조한다.**
#
#   ① 선언 ↔ 디스크 — 없는 파일을 가리키나 · 아무도 안 싣는 파일이 남아 있나
#   ② 선언 ↔ 커맨드 본문 — 싣는다고 적어 두고 본문이 한 번도 안 가리키면 읽힐 계기가 없다.
#      반대로 본문이 가리키는데 선언에 없으면 그 파일은 그 커맨드에 실리지 않는다
#   ③ `## 연결` 의 `절차 조각` 행 — 행이 있으면 선언과 낱낱이 같아야 한다
#
# **`## 연결` 에 행이 있는 것까지는 요구하지 않는다.** `design` 은 레벨이 어느 절차를 읽는지
# 가르므로 그 표를 `## 절차` 안에 두었다(`design.md:63-66`) — 연결 절에 무조건 행을 요구하면
# 조건부 구조를 가진 커맨드가 늘 읽는 것처럼 적게 된다. 요구하는 것은 **본문 어딘가가
# 그 경로를 가리키는 것**이고, 행이 있으면 그 행이 정확한지까지 본다.
PROC_DIR = 'plugins/flow/procedures'
PROC_PATH = re.compile(r'procedures/([a-z0-9-]+(?:/[a-z0-9-]+)*)\.md')
PROC_ROW = '절차 조각'


@check('procedures-wired', '절차 조각 배선 (topology ↔ 디스크 ↔ 본문)',
       '없는 절차를 가리켜도 `read-order-wired` 가 조용히 건너뛴다 (T7 구현 1)')
def _procedures_wired(ctx):
    r = Result(unit='절차 조각')
    t = _topo(ctx)
    if not t:
        return r
    cmds = t.get('commands') or {}
    base = os.path.join(ctx.root, PROC_DIR)
    on_disk = {os.path.relpath(p, base).replace(os.sep, '/')[:-3]
               for p in ctx.paths(f'{PROC_DIR}/**/*.md')}

    declared = {}
    for name, c in sorted(cmds.items()):
        for x in ((c or {}).get('procedures') or []):
            declared.setdefault(str(x), []).append(name)

    # ① 선언 ↔ 디스크 — 양방향
    for x, who in sorted(declared.items()):
        r.targets += 1
        if x not in on_disk:
            r.fail(f"없는 절차를 싣는다 — commands.{' · '.join(who)}.procedures 의 `{x}` 는 "
                   f"`{PROC_DIR}/{x}.md` 가 없다 (오타면 그 커맨드는 절차를 안 읽는데 "
                   f"아무도 알려 주지 않는다)")
    for x in sorted(on_disk - set(declared)):
        r.targets += 1
        r.fail(f"아무도 안 싣는 절차 — `{PROC_DIR}/{x}.md` 가 어느 커맨드의 "
               f"`procedures` 에도 없다 (실릴 자리가 없으면 배포만 되고 안 읽힌다 — "
               f"싣거나 지운다)")

    # ② 선언 ↔ 커맨드 본문 · ③ `## 연결` 의 절차 조각 행
    for name, c in sorted(cmds.items()):
        p = os.path.join(ctx.root, f'plugins/flow/commands/{name}.md')
        if not os.path.isfile(p):
            continue
        mine = [str(x) for x in ((c or {}).get('procedures') or [])]
        named = set(PROC_PATH.findall(ctx.read(p)))
        for x in mine:
            r.targets += 1
            if x not in named:
                r.fail(f"본문이 안 가리킨다 {ctx.rel(p)} — topology 는 `{x}` 를 싣는다고 "
                       f"적는데 본문에 그 경로가 없다 (실려도 읽으라는 말이 없으면 "
                       f"안 읽는다)")
        for x in sorted(named - set(mine)):
            r.targets += 1
            r.fail(f"배선 없는 절차를 가리킨다 {ctx.rel(p)} — 본문이 `{x}` 를 적는데 "
                   f"`commands.{name}.procedures` 에 없다 (그 자리에서는 안 실린다 — "
                   f"정본에 먼저 적는다)")

        sec = _section(ctx, p, '연결')
        rows = [line for lab, line in _table_rows(sec or '') if lab == PROC_ROW]
        if not rows:
            continue
        r.targets += 1
        got = {x for line in rows for x in PROC_PATH.findall(line)}
        if got != set(mine):
            miss = sorted(set(mine) - got)
            over = sorted(got - set(mine))
            r.fail(f"연결 절 절차 행 어긋남 {ctx.rel(p)} — "
                   + (f"빠진 것 {_names(miss)} " if miss else '')
                   + (f"초과 {_names(over)} " if over else '')
                   + f"(`## 연결` 의 `{PROC_ROW}` 행은 `commands.{name}.procedures` 와 "
                     f"낱낱이 같아야 한다)")
    return r


# ── 도달 불가 커맨드 — 라우터에서 갈 수 없는 국면 ──
# **재설계 D7 이 여기다.** `next.next` 에 `setup`·`spike`·`publish` 가 없어서, `next.md` 가
# 스스로 *"커맨드를 지어내지 않는다 — 위상 정본에 있는 것만 부른다"* 라고 못 박은 그 규칙대로
# 하면 라우터가 그 셋을 영원히 제시할 수 없었다. 그런데 `next.md` 본문은 설정이 없으면
# `/flow:setup` 을 안내하라 하고 유형 칸에는 `불확실`(→ `spike`)을 출력하라 한다 —
# **본문이 데이터에 없는 길을 안내한다.**
#
# **"도달 불가"를 어떻게 정의하나 — 이 검사의 값어치가 거기 있다.**
# 모든 커맨드가 `next` 로만 도달해야 하는 것은 아니다. 판정 기준은 이것으로 잡는다:
#
#   **사용자가 커맨드 이름을 몰라도 그 국면에 닿을 수 있나.**
#
# 이름을 알고 치는 사람은 어디든 간다 — 그건 위상이 아니라 기억이다. 제품이 책임지는 것은
# *모르는 사람이 도착하는 길*이고, 그 길의 정본이 이 파일의 `next` 간선이다.
# 그래서 **진입점에서 `next` 간선을 따라 닿지 않는 커맨드는 도달 불가**로 본다.
#
# **진입점을 스크립트에 손으로 열거하지 않는다** — 손으로 적은 화이트리스트는 낡는다.
# 정본은 데이터다: `commands.<이름>.entryPoint: true` 를 단 커맨드가 진입점이고, 왜 그런지를
# `$entryPoint-why` 로 남긴다. 진입점을 늘려 검사를 무르게 만드는 길은 **`after` 가 막는다** —
# 앞에 와야 하는 국면이 있는 커맨드는 진입점이 될 수 없다. 시작점인데 선행 조건이 있다는 말은
# 앞뒤가 안 맞는다.
#
# **되돌아가는 간선도 여기서 본다.** `after` 는 실패했을 때 되돌아가는 앞 국면이고
# (`next.md` — *"게이트가 실패하면 사유와 함께 직전 국면을 다시 실행한다"*), `gate-timing` 도
# `after` 를 그 뜻으로 읽는다. 되돌아간 뒤 다시 앞으로 오지 못하면 그건 **편도 되돌림**이다 —
# `X.after` 에 `Y` 가 있으면 `Y.next` 에 `X` 가 있어야 한다.
#
# **반대 방향(앞으로만 있는 간선)은 요구하지 않는다.** `setup.next` 는 `prd`·`design` 인데
# `design.after` 는 `prd` 뿐이다 — 앞으로 가는 지름길은 있어도 되돌아갈 자리는 요구를 만든
# 국면이라 다르다. 대칭을 요구하면 아무것도 안 만드는 국면으로 되돌아가라고 적게 된다.
#
# **못 잡는 것** — 간선이 있어도 커맨드 본문이 그 유형을 어디로 보내는지 안 적으면 라우터는
# 여전히 헤맨다. 그 축은 데이터가 아니라 산문이라 기계가 못 본다.
@check('route-reachable', '도달 불가 커맨드 · 편도 되돌림',
       '라우터가 부를 수 없는 국면이 위상에 남는 것 (재설계 D7 · 능력 5)')
def _route_reachable(ctx):
    r = Result(unit='커맨드')
    t = _topo(ctx)
    if not t:
        return r
    cmds = t.get('commands') or {}
    if not cmds:
        return r                      # 위상이 비었다 — `topology-pending` 이 지목한다

    edges = {n: [str(x) for x in ((c or {}).get('next') or [])] for n, c in cmds.items()}
    backs = {n: [str(x) for x in ((c or {}).get('after') or [])] for n, c in cmds.items()}

    # ① 간선이 실재하는 커맨드를 가리키나 — 오타는 간선을 조용히 없앤다
    for n in sorted(cmds):
        for key, xs in (('next', edges[n]), ('after', backs[n])):
            for x in xs:
                r.targets += 1
                if x not in cmds:
                    r.fail(f"없는 커맨드를 가리킨다 — commands.{n}.{key} 의 `{x}` 가 "
                           f"`commands` 에 없다 (그 간선은 아무 데도 안 간다)")

    # ② 진입점 선언 — 없으면 이 검사는 아무것도 판정하지 못한다
    roots = []
    for n, c in sorted(cmds.items()):
        if not (c or {}).get('entryPoint'):
            continue
        r.targets += 1
        roots.append(n)
        if not (c or {}).get('$entryPoint-why'):
            r.fail(f"진입점 이유가 없다 — commands.{n}.entryPoint 에 `$entryPoint-why` 가 "
                   f"없다 (왜 아무 앞 국면 없이 여기서 시작하나를 못 적으면 진입점을 늘려 "
                   f"이 검사를 끄는 길이 된다)")
        if backs[n]:
            r.fail(f"진입점인데 앞 국면이 있다 — commands.{n}.after 가 "
                   f"{_names(backs[n])} 다. 앞에 와야 하는 국면이 있는 커맨드는 시작점이 "
                   f"아니다 (`entryPoint` 를 떼거나 `after` 를 비운다)")
    if not roots:
        r.targets += 1
        r.fail("진입점이 없다 — `commands.<이름>.entryPoint: true` 를 단 커맨드가 하나도 "
               "없어서 도달 가능성을 계산할 자리가 없다 (사용자가 이름을 몰라도 부르는 "
               "커맨드에 단다)")
        return r

    # ③ 진입점에서 `next` 간선을 따라 닿나
    seen, stack = set(roots), list(roots)
    while stack:
        for x in edges.get(stack.pop(), []):
            if x in cmds and x not in seen:
                seen.add(x)
                stack.append(x)
    for n in sorted(cmds):
        r.targets += 1
        if n not in seen:
            r.fail(f"도달 불가 — commands.{n} 이 진입점({' · '.join(roots)})에서 `next` 를 "
                   f"따라 닿지 않는다. 이름을 아는 사람만 갈 수 있는 국면이다 "
                   f"(앞 국면의 `next` 에 넣거나, 시작점이면 `entryPoint` 로 선언한다)")

    # ④ 편도 되돌림 — 되돌아간 국면에서 다시 앞으로 못 온다
    for n in sorted(cmds):
        for y in backs[n]:
            if y not in cmds:
                continue                       # ① 이 이미 지목했다
            r.targets += 1
            if n not in edges.get(y, []):
                r.fail(f"편도 되돌림 — commands.{n}.after 가 `{y}` 를 앞 국면으로 적는데 "
                       f"`commands.{y}.next` 에 `{n}` 이 없다. 실패해서 되돌아가면 다시 "
                       f"앞으로 올 길이 없다 (두 간선은 짝이다)")
    return r


# ── 스킬 description 의 등급 ↔ 문형 ──
# `자율` 이라 적고 오발동 억제 신호(`/flow:X 가 쓴다`)를 달면 **등급이 사실상 뒤집힌다.**
# 그래서 등급을 데이터로 두고 문형을 대조한다.
#
# 등급을 `SKILL.md` frontmatter 의 비표준 필드로 둘 수 있는지는 이 세션에서 확인이 안 됐다
# (설계 `description 등급` 절의 "구현 전 확인할 것"). 그래서 지시된 대체 자리인
# `flow.topology.json` 의 `skills.<이름>.grade` 를 정본으로 읽는다.
GRADES = {
    '호출-전용': '커맨드가 싣는다 — 싣는 커맨드를 열거한다',
    '자율': '사용자·작업 성질로 발동한다 — 커맨드 열거로 끝내지 않는다',
    '기본값': '조건에 맞는 커맨드가 전부 싣는다 — 열거하지 않는다(부분 열거는 거짓말이 된다)',
}
SELF_CALL = re.compile(r'사용자가\s*직접|직접\s*(?:요청|부른)')


@check('skill-description-grade', '스킬 등급 ↔ description 문형',
       '자율이라 적고 억제 신호를 달면 등급이 뒤집힌다')
def _skill_description_grade(ctx):
    r = Result(unit='스킬')
    t = _topo(ctx)
    if not t:
        return r
    for name, v in sorted((t.get('skills') or {}).items()):
        p = os.path.join(ctx.root, f'plugins/flow/skills/{name}/SKILL.md')
        if not os.path.isfile(p):
            continue
        r.targets += 1
        grade = (v or {}).get('grade')
        if grade not in GRADES:
            r.fail(f"등급 없음 skills.{name}.grade — {grade!r} "
                   f"(하나여야 한다: {' · '.join(GRADES)})")
            continue
        d = _desc(ctx, p)
        if not d:
            r.fail(f"description 없음 {ctx.rel(p)} — 매 턴 실리는 자리가 비었다")
            continue
        listed = set(re.findall(r'/flow:([a-z]+)', d))
        if grade == '호출-전용' and not listed:
            r.fail(f"문형 어긋남 {ctx.rel(p)} [호출-전용] — description 이 싣는 커맨드를 "
                   f"열거하지 않았다 (일반형은 기계가 대조할 수 없다 — "
                   f"'모든 커맨드가 쓴다' 같은 일반형은 대조할 짝이 없다)")
        if grade == '기본값' and listed:
            r.fail(f"문형 어긋남 {ctx.rel(p)} [기본값] — `/flow:"
                   f"{sorted(listed)[0]}` 를 열거했다. 기본값은 열거하지 않는다 "
                   f"(부분 열거는 '이것만 쓴다'로 읽혀 거짓말이 된다)")
        if grade == '자율' and not SELF_CALL.search(d):
            r.fail(f"문형 어긋남 {ctx.rel(p)} [자율] — 커맨드만 적고 직접 호출을 안 적었다 "
                   f"(억제 신호만 남으면 등급이 뒤집힌다)")
    return r


# ── description 의 '누가 쓴다'가 사실인가 — 양방향 ──
# **한 방향만** 보면 "모든 커맨드가 쓴다"는 거짓이 통과한다. 매 턴 실리는 거짓말이다.
# 조각만 싣는 것도 '쓴다'로 센다 — `doc-verify` 는 `/flow:design` 이 `canon-map` 조각만 읽는다.

def _uses(t):
    """커맨드 → 그 커맨드가 쓰는 스킬 이름 집합 (조각만 싣는 것도 쓴다)."""
    out = {}
    for name, c in (t.get('commands') or {}).items():
        sk = set()
        for _, always, cond in _loads_rows((c or {}).get('loads')):
            for x in set(always) | set(cond):
                sk.add(x.split('/')[0])
        out[name] = sk
    return out


@check('skill-description-users', "description 의 '누가 쓴다' 양방향",
       '한 방향만 보면 거짓 주장이 매 턴 실린다')
def _skill_description_users(ctx):
    r = Result(unit='스킬')
    t = _topo(ctx)
    if not t:
        return r
    uses = _uses(t)
    for name in sorted(t.get('skills') or {}):
        p = os.path.join(ctx.root, f'plugins/flow/skills/{name}/SKILL.md')
        if not os.path.isfile(p):
            continue
        d = _desc(ctx, p)
        if not d:
            continue                       # 위 검사가 지목한다
        r.targets += 1
        listed = set(re.findall(r'/flow:([a-z]+)', d))
        actual = {c for c, s in uses.items() if name in s}
        for c in sorted(listed - actual):
            r.fail(f"거짓 주장 {ctx.rel(p)} — `/flow:{c}` 가 쓴다고 적었는데 topology 의 "
                   f"`commands.{c}.loads` 에 `{name}` 도 그 조각도 없다 "
                   f"(매 턴 실리는 거짓말이다)")
        if listed:
            for c in sorted(actual - listed):
                r.fail(f"열거 누락 {ctx.rel(p)} — `/flow:{c}` 가 싣는데 description 에 없다 "
                       f"(부분 열거는 '이것만 쓴다'로 읽힌다 — 전부 적거나 등급을 "
                       f"`기본값` 으로 내린다)")
    return r


# ── limits 정본이 하나인가 ──
# **이 프로젝트가 스스로 경계한 병이 limits 에서 재발했다.** 셸 머리말의 `limit:` 8줄과
# `guard-rules.json` 의 `limits` 10개가 겹치는데 생성기가 둘 다 렌더해서, 사용자 문서의
# `못 막는 것` 표에 같은 한계가 6행씩 두 번 실렸다. 게다가 겹친 쪽 한 줄은 **낡았다** —
# `rsync` 를 잡게 고쳤는데 JSON 은 "rsync 는 통과한다"고 계속 적고 있었다.
#
# 왜 JSON 이 정본인가: `rule` 은 구현이 셸에 있어 본문의 `@rule` 표시와 대조되지만
# `limit` 은 대조할 짝이 없다 — 셸에 두면 근접성만 얻고 보장은 못 얻으면서 정본이 둘이 된다.
LIMIT_DUP_RATIO = 0.75


# **무엇까지 잡나 — 넘겨 읽지 마라.**
#   정본이 둘로 갈리는 것 → **구조로 막는다.** 셸 머리말에 `limit:` 이 있으면 문구와 무관하게 실패.
#   한 정본 안의 중복    → 문자 유사도라 **복붙과 가벼운 손질까지**다.
#     실측: `심볼릭 링크 우회`↔`심볼릭 링크로 우회하는 것` 은 잡고,
#           `MCP 파일 도구`↔`다른 실행 경로 — python subprocess · MCP 도구` 는 **안 잡는다.**
#     짧은 바꿔쓰기는 사람이 봐야 한다. 그걸 잡는다고 적지 않는다.
@check('limits-single-canon', 'limits 정본이 하나인가',
       '같은 한계가 두 정본에 갈려 생성 표에 두 번 실리고 한쪽이 낡는 것')
def _limits_single_canon(ctx):
    r = Result(unit='한계')
    try:
        import gen_docs
    except Exception as e:
        return broken(f"gen-docs 를 불러올 수 없다 — {type(e).__name__}: {e}")

    gp = os.path.join(ctx.root, gen_docs.GUARD_RULES)
    if not os.path.exists(gp):
        return r
    try:
        gr = json.loads(ctx.read(gp))
    except json.JSONDecodeError as e:
        r.targets = 1
        r.fail(f"guard-rules.json 파싱 실패 — {e}")
        return r
    rows = gen_docs.limit_rows(gr)
    r.targets = len(rows)

    if not rows:
        r.fail("`guard-rules.json` 의 `limits` 가 비었다 — 못 막는 것을 안 적으면 "
               "문서가 실제 방어보다 넓게 읽힌다")

    def norm(s):
        # 서식·기호를 지운다. 같은 한계를 다르게 꾸며 적은 것을 같다고 보게 한다
        return re.sub(r'[^가-힣a-zA-Z0-9]', '', re.sub(r'[`*]', '', str(s)))

    # ① 셸 머리말에 limit 이 남았나 — 남았으면 그 텍스트가 JSON 과 겹치는지까지 짚어 준다
    sh_limits = []
    if os.path.exists(os.path.join(ctx.root, gen_docs.GUARD_SH)):
        try:
            _, _, sh_limits, _ = gen_docs.shell_rules(ctx.root)
        except ValueError:
            sh_limits = []          # 머리말 형식 오류는 shell-guard-header 가 본다
    for s in sh_limits:
        r.targets += 1
        hit = next((x['what'] for x in rows
                    if SequenceMatcher(None, norm(s['what']), norm(x['what'])).ratio()
                    >= LIMIT_DUP_RATIO), None)
        if hit:
            r.fail(f"두 정본에 같은 한계 — 셸 머리말의 `{s['what'][:40]}` 가 "
                   f"`guard-rules.json` 의 `{hit[:40]}` 와 겹친다 "
                   f"(생성 표에 두 번 실린다. 셸 쪽을 지운다 — 정본은 JSON 이다)")
        else:
            r.fail(f"셸 머리말에 한계가 있다 — `{s['what'][:40]}` "
                   f"(정본은 `guard-rules.json` 의 `limits` 다. 옮긴다)")

    # ② 한 정본 안에서도 같은 것을 두 번 적었나
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i]['what'], rows[j]['what']
            if SequenceMatcher(None, norm(a), norm(b)).ratio() >= LIMIT_DUP_RATIO:
                r.fail(f"limits 안에서 중복 — `{a[:40]}` ↔ `{b[:40]}` "
                       f"(하나로 합친다)")

    # ③ 왜가 비면 표의 한 열이 `—` 로 남는다. 한계는 **왜 못 막나**가 본문이다
    for x in rows:
        if x['why'] == '—':
            r.fail(f"왜가 없다 — `{x['what'][:40]}` (`why` 를 적는다. "
                   f"못 막는 이유가 없으면 고칠 수 있는지도 판단할 수 없다)")
    return r


# ── `machine` 등급이 실제로 배선됐나 ──
# **여기가 한 번 어긋났던 자리다.** 강제력을 3등급으로 갈랐는데 topology 에
# `machine` 이라 적힌 진입 조건 7개 중 실제로 훅이 보는 것은 3개뿐이었고
# 커맨드의 `## 진입 조건` 표는 5곳에 *"훅 — 경로 존재"* 라고 렌더하고 있었다.
# 아무도 안 보는데 사용자에게는 기계라고 표시된 것이다 —
# "드리프트 4겹"이라 적고 AI 경로는 1겹인 것과 같은 종류다.
#
# 그래서 `machine` 을 다는 비용을 **배선 증명**으로 만든다. `enforcedBy` 로 무엇이
# 강제하는지 적고, 그 훅이 실재하고 `hooks.json` 에 걸렸는지 여기서 대조한다.
@check('machine-gate-wired', '`machine` 등급 ↔ 실제 훅 배선',
       '강제하는 기계가 없는데 기계라고 적는 것')
def _machine_gate_wired(ctx):
    r = Result(unit='machine 조건')
    tp = os.path.join(ctx.root, 'plugins/flow/flow.topology.json')
    hp = os.path.join(ctx.root, 'plugins/flow/hooks/hooks.json')
    if not os.path.exists(tp):
        return r
    try:
        topo = json.loads(ctx.read(tp))
    except json.JSONDecodeError as e:
        r.targets = 1
        r.fail(f"flow.topology.json 파싱 실패 — {e}")
        return r

    wired = {}          # 훅 경로 → 걸린 이벤트들
    if os.path.exists(hp):
        try:
            for ev, groups in (json.loads(ctx.read(hp)).get('hooks') or {}).items():
                for gr in groups or []:
                    for h in gr.get('hooks') or []:
                        cmd = (h.get('command') or '').strip('"')
                        tail = cmd.replace('${CLAUDE_PLUGIN_ROOT}/', '').strip('"')
                        wired.setdefault(tail, set()).add(ev)
        except json.JSONDecodeError as e:
            r.targets = 1
            r.fail(f"hooks.json 파싱 실패 — {e}")
            return r

    for name, c in (topo.get('commands') or {}).items():
        for item in ((c or {}).get('entry') or {}).get('machine') or []:
            r.targets += 1
            iid = item.get('id')
            eb = item.get('enforcedBy')
            if not isinstance(eb, dict):
                r.fail(f"배선 증명 없음 — commands.{name}.entry.machine `{iid}` 에 "
                       f"`enforcedBy` 가 없다 (무엇이 강제하는지 못 적으면 그건 기계가 "
                       f"아니라 약속이다. `promise` 로 내리고 `why` 를 적는다)")
                continue
            hook = eb.get('hook')
            if not hook:
                r.fail(f"배선 증명 불완전 — commands.{name}.entry.machine `{iid}` 의 "
                       f"`enforcedBy.hook` 이 비었다")
                continue
            if not os.path.exists(os.path.join(ctx.root, 'plugins/flow', hook)):
                r.fail(f"없는 훅을 가리킨다 — commands.{name}.entry.machine `{iid}` → "
                       f"`{hook}` 파일이 없다")
                continue
            kind = eb.get('kind')
            if kind == 'git-hook':
                # 우리가 심지만 **프로젝트가 설치해야** 도는 층이다. 조건을 안 적으면
                # 미설치 프로젝트에서 없는 층을 기계로 읽는다.
                if not eb.get('condition'):
                    r.fail(f"조건 없음 — commands.{name}.entry.machine `{iid}` 는 git 훅이라 "
                           f"프로젝트가 설치해야만 돈다. `enforcedBy.condition` 에 그 조건을 "
                           f"적어야 표에 함께 렌더된다")
            else:
                ev = eb.get('event') or 'PreToolUse'
                if ev not in wired.get(hook, set()):
                    r.fail(f"배선 안 됨 — commands.{name}.entry.machine `{iid}` 가 "
                           f"`{hook}` 을 가리키는데 hooks.json 의 `{ev}` 에 없다 "
                           f"(적어만 두고 안 걸면 아무도 판정하지 않는다)")
    return r


# ── 면제를 누가 채우나가 실제로 적혀 있나 ──
# **D2 가 이 검사의 부재였다.** `gate.legacyExempt` 는 기계로는 처음부터 돌았는데
# 채우라는 지시가 어느 커맨드에도 없었다 — 리포 전체에서 정의와 빈 배열 두 곳뿐이었다.
# 그런데 `build.md` 는 작동하는 면제인 것처럼 적었다. 도달 불가한 탈출구는 탈출구가 아니고,
# 그 자리에서 사람은 훅을 끈다.
#
# 그래서 **설정 키로 여는 면제에는 채우는 커맨드를 적게 하고, 그 커맨드가 정말 그 키를
# 말하는지 대조한다.** 양방향이다 — 데이터가 커맨드를 가리키고 커맨드가 키를 말해야 한다.
@check('exempt-fill-wired', '면제를 누가 채우나 ↔ 커맨드 본문',
       '채우는 길이 없는 면제는 도달 불가고, 사람은 그 자리에서 훅을 끈다 (D2)')
def _exempt_fill_wired(ctx):
    r = Result(unit='설정 면제')
    tp = os.path.join(ctx.root, 'plugins/flow/flow.topology.json')
    if not os.path.exists(tp):
        return r
    try:
        topo = json.loads(ctx.read(tp))
    except json.JSONDecodeError as e:
        r.targets = 1
        r.fail(f"flow.topology.json 파싱 실패 — {e}")
        return r

    for ex in ((topo.get('gate') or {}).get('exemptions') or []):
        ck = (ex or {}).get('configKey')
        if not ck:
            continue                      # 플러그인 정본 경로만 쓰는 면제는 채울 것이 없다
        r.targets += 1
        eid = ex.get('id')
        fills = ex.get('whoFills')
        text = '\n'.join(fills) if isinstance(fills, list) else str(fills or '')
        cmds = sorted(set(re.findall(r'/flow:([a-z][a-z0-9-]*)', text)))
        if not cmds:
            r.fail(f"채우는 커맨드가 없다 — gate.exemptions `{eid}` 의 `{ck}` 는 프로젝트가 "
                   f"채워야 하는데 `whoFills` 가 어느 커맨드도 가리키지 않는다 "
                   f"(그러면 그 면제는 도달 불가다 — D2)")
            continue
        for cmd in cmds:
            p = os.path.join(ctx.root, 'plugins/flow/commands', f'{cmd}.md')
            if not os.path.exists(p):
                r.fail(f"없는 커맨드를 가리킨다 — gate.exemptions `{eid}` 의 `whoFills` 가 "
                       f"`/flow:{cmd}` 를 적었는데 commands/{cmd}.md 가 없다")
                continue
            if ck not in ctx.read(p):
                r.fail(f"커맨드가 그 키를 말하지 않는다 — gate.exemptions `{eid}` 는 "
                       f"`/flow:{cmd}` 가 `{ck}` 를 채운다고 적었는데 commands/{cmd}.md 에 "
                       f"그 키가 없다 (데이터만 가리키면 그게 D2 다)")
    return r


# ── 커맨드가 표시하는 등급·시점 ↔ topology ──
# 게이트 절은 손으로 쓴다(생성물이 아니다). 그래서 topology 에서 등급을 내려도 본문은
# 그대로 남는다 — H1 이 정확히 그 상태였다(5곳이 "기계"라 적혔는데 훅은 안 봄).
#
# **표와 불릿 두 형식을 다 본다.** 한 형식만 보면 다른 형식이 탈출구가 된다 —
# 실제로 표만 보게 짰더니 `verify`·`sync` 의 불릿 거짓 표시가 그대로 통과했다.
#
# **`내용` 에는 시점을 함께 적는다** — `내용 · 진입` 또는 `내용 · 퇴장`. D5 는 데이터만의
# 결함이 아니었다: 본문도 퇴장 조건을 진입 절에 적어 두었고, **사용자는 본문을 읽는다.**
# 시점을 안 적으면 읽는 쪽은 시작할 때 판정하는 것으로 읽는다.
# `기계`·`약속` 에는 붙이지 않는다 — 훅은 도구 호출마다 보고 약속은 판정 시점이 없다.
GRADE_LABEL = {'machine': '기계', 'content': '내용', 'promise': '약속'}
LABEL_GRADE = {v: k for k, v in GRADE_LABEL.items()}
WHEN_LABEL = {'entry': '진입', 'exit': '퇴장'}
LABEL_WHEN = {v: k for k, v in WHEN_LABEL.items()}
GATE_HEAD = re.compile(r'^##+\s+(?:게이트|진입 조건)')
GRADE_TXT = r'(기계|내용|약속)(?:\s*·\s*(진입|퇴장))?'
GRADE_BULLET = re.compile(r'^\s*[-*]\s*\*\*' + GRADE_TXT + r'\*\*')
# **`없다` 는 구분자 바로 뒤에 올 때만 '없다는 선언'이다.** 문장 아무 데서나 찾으면
# `…판정 독립성이 없다` 같은 서술이 선언으로 읽힌다(실제로 build 가 그렇게 오판됐다).
GRADE_NONE = re.compile(r'^\s*[-*]\s*\*\*' + GRADE_TXT + r'\*\*\s*[—–-]\s*없다')


def _slot_grades(c):
    """(등급, 시점) → 그 자리의 항목 수. 시점은 `content` 에만 있다(다른 등급은 None)."""
    out = {}
    for g in ('machine', 'promise'):
        n = len((c.get('entry') or {}).get(g) or [])
        if n:
            out[(g, None)] = n
    for slot in ('entry', 'exit'):
        n = len((c.get(slot) or {}).get('content') or [])
        if n:
            out[('content', slot)] = n
    return out


def _show(g, when):
    return GRADE_LABEL[g] + (f" · {WHEN_LABEL[when]}" if when else '')


def _gate_labels(ctx, p):
    """게이트 절의 등급 라벨 — [(등급, 시점 또는 None, 없다는 선언인가)] · 절이 없으면 None."""
    L = ctx.lines(p)
    fenced = fenced_map(L)
    start = next((i for i, l in enumerate(L)
                  if not fenced[i] and GATE_HEAD.match(l)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(L))
                if not fenced[i] and L[i].startswith('## ')), len(L))
    out = []
    for i in range(start, end):
        if fenced[i]:
            continue
        l = L[i]
        m = GRADE_BULLET.match(l)
        if m:
            out.append((LABEL_GRADE[m.group(1)], LABEL_WHEN.get(m.group(2) or ''),
                        bool(GRADE_NONE.match(l))))
            continue
        if l.startswith('|') and not SEP.match(l):
            first = re.sub(r'[`*]', '', l.strip('|').split('|')[0]).strip()
            cm = re.fullmatch(GRADE_TXT, first)
            if cm:
                out.append((LABEL_GRADE[cm.group(1)], LABEL_WHEN.get(cm.group(2) or ''),
                            False))
    return out


# ── 본문이 내용 조건의 시점을 적나 ──
# **D5 는 데이터만의 결함이 아니었다.** 커맨드 본문도 퇴장 조건을 `진입 조건` 절에 적어
# 두었고, **사용자는 데이터가 아니라 본문을 읽는다.** 시점을 안 적으면 읽는 쪽은 시작할 때
# 판정하는 것으로 읽는다 — `machine` 이 아닌 것을 `기계` 라 적던 H1 과 같은 종류의 거짓이다.
#
# `기계`·`약속` 에는 붙이지 않는다 — 훅은 도구 호출마다 보고, 약속은 판정하는 자가 없어
# 시점이 없다. 없는 시점을 적는 것도 거짓 표시다.
#
# **`entry-grade-parity` 와 가른 이유** — 한 id 에 묶으면 위반 픽스처가 한 규칙만 건드려도
# 통과라 나머지가 사문화돼도 테스트가 못 잡는다(T1 이 검사를 넷으로 가른 것과 같은 이유).
@check('gate-timing-shown', '본문의 내용 조건 시점 표시',
       '퇴장 조건을 시점 없이 적어 시작할 때 판정하는 것으로 읽히는 것 (D5)')
def _gate_timing_shown(ctx):
    r = Result(unit='등급 표시')
    for p in ctx.commands():
        labels = _gate_labels(ctx, p)
        for g, w, is_none in labels or []:
            r.targets += 1
            if g == 'content' and not w and not is_none:
                r.fail(f"시점 표시 없음 {ctx.rel(p)} — `내용` 을 적었는데 `진입`·`퇴장` "
                       f"어느 쪽인지 없다 (`내용 · 퇴장` 처럼 적는다. 안 적으면 읽는 쪽은 "
                       f"시작할 때 판정하는 것으로 읽는다 — D5 가 그 자리다)")
            elif g != 'content' and w:
                r.fail(f"시점을 붙일 수 없는 등급 {ctx.rel(p)} — "
                       f"`{GRADE_LABEL[g]} · {WHEN_LABEL[w]}` 이라 적었다. 훅은 도구 호출마다 "
                       f"보고 약속은 판정 시점이 없다 — 시점은 `내용` 에만 붙인다")
    return r


@check('entry-grade-parity', '커맨드 등급·시점 표시 ↔ topology',
       '등급을 내려도 커맨드 본문에 기계로 남는 것 · 퇴장 조건을 진입이라 적는 것 (H1 · D5)')
def _entry_grade_parity(ctx):
    r = Result(unit='커맨드')
    tp = os.path.join(ctx.root, 'plugins/flow/flow.topology.json')
    if not os.path.exists(tp):
        return r
    try:
        topo = json.loads(ctx.read(tp))
    except json.JSONDecodeError:
        return r
    cmds = topo.get('commands') or {}

    for p in ctx.commands():
        name = os.path.basename(p)[:-3]
        c = cmds.get(name)
        if not c:
            continue
        actual = _slot_grades(c)
        labels = _gate_labels(ctx, p)
        if labels is None:
            # 기계라고 데이터에 적었으면 **보여 줘야** 한다. 절을 지워서 대조를 피하는 길을 막는다.
            if (c.get('entry') or {}).get('machine'):
                r.targets += 1
                r.fail(f"게이트 절 없음 {ctx.rel(p)} — topology 는 `entry.machine` 이 "
                       f"{len(c['entry']['machine'])}개라고 적는데 본문에 게이트 절이 없다 "
                       f"(기계로 막히는 것은 사용자에게 보여야 한다)")
            continue
        r.targets += 1

        claimed, denied = set(), set()
        for g, w, is_none in labels:
            if g == 'content' and not w:
                # 시점을 안 적은 라벨 — 그 흠은 `gate-timing-shown` 이 잡는다.
                # 여기서는 **등급이 있나 없나** 만 본다: `- **내용** — 없다` 는 두 시점 다
                # 없다는 선언이고, 그냥 `내용` 은 데이터에 있는 시점을 가리킨 것으로 읽는다.
                # 데이터에 아무 내용 조건도 없으면 거짓 표시로 떨어진다.
                if is_none:
                    denied.update({('content', 'entry'), ('content', 'exit')})
                    continue
                present = [x for x in ('entry', 'exit') if ('content', x) in actual]
                claimed.update({('content', x) for x in present} or {('content', None)})
                continue
            (denied if is_none else claimed).add((g, w))

        _k = lambda x: (x[0], x[1] or '')      # None 과 str 을 비교하면 TypeError 다
        for key in sorted(claimed - set(actual), key=_k):
            g, w = key
            dotted = f"{w or 'entry'}.{g}"
            r.fail(f"거짓 등급 표시 {ctx.rel(p)} — 본문은 `{_show(g, w)}` 이라 적는데 "
                   f"topology 의 `{dotted}` 가 비었다 (아무도 판정하지 않는 것을 판정한다고 "
                   f"적는 것이 거짓 표시다 — 내렸거나 시점을 옮겼으면 본문도 따라간다)")
        for key in sorted(set(actual) - claimed - denied, key=_k):
            g, w = key
            r.fail(f"등급 누락 {ctx.rel(p)} — topology 의 `{w or 'entry'}.{g}` 에 "
                   f"{actual[key]}개가 있는데 본문이 `{_show(g, w)}` 을 안 적는다")
        for key in sorted(denied & set(actual), key=_k):
            g, w = key
            r.fail(f"없다고 적었는데 있다 {ctx.rel(p)} — 본문은 `{_show(g, w)}` 이 없다고 "
                   f"적는데 topology 의 `{w or 'entry'}.{g}` 에 {actual[key]}개가 있다")
    return r


# ═══════════════════════════════════════════════════════════════════
# 늦게 되찾은 검사들
#
# 아래 다섯은 첫 이식에서 빠졌다가 되돌림 실험으로 전부 미탐임을 확인하고 되살린 것이다.
#
# **절 참조 금지는 두지 않는다.** 그 규칙은 스킬이 통째로 실릴 때만 뜻이 있다 — 그때는
# 절 이름이 정보를 안 주고 깨질 자리만 만든다. 지금은 조각을 낱개로 싣는다. `` `traceability` 의 `level` `` 은 금지할 참조가 아니라
# **주소**다. 대신 그 주소가 실재하는지를 본다 (`fragment-reference-exists`).
# ═══════════════════════════════════════════════════════════════════

FM_FILES = ('plugins/flow/commands/*.md', 'plugins/flow/agents/*.md',
            'plugins/flow/skills/*/SKILL.md')


@check('frontmatter-lowercase', 'frontmatter 키 소문자',
       '대문자 키를 Claude Code 가 못 읽어 커맨드·스킬이 안 뜬다')
def _frontmatter_lowercase(ctx):
    # `argument-hint-quoted` 와 같은 사고 계열이다 — **파일이 통째로 안 뜨고 조용하다.**
    # 그쪽만 이식되고 이쪽이 빠져 있었다.
    r = Result(unit='키')
    for f in ctx.paths(*FM_FILES):
        s = ctx.read(f)
        if not s.startswith('---'):
            r.targets += 1
            r.fail(f"frontmatter 없음 {ctx.rel(f)} — `---` 로 시작해야 파일이 뜬다")
            continue
        for k in re.findall(r'^([A-Za-z-]+):', s.split('---')[1], re.M):
            r.targets += 1
            if k != k.lower():
                r.fail(f"frontmatter 대문자 키 {ctx.rel(f)} — `{k}` "
                       f"(소문자로. Claude Code 가 못 읽어 안 뜬다)")
    return r


def _anchors(path):
    """헤딩 → GitHub 앵커. 기호를 떼고 소문자·공백을 `-` 로."""
    out = set()
    try:
        with open(path, encoding='utf-8') as fh:
            for l in fh:
                m = re.match(r'#{1,6}\s+(.*)', l)
                if m:
                    t = re.sub(r'[`*\[\]():.,—·?/\\]', '', m.group(1).strip())
                    out.add(t.lower().replace(' ', '-'))
    except OSError:
        pass
    return out


@check('link-target-exists', '링크 대상·앵커 실존',
       '헤딩 이름을 바꾸면 링크가 조용히 깨진다')
def _link_target_exists(ctx):
    r = Result(unit='링크')
    for f in ctx.render_files():
        s = ctx.read(f)
        d = os.path.dirname(f)
        for m in re.finditer(r'\]\(([^)]+)\)', s):
            u = m.group(1)
            if u.startswith(('http', '#', 'mailto:')):
                continue
            path, _, frag = u.partition('#')
            r.targets += 1
            tgt = os.path.normpath(os.path.join(d, path)) if path else f
            ln = 1 + s[:m.start()].count('\n')
            if not os.path.exists(tgt):
                r.fail(f"링크 대상 없음 {ctx.rel(f)}:{ln} — {u}")
            elif frag and frag.lower() not in _anchors(tgt):
                r.fail(f"앵커 없음 {ctx.rel(f)}:{ln} — {u} (헤딩 이름이 바뀌었나)")
    return r


def _uncoded(line):
    """인라인 코드(`` `…` ``)를 지운 줄. 백틱 안은 **인용**이라 대상이 아니다."""
    return re.sub(r'`[^`]*`', '', line)


@check('placeholder-leak', '자리표시자 유출',
       '템플릿 밖의 `{{ }}` 를 사용자가 내용으로 읽는다')
def _placeholder_leak(ctx):
    # "자리표시자를 설명하는 줄"을 낱말 목록으로 빼지 않는다. 그 목록은 늘 모자란다 —
    # 이 repo 만 해도 그 목록에 없는 형태로 일곱 곳이 자리표시자를 **인용**한다.
    # 백틱이 그 판정을 대신한다. 사용자가 내용으로 읽는 것은 **백틱 밖에 맨몸으로 있는 것**이다.
    r = Result(unit='자리표시자')
    for f in ctx.instruction_files():
        rel = ctx.rel(f)
        if 'project-template' in rel:
            continue                      # 사람이 채우는 골격이다. 거기 있는 것이 정상
        for i, l in enumerate(ctx.lines(f), 1):
            for _ in re.finditer(r'\{\{.*?\}\}', l):
                r.targets += 1
            bare = _uncoded(l)
            if re.search(r'\{\{.*?\}\}', bare):
                r.fail(f"자리표시자 유출 {rel}:{i} — {bare.strip()[:60]} "
                       f"(인용이면 백틱으로 감싼다)")
    return r


FRAG_REF = re.compile(r'`([a-z][a-z0-9-]*)`\s*의\s*`([^`]+)`')


@check('fragment-reference-exists', '산문이 가리킨 조각 실존',
       '없는 조각을 가리키면 그 자리에서 읽을 것이 사라진다')
def _fragment_reference_exists(ctx):
    # `command-loads-parity` 는 `## 연결` **표**만 본다. 절차·에이전트 본문의 산문 참조는
    # 아무도 안 봤다 — 조각 이름을 바꾸면 그쪽이 조용히 죽는다.
    r = Result(unit='조각 참조')
    skills = {os.path.basename(os.path.dirname(p)) for p in ctx.skills()}
    have = {f"{os.path.basename(os.path.dirname(os.path.dirname(p)))}/"
            f"{os.path.basename(p)[:-3]}"
            for p in ctx.paths('plugins/flow/skills/*/references/*.md')}
    for f in ctx.instruction_files():
        for i, l in enumerate(ctx.lines(f), 1):
            for who, frag in FRAG_REF.findall(l):
                # 스킬 이름이 아니면 조각 참조가 아니다 — 도메인 예시(`approval` 의 `DR-*`) 등
                if who not in skills:
                    continue
                r.targets += 1
                if f"{who}/{frag}" not in have:
                    r.fail(f"없는 조각 {ctx.rel(f)}:{i} — `{who}` 의 `{frag}` "
                           f"(`skills/{who}/references/{frag}.md` 가 없다)")
    return r


@check('plantuml-pragma', 'PlantUML 렌더 전제',
       '`!pragma layout smetana` 가 없으면 Graphviz 없이 안 그려진다')
def _plantuml_pragma(ctx):
    r = Result(unit='블록')
    for f in ctx.render_files():
        s = ctx.read(f)
        for m in re.finditer(r'```plantuml\n(.*?)```', s, re.S):
            r.targets += 1
            if 'pragma layout smetana' not in m.group(1):
                ln = s[:m.start()].count('\n') + 1
                r.fail(f"PlantUML {ctx.rel(f)}:{ln} — `!pragma layout smetana` 없음 "
                       f"(Graphviz 없이 렌더 안 됨)")
    return r


FLUFF = re.compile(r'(?<![가-힣])(매우|아주|정말|굉장히|훨씬|상당히|다양한|여러가지|손쉽게'
                   r'|간편하게|효율적으로|효과적으로|최적화된|강력한|유연한|풍부한|성공적으로'
                   r'|원활하게)(?![가-힣])')


@check('fluff', '미사여구',
       '뜻을 안 더하는 강조가 지시서에 실린다 (`plain-writing`)')
def _fluff(ctx):
    r = Result(unit='줄')
    for f in ctx.instruction_files():
        rel = ctx.rel(f)
        # 규칙을 적는 스킬 자신은 금지어를 예로 들 수밖에 없다
        if 'skills/plain-writing/' in rel:
            continue
        L = ctx.lines(f)
        fenced = fenced_map(L)
        for i, l in enumerate(L, 1):
            if fenced[i - 1] or not l.strip():
                continue
            r.targets += 1
            m = FLUFF.search(l)
            if m:
                r.fail(f"미사여구 {rel}:{i} — `{m.group(1)}` "
                       f"(`plain-writing` — 뜻을 안 더하면 지운다)")
    return r


# ── 배포되는 것과 git 에 있는 것 ──
# **다른 검사는 전부 디스크를 본다.** 그래서 디스크엔 있고 git 엔 없는 파일을 아무도 못 잡는다 —
# 검사기는 초록인데 **배포본에서만 사라진다.** 실제로 그랬다:
# 사용자 전역 `~/.gitignore_global` 의 `build/` 가 `procedures/build/` 조각 둘을 삼켰고,
# `fragment-reference-exists`·`command-loads-parity` 는 디스크를 보므로 통과했다.
# `project-template/.claude/` 도 같은 형태로 잃을 뻔했다(`.gitignore` 의 되살리기 규칙).
@check('plugin-files-tracked', '배포 파일이 git 에 있나',
       '전역 gitignore 가 삼키면 검사기는 통과하는데 배포본에서 사라진다')
def _plugin_files_tracked(ctx):
    import subprocess
    r = Result(unit='파일')
    root = ctx.root
    if not os.path.isdir(os.path.join(root, '.git')):
        return r                      # git repo 가 아니면 판정할 것이 없다
    try:
        out = subprocess.run(['git', '-C', root, 'ls-files', '--cached', '--others',
                              '--exclude-standard', 'plugins'],
                             capture_output=True, text=True, timeout=30)
        listed = {l for l in out.stdout.split('\n') if l.strip()}
        cached = subprocess.run(['git', '-C', root, 'ls-files', '--cached', 'plugins'],
                                capture_output=True, text=True, timeout=30)
        tracked = {l for l in cached.stdout.split('\n') if l.strip()}
    except (OSError, subprocess.SubprocessError) as e:
        return broken(f"git 을 부르지 못했다 ({type(e).__name__})", unit='파일')

    for dirpath, dirnames, filenames in os.walk(os.path.join(root, 'plugins')):
        dirnames[:] = [d for d in dirnames if d not in ('.git', '__pycache__')]
        for fn in filenames:
            if fn == '.DS_Store':
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, '/')
            r.targets += 1
            if rel in tracked:
                continue
            # `listed` 에 있으면 무시된 게 아니라 그냥 아직 add 안 한 새 파일이다 — 그것도 못 나간다
            why = ('아직 `git add` 안 됨' if rel in listed
                   else '**gitignore 가 삼켰다** — `.gitignore` 에 되살리는 규칙을 넣는다')
            r.fail(f"배포 누락 {rel} — git 이 추적하지 않는다 ({why})")
    return r


# ── 선언한 조각을 읽으라고 지시하나 ──
# **`## 연결` 의 표는 배선 선언이고 지시가 아니다.** 실측에서 `build` 가 선언한 조각 7개 중
# 하나도 안 읽고 구현·검증을 끝냈다. 조각을 절차 중간의 괄호로만 가리켜 *"정본이 어디 있다"* 는
# 인용으로 읽혔기 때문이다. 읽으라는 절을 세우고 다시 돌리니 **0/7 → 7/7 이 두 번 재현됐다.**
#
# **간접도 인정한다** — `design` 은 조각을 자기 절에 적지 않고 절차 조각에 맡기는데(그 절차가
# 조각을 지시한다) 실측에서 7개를 읽었다. 그래서 커맨드 본문 **또는 그 커맨드가 싣는 절차 조각**에서
# 이름이 불리면 통과다. 한 방식을 강요하지 않는다.
@check('fragment-read-instructed', '선언한 조각에 읽기 지시가 있나',
       '표에만 있으면 지시로 읽히지 않는다 — 실측에서 0/7 이 났다')
def _fragment_read_instructed(ctx):
    # **범위가 이 검사의 전부다.** 처음에 본문 전체에서 이름을 찾게 만들었더니
    # `## 연결` 표가 그 조건을 이미 만족시켜 **사보타주가 통과했다** — 읽기 목록을 24줄 지워도
    # 초록이었다. 그게 사문화된 검사의 형태다.
    # 그래서 **읽기 절 안** 과 **그 커맨드가 싣는 절차 조각** 만 본다. 표는 세지 않는다.
    r = Result(unit='조각')
    topo = _topo(ctx)
    if not topo:
        return r
    for p in ctx.commands():
        name = os.path.basename(p)[:-3]
        c = (topo.get('commands') or {}).get(name) or {}
        loads = c.get('loads') or {}
        want = set()
        for m in (loads.get('modes') or {None: loads}).values():
            if not isinstance(m, dict):
                continue
            want |= set(m.get('fragments') or [])
            want |= set(m.get('conditional') or {})
        if not want:
            continue

        # 읽기 절 — `###` 제목에 `읽` 이 든 절의 본문. 없으면 그 자체가 실패다.
        L = ctx.lines(p)
        st = next((i for i, l in enumerate(L)
                   if re.match(r'^###\s', l) and '읽' in l), None)
        if st is None:
            r.targets += len(want)
            r.fail(f"읽기 절 없음 {ctx.rel(p)} — 조각 {len(want)}개를 선언했는데 "
                   f"`### … 읽는다` 절이 없다 (표는 지시가 아니다)")
            continue
        en = next((i for i in range(st + 1, len(L)) if L[i].startswith('### ')), len(L))
        hay = '\n'.join(L[st:en])
        # **간접을 인정한다** — `design` 은 조각을 절차 조각에 맡기고 실측에서 7개를 읽었다.
        for pr in (c.get('procedures') or []):
            fp = os.path.join(ctx.root, f'plugins/flow/procedures/{pr}.md')
            if os.path.isfile(fp):
                hay += '\n' + ctx.read(fp)

        for f in sorted(want):
            r.targets += 1
            if f.split('/')[1] not in hay:
                r.fail(f"읽기 지시 부재 {ctx.rel(p)} — `{f}` 를 선언했는데 읽기 절도 "
                       f"절차 조각도 이름으로 가리키지 않는다")
    return r

# ── 어휘 정본이 실재하나 ──
# `doc-verify/vocabulary` 가 *값 집합 → 정본 조각* 지도를 갖는다. **지도가 낡으면 대조가 거짓이 된다** —
# 정본 조각에서 값이 빠졌는데 지도는 그대로면, 채점이 "정본에 있다" 고 믿고 넘어간다.
# 그래서 지도의 각 행을 **그 조각이 실제로 그 값들을 담고 있나**로 대조한다.
# 지도 자체가 F2(조각 미적재)를 산출물 쪽에서 잡으려고 만든 것이라, 지도가 썩으면 그 방어가 사라진다.
VOCAB = 'plugins/flow/skills/doc-verify/references/vocabulary.md'


@check('vocabulary-canon', '어휘 지도 ↔ 정본 조각',
       '지도가 낡으면 값 대조가 거짓이 된다 (F2 를 산출물 쪽에서 잡는 유일한 길)')
def _vocabulary_canon(ctx):
    r = Result(unit='값 집합')
    vp = os.path.join(ctx.root, VOCAB)
    if not os.path.isfile(vp):
        return r
    rows = [l for l in ctx.lines(vp) if l.startswith('|') and not SEP.match(l)]
    for l in rows[1:]:                       # 머리글 제외
        cells = [c.strip() for c in l.strip('|').split('|')]
        if len(cells) < 3:
            continue
        values, canon = cells[1], cells[2]
        # 정본 칸에서 조각 이름을 뽑는다 — `skills/x/references/y.md` 든 `x/y` 든
        m = re.search(r'`([a-z-]+)/([a-z-]+)`', canon)
        if not m:
            continue                          # topology 를 정본으로 적은 행 등은 대상이 아니다
        r.targets += 1
        fp = os.path.join(ctx.root, f'plugins/flow/skills/{m.group(1)}/references/{m.group(2)}.md')
        if not os.path.isfile(fp):
            r.fail(f"어휘 정본 없음 {VOCAB} — `{m.group(1)}/{m.group(2)}` 가 디스크에 없다")
            continue
        body = ctx.read(fp)
        # 값 칸의 백틱·굵게 안 토큰이 그 조각에 실제로 있나
        toks = [t for t in re.findall(r'`([^`]+)`|\*\*([^*]+)\*\*', values)]
        toks = [a or b for a, b in toks]
        # 설명 토큰(`표기 없음(=선택)` 처럼 괄호가 든 것)은 값이 아니다
        toks = [t for t in toks if '(' not in t and t not in ('비움',)]
        miss = [t for t in toks if t not in body]
        if miss:
            r.fail(f"어휘 정본에 값이 없다 {m.group(1)}/{m.group(2)} — {miss} "
                   f"(지도는 이 조각을 정본이라 적는다. 값이 옮겨졌으면 지도를 고친다)")
    return r


# ── 실행 ──

def run(ctx, only=None):
    """검사를 돌린다. **검사 하나가 고장나도 나머지는 돈다 — 스택 트레이스로 죽지 않는다.**

    검사기가 크래시하면 어느 검사가 사문화됐는지 이름으로 지목할 수 없다.
    그래서 고장을 예외로 흘리지 않고 `Result.error` 에 담아 판정 자리에 올린다.
    """
    out = []
    for c in [c for c in CHECKS if not only or c.id in only]:
        try:
            r = c.fn(ctx)
        except Exception as e:                       # 검사기 고장을 판정으로 바꾼다
            tb = traceback.extract_tb(sys.exc_info()[2])
            where = f"{os.path.basename(tb[-1].filename)}:{tb[-1].lineno}" if tb else '?'
            r = broken(f"{type(e).__name__}: {e} @ {where}")
        else:
            if r is None:
                r = broken('None 을 돌려줬다 — 몸통이 사라졌나 (`return` 이 앞에 붙었나)')
            elif not isinstance(r, Result):
                r = broken(f"Result 가 아닌 {type(r).__name__} 을 돌려줬다")
        out.append((c, r))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='문서 정합 검사 (flow)')
    ap.add_argument('--root', default=REPO, help='검사할 루트 (기본: repo)')
    ap.add_argument('--list', action='store_true', help='검사 목록을 JSON 으로 출력')
    ap.add_argument('--only', action='append', default=[], help='이 검사만 (여러 번)')
    ap.add_argument('--json', dest='as_json', action='store_true', help='결과를 JSON 으로')
    ap.add_argument('--strict-targets', action='store_true',
                    help='대상 0건인 검사도 실패로 본다')
    a = ap.parse_args(argv)

    if a.list:
        print(json.dumps([{'id': c.id, 'title': c.title, 'why': c.why} for c in CHECKS],
                         ensure_ascii=False, indent=2))
        return 0

    known = {c.id for c in CHECKS}
    unknown = [x for x in a.only if x not in known]
    if unknown:
        # 조용히 0건 통과하면 테스트가 오타를 못 잡는다 — 하드 에러다
        print(f"없는 검사 id: {', '.join(unknown)}", file=sys.stderr)
        print(f"있는 것: {', '.join(sorted(known))}", file=sys.stderr)
        return 2

    ctx = Ctx(a.root)
    results = run(ctx, set(a.only) or None)
    sick = [c.id for c, r in results if r.error]
    failed = sum(len(r.findings) for _, r in results)
    empty = [c.id for c, r in results if r.targets == 0 and not r.error]

    if a.as_json:
        print(json.dumps({
            'root': ctx.root,
            'checks': [{'id': c.id, 'title': c.title, 'unit': r.unit,
                        'targets': r.targets, 'findings': r.findings,
                        'error': r.error}
                       for c, r in results],
            'failed': failed,
            'zero_target': empty,
            'broken': sick,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"문서 정합 검사 — 루트 {ctx.root}")
        for c, r in results:
            n = f"대상 {r.targets} {r.unit}"
            if r.error:
                print(f"  💥 {c.id} — **검사기 고장**: {r.error}")
                print(f"       ({c.title} — 판정을 내지 못했다. 통과도 실패도 아니다)")
            elif r.findings:
                print(f"  ❌ {c.id} — {c.title} · {n} · 실패 {len(r.findings)}")
                for x in r.findings:
                    print(f"       {x}")
            elif r.targets == 0:
                print(f"  ⚠️  {c.id} — {c.title} · {n} · "
                      f"**검사가 아무것도 안 봤다** (통과가 아니다)")
            else:
                print(f"  ✅ {c.id} — {c.title} · {n}")
        bad = {c.id for c, r in results if r.findings}
        ok = len(results) - len(bad) - len(empty) - len(sick)
        print(f"\n검사 {len(results)} · 통과 {ok} · 대상 0건 {len(empty)} · "
              f"실패 {failed} · 검사기 고장 {len(sick)}")
        if empty:
            print(f"  대상 0건: {', '.join(empty)} — 그 층의 파일이 아직 없다는 뜻이다")
        if sick:
            print(f"  검사기 고장: {', '.join(sick)} — 이 검사의 판정은 없다. "
                  f"문서가 맞는지와 무관하게 검사기를 먼저 고친다")

    # 고장이 먼저다 — 판정을 못 낸 검사가 있으면 문서 통과 여부는 신뢰할 수 없다
    if sick:
        return 3
    if failed:
        return 1
    if a.strict_targets and empty:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
