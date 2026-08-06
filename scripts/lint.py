#!/usr/bin/env python3
"""문서 정합 검사 — 눈으로는 안 보이고 grep 으로도 안 걸리는 것들.

v1 `lint-docs.py` 653줄에서 **진단이 값어치를 확인한 검사만** 옮겼다
(`doc/00.diagnosis/diag-C-infra.md` 1절). 버린 것은 4절·2절 근거다 —
사문화된 검사(v1 검사 4의 에이전트·스킬 화이트리스트 22개)와
유지비가 안 맞는 검사(v1 검사 7 갯수 표기).

구조 — 검사는 `@check` 로 등록한다. 등록하면 `--list` 에 뜨고,
`lint.test.py` 가 그 목록을 읽어 **픽스처 없는 검사를 실패로 만든다.**
검사를 더하고 테스트를 안 붙이는 길이 없다.

각 검사는 걸린 것과 함께 **본 대상 수**를 돌려준다. 대상이 0건이면 통과가 아니라
`대상 0건` 으로 따로 적는다 — v1 은 대상 0건과 전부 통과를 구별하지 못했다.

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
# v1 은 범위가 하나여서 이 구분이 없었다. `doc/` (설계·진단 기록)은 렌더 범위에만 든다.
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
    펜스 안은 렌더될 때 표가 아니라 글자라 대상이 아니다(v1 은 검사 넷 중 둘만 이걸 봤다).
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
       '이스케이프 안 된 `|` 가 행을 깨뜨린다 (diag-C 1절 · v1 검사 1)')
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
       '표 사이에 글이 껴 뒤 행이 표 밖으로 나간다 (diag-C 1절 · v1 검사 1-1)')
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
       '표 바로 뒤 불릿·문단이 마지막 칸에 흡수된다 (diag-C 1절 · v1 검사 1-1b)')
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
       '빈 줄로 끊겨 뒷조각이 머리글을 잃는다 (diag-C 1절 · v1 검사 1-1c)')
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
# 안 감싸면 **파일이 통째로 안 뜬다.** v1 은 이 사고를 yaml 파싱 검사(검사 6-1)와 따로 뽑아 뒀다 —
# 그쪽은 `import yaml` 이 실패하면 통째로 꺼지기 때문이다(diag-C 1절). v2 는 yaml 을 아예 안 쓴다.
@check('argument-hint-quoted', 'argument-hint 따옴표',
       '안 감싸면 커맨드 파일이 안 뜬다 (diag-C 1절 · v1 검사 6-2)')
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


def _desc(ctx, path):
    """frontmatter 의 description. folded(`>-`) 도 이어 붙여 한 줄로.

    한 물리 줄만 읽으면 folded 에서는 `>-` 만 잡혀 **검사가 조용히 꺼진다**(v1 이 그 사고를 겪었다).
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


# ── 출력 형식 ↔ 템플릿 왕복 (v1 검사 10 · 10-1) ──
# 스킬의 `출력 형식` 절이 지시한 절 이름과 그 템플릿의 절이 어긋나면,
# 그대로 만든 문서가 `doc-verify` 채점에서 FAIL 이다. 그 인과가 실제로 있었다(diag-C 1절).
#
# v1 은 스킬↔템플릿 짝을 **스크립트 안에 손으로 열거**했다(`OUT_TPL`·`MULTI`·`ROUNDTRIP`).
# 그게 diag-C 4절이 말하는 그 병이다 — 정본이 둘. v2 는 `flow.topology.json` 의
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
# **`SKILL.md` 만 스캔하면 안 된다.** v2 는 출력 형식을 `references/` 조각으로 내렸다 —
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
       '스킬이 이름을 지어내면 생성 문서가 채점에서 미등재다 (diag-C 1절 · v1 검사 10)')
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
       '이름 대조만으로는 빠진 절을 못 본다 (diag-C 1절 · v1 검사 10-1)')
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


# ── 스킬 간 중복 ──
# 정본이 둘이 되면 한쪽만 고쳐진다. 이걸 기계로 지키는 유일한 장치다(diag-C 1절 · v1 검사 11).
DUP_RATIO = 0.85


