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


def fm_field(text, key):
    """frontmatter 의 한 줄 필드. **yaml 을 쓰지 않는다** — 없으면 꺼지는 검사를 만들지 않는다."""
    if not text.startswith('---'):
        return None
    parts = text.split('---', 2)
    if len(parts) < 3:
        return None
    m = re.search(rf'^{re.escape(key)}:\s*(.*)$', parts[1], re.M)
    if not m:
        return None
    return m.group(1).strip().strip('\'"') or None


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


# ── 출력 형식 ↔ 템플릿 왕복 (v1 검사 10 · 10-1) ──
# 스킬의 `출력 형식` 절이 지시한 절 이름과 그 템플릿의 절이 어긋나면,
# 그대로 만든 문서가 `doc-verify` 채점에서 FAIL 이다. 그 인과가 실제로 있었다(diag-C 1절).
#
# v1 은 스킬↔템플릿 짝을 **스크립트 안에 손으로 열거**했다(`OUT_TPL`·`MULTI`·`ROUNDTRIP`).
# 그게 diag-C 4절이 말하는 그 병이다 — 정본이 둘. v2 는 스킬 frontmatter 가 자기 템플릿을 적고
# 검사기는 그걸 읽는다. 짝을 늘리는 비용이 스킬 한 줄이 된다.
#
#   ---
#   name: code-review
#   output-template: 06.review            # 여럿이면 쉼표로, 순서가 코드블록 순서와 짝이다
#   ---

def _declared(ctx):
    """(스킬 경로, 스킬 이름, [템플릿 이름...]) — `output-template` 을 적은 스킬만."""
    out = []
    for p in ctx.skills():
        v = fm_field(ctx.read(p), 'output-template')
        if not v:
            continue
        tpls = [t.strip() for t in v.split(',') if t.strip()]
        if tpls:
            out.append((p, os.path.basename(os.path.dirname(p)), tpls))
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
    for p, name, tpls in _declared(ctx):
        known = _tpl_sections(ctx, *tpls)
        for sec in _out_sections(ctx, p):
            r.targets += 1
            if sec not in known:
                r.fail(f"출력 형식 미등재 {ctx.rel(p)} — `{sec}` 이 템플릿"
                       f"({'·'.join(tpls)})에 없다 "
                       f"(템플릿이 기준이다 — 이름을 맞추거나 템플릿에 절을 추가한다)")
    return r


@check('output-required-sections', '템플릿 필수 절이 출력 형식에 있나',
       '이름 대조만으로는 빠진 절을 못 본다 (diag-C 1절 · v1 검사 10-1)')
def _output_required(ctx):
    r = Result(unit='필수 절')
    for p, name, tpls in _declared(ctx):
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