def _outside(ctx, p):
    out, fence = [], False
    for i, l in enumerate(ctx.lines(p), 1):
        if l.lstrip().startswith('```'):
            fence = not fence
            continue
        if not fence:
            out.append((i, l))
    return out


@check('skill-duplication', '스킬 간 중복',
       '정본이 둘이 되면 한쪽만 고쳐진다 (diag-C 1절 · v1 검사 11 · SequenceMatcher ≥ 0.85)')
def _skill_duplication(ctx):
    r = Result(unit='스킬')
    src = {}
    for p in ctx.skills():
        n = os.path.basename(os.path.dirname(p))
        lines = [re.sub(r'\s+', ' ', re.sub(r'[`*|]', '', l).strip(' -'))
                 for _, l in _outside(ctx, p)
                 if l.strip().startswith(('- ', '| ')) and len(l.strip()) > 34]
        if lines:
            src[n] = lines
            r.targets += 1

    def nz(s):
        return re.sub(r'[^가-힣a-zA-Z0-9]', '', s)

    keys = sorted(src)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            for x in src[a]:
                for y in src[b]:
                    if SequenceMatcher(None, nz(x), nz(y)).ratio() >= DUP_RATIO:
                        r.fail(f"스킬 간 중복 [{a}]↔[{b}] — {x[:52]} "
                               f"(정본 하나를 정하고 다른 쪽은 이름으로 가리킨다)")
    return r


# ── 절 이름에 번호·라벨이 붙었나 ──
# 절을 하나 더하면 밖에서 번호로 가리킨 줄이 조용히 어긋난다. v1 에서 실제로 그랬다(v1 검사 8-1).
# 산문·프롬프트 안의 번호는 대상이 아니다 — `N단계` 는 순서가 뜻이다.
# 템플릿(`03.templates/`)은 사람이 절 번호로 자리를 찾는 골격이라 뺀다.
LABELED = re.compile(r'^#{2,4}\s+(?:[0-9]+\s*[.)]|[①-⑳]|절차\s+[A-Z0-9])')
HEADING = re.compile(r'^#{2,4}\s+\S')


@check('section-label', '절 이름 번호·라벨 금지',
       '절을 하나 더하면 번호로 가리킨 참조가 조용히 어긋난다 (v1 검사 8-1)')
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
# 검출기 실행이 약속이면 v1 의 병이 데이터 층에서 반복된다 — 그래서 이 검사가 CI 에서 돈다.

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
    if not limits:
        r.fail(f"머리말에 `limit:` 줄이 하나도 없다 — v1 은 목록에서 빠진 것을 "
               f"한계로도 안 적어 문서가 실제 방어보다 넓게 읽혔다 (diag-C 3절)")
    return r


# ── 두 매니페스트의 version 일치 ──
# 어긋난 채 올리면 **한쪽만 바뀌는데 스크립트는 성공했다고 말한다.** 설치측은 marketplace.json 을
# 보므로 업데이트가 전달되지 않는다(diag-C 1절). description 은 생성물이라 위 검사가 본다.

@check('manifest-version-parity', '두 매니페스트 version 일치',
       '어긋난 채 버전을 올리면 설치측에 업데이트가 전달되지 않는다 (diag-C 1절)')
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
TOPO_CMD_KEYS = ('order', 'phase', 'after', 'next', 'entry', 'loads', 'procedures')
TOPO_ENTRY_KEYS = ('machine', 'content', 'promise')


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
        e = c.get('entry')
        if isinstance(e, dict):
            for k in TOPO_ENTRY_KEYS:
                if k not in e:
                    r.fail(f"진입 조건 등급이 빠졌다 — commands.{name}.entry.{k} "
                           f"(없는 등급은 빈 배열로 적는다. 등급을 섞지 않는 것이 이 파일의 일이다)")
        elif 'entry' in c:
            r.fail(f"commands.{name}.entry 가 객체가 아니다")

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
# v1 최다 실측 결함이 여기였다 — `## 연결` 절이 본문과 15+23건 어긋났는데 **검사기는 세 줄의
# 존재만 봤다**(diag-A 2절). 존재 검사는 어긋남을 못 본다. 그래서 정본과 낱낱이 대조한다.
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
       'v1 최다 실측 결함 — 연결 절이 본문과 15+23건 어긋났고 검사기는 존재만 봤다 (diag-A 2절)')
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
            miss, cmiss, unmarked, extra = [], [], [], []

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
    return r


# ── gatekeeper 위임 지시가 있나 ──
# v1 최대 결함 — 게이트를 4곳이 약속하고 실제로 거는 곳은 하나였다(diag-A 4절).
# `entry.content` 는 **gatekeeper 가 판정하는 등급**이다. 그런데 부르는 것 자체는 약속이라
# 기계가 못 막는다. 막을 수 있는 것은 **부르라는 지시가 본문에 있나** 까지다.
#
# `entry.content` 가 빈 커맨드에는 걸지 않는다 — 부를 것이 없는 게 정상이고,
# 없는 것을 요구하면 커맨드가 게이트를 발명하게 된다.
GK_CALL = re.compile(r'gatekeeper`?\s*(?:에이전트)?\s*(?:에|에게|를|을)?\s*'
                     r'[^\n]{0,30}?(?:부른다|넘긴다|위임)')


@check('gatekeeper-delegation', 'gatekeeper 위임 지시',
       '게이트를 약속만 하고 아무도 안 부르는 것 — v1 최대 결함 (diag-A 4절)')
def _gatekeeper_delegation(ctx):
    r = Result(unit='커맨드')
    t = _topo(ctx)
    if not t:
        return r
    for name, c in (t.get('commands') or {}).items():
        content = ((c or {}).get('entry') or {}).get('content') or []
        if not content:
            continue                       # 부를 것이 없다 — 대상이 아니다
        p = os.path.join(ctx.root, f'plugins/flow/commands/{name}.md')
        if not os.path.isfile(p):
            continue
        r.targets += 1
        if not GK_CALL.search(ctx.read(p)):
            ids = ', '.join(str(x.get('id')) for x in content if isinstance(x, dict))
            r.fail(f"위임 지시 없음 {ctx.rel(p)} — `entry.content`({ids}) 가 있는데 "
                   f"`gatekeeper` 를 부르라는 지시가 본문에 없다 "
                   f"(약속만 남으면 게이트가 이름만 있는 것이다)")
    return r


# ── 스킬 description 의 등급 ↔ 문형 ──
# v1 은 자율 7개 중 6개가 오발동 억제 신호(`/flow:X 가 쓴다`)를 달아 **등급이 사실상 뒤집혔다**
# (diag-B 3-a). v2 는 등급을 데이터로 두고 문형을 대조한다.
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
       'v1 은 자율 7개 중 6개가 억제 신호를 달아 등급이 뒤집혔다 (diag-B 3-a)')
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
                   f"v1 의 '모든 커맨드가 쓴다'가 그렇게 통과했다)")
        if grade == '기본값' and listed:
            r.fail(f"문형 어긋남 {ctx.rel(p)} [기본값] — `/flow:"
                   f"{sorted(listed)[0]}` 를 열거했다. 기본값은 열거하지 않는다 "
                   f"(부분 열거는 '이것만 쓴다'로 읽혀 거짓말이 된다)")
        if grade == '자율' and not SELF_CALL.search(d):
            r.fail(f"문형 어긋남 {ctx.rel(p)} [자율] — 커맨드만 적고 직접 호출을 안 적었다 "
                   f"(그것이 v1 에서 등급이 뒤집힌 자리다)")
    return r


# ── description 의 '누가 쓴다'가 사실인가 — 양방향 ──
# v1 검사기는 **한 방향만** 봐서 "모든 커맨드가 쓴다"는 거짓이 통과했다. 매 턴 실리는 거짓말이다.
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
       'v1 은 한 방향만 봐서 거짓 주장이 매 턴 실렸다 (diag-B 3-g · 설계 커맨드↔스킬 연결도)')
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
    ap = argparse.ArgumentParser(description='문서 정합 검사 (flow v2)')
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
