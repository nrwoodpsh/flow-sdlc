#!/usr/bin/env python3
"""문서 정합 검사 — 눈으로는 안 보이고 grep으로도 안 걸리는 것들.

돌리는 법:  python3 scripts/lint-docs.py     (repo 어디서든)
하나라도 걸리면 exit 1.

무엇을 보나 (번호는 아래 `# ──` 구획과 같다)
  1.    표의 열 수          — 이스케이프 안 된 `|` 가 행을 깨뜨린다
  1-1.  끊긴 표            — 표 사이에 글이 껴 뒤 행이 표 밖으로 나갔나
  1-1b. 표 뒤 빈 줄        — 불릿·문단이 표 마지막 칸에 딸려 들어가나
  1-1c. 쪼개진 표          — 빈 줄로 끊겨 뒷조각이 머리글을 잃었나
  1-2.  링크·앵커          — `path#앵커`의 파일과 헤딩이 실제로 있나
  1-3.  편집자 메모        — 실행 지시서(커맨드·스킬)에 유지보수 메모가 섞였나
  2.    등급 절 등재        — 템플릿의 [진행 필수]·[문서 필수] 절이 doc-verify 에 있나
  2-1.  등급 표기 형식      — `**[진행 필수]**`·`**[문서 필수]**` 두 형태만 쓰나
  3.    자리표시자 유출      — `{{ }}` 가 템플릿 밖(커맨드·스킬·가이드)에 남았나
  4.    이름 실존           — 백틱으로 가리킨 커맨드·에이전트·스킬이 실제로 있나
  5.    PlantUML 렌더 전제  — 코드블록에 `!pragma layout smetana` 가 있나
  6.    frontmatter 규약    — 키가 소문자인가
  6-1.  frontmatter 파싱   — 플러그인 파일의 frontmatter 가 YAML 로 읽히나
  6-2.  argument-hint 따옴표 — 안 감싸면 파일이 안 뜬다 (pyyaml 없이도 돈다)
  7.    갯수 표기           — 우리 자산을 세어 적었나 (plain-writing `갯수:`)
  8.    절 참조 금지        — `X`의 `Y` 로 절을 가리켰나 · 치환 잔여물이 매달렸나
  9.    description 오주장  — "누가 쓴다"가 커맨드의 `## 연결` 과 맞나
 10.    출력 형식 ↔ 템플릿   — 스킬이 지시한 절이 그 템플릿에 있나
 10-1.  왕복               — 스킬대로 만든 문서에 필수 절이 다 있나
 10-2.  plain-writing 결선 — 글을 쓰는 커맨드가 `## 연결` 에 적었나
 10-3.  `## 연결` 세 줄     — 커맨드가 스킬·에이전트·도구를 다 적었나
 11.    스킬 골격·문장·중복  — 마지막 절 `경계` · 목적 문단 · 미사여구 · 스킬 간 중복
"""
import re, sys, glob, os, json
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # scripts/ 의 부모
os.chdir(ROOT)

TPL = 'plugins/flow/project-template/doc/00.ref/03.templates'
fails = []


def md_files():
    out = []
    for pat in ('plugins/**/*.md', 'guide/*.md', '.claude/rules/*.md', '.claude/skills/*/SKILL.md'):
        out += glob.glob(pat, recursive=True)
    return out + [f for f in ('README.md', 'CLAUDE.md') if os.path.exists(f)]


def bar(line):
    """이스케이프한 `\\|` 는 세지 않는다."""
    return line.replace('\\|', '').count('|')


# ── 1. 표 열 수 ──
for f in md_files():
    L = open(f).read().split('\n')
    for i, l in enumerate(L):
        if not l.startswith('|'):
            continue
        if i + 1 >= len(L) or not re.match(r'^\|[:\- |]+\|$', L[i + 1]):
            continue
        h, j = bar(l), i + 2
        while j < len(L) and L[j].startswith('|'):
            if bar(L[j]) != h:
                fails.append(f"표 열 수 {f}:{j+1} — 머리 {h-1}칸, 이 행 {bar(L[j])-1}칸 "
                             f"(표 안의 `|` 는 `\\|` 로 escape)")
            j += 1

# ── 1-1. 표가 중간에 끊겼나 ──
# 표 사이에 비-표 줄(문단·blockquote)이 끼면 뒤 행은 **표가 아니라 파이프 문자열**로 렌더된다.
# 열 수 검사는 끊긴 뒤 행을 아예 안 보므로 따로 본다.
for f in md_files():
    L = open(f).read().split('\n')
    i = 0
    while i < len(L):
        if (L[i].startswith('|') and i + 1 < len(L)
                and re.match(r'^\|[:\- |]+\|$', L[i + 1])):
            j = i + 2                        # 표 본문 끝까지
            while j < len(L) and L[j].startswith('|'):
                j += 1
            k = j                            # 빈 줄이 아닌 다음 내용
            while k < len(L) and not L[k].strip():
                k += 1
            # 표 뒤에 다른 내용이 오고, 그 뒤에 또 `|` 행이 붙어 있으면 고아 행이다
            if k < len(L) and not L[k].startswith('|'):
                m = k + 1
                while m < len(L) and L[m].strip():
                    if L[m].startswith('|'):
                        # 구분선이 뒤따르면 **새 표의 머리글**이다 — 고아가 아니다
                        nxt = L[m + 1] if m + 1 < len(L) else ''
                        if not re.match(r'^\|[:\- |]+\|$', nxt):
                            fails.append(f"끊긴 표 {f}:{m+1} — 표 사이에 다른 줄이 끼어 이 행이 "
                                         f"표 밖으로 나갑니다 (그 줄을 표 뒤로 옮긴다)")
                        break
                    m += 1
            i = j
        else:
            i += 1

# ── 1-1b. 표 바로 뒤에 빈 줄 없이 불릿·문단이 붙었나 ──
# 표 마지막 행 다음 줄이 `-`·`*`·글자면 **표 안으로 빨려 들어가** 마지막 칸에 붙어 렌더된다.
# `끊긴 표` 검사는 표 사이에 낀 것만 보고 이 경우를 안 본다.
for f in md_files():
    L = open(f).read().split('\n')
    fence = False
    for i in range(len(L) - 1):
        if L[i].lstrip().startswith('```'):
            fence = not fence
            continue
        if fence or not L[i].startswith('|'):
            continue
        if i and re.match(r'^\|[:\- |]+\|$', L[i - 1]):
            continue                      # 구분선 바로 뒤 = 첫 본문 행
        nxt = L[i + 1]
        # 펜스 시작·표 계속·빈 줄은 정상
        if nxt.startswith('|') or not nxt.strip() or nxt.lstrip().startswith('```'):
            continue
        if re.match(r'^\s*[-*]\s|^\S', nxt):
            fails.append(f"표 뒤 빈 줄 없음 {f}:{i+2} — 표 마지막 칸에 딸려 들어간다 "
                         f"({nxt.strip()[:40]})")

# ── 1-1c. 표가 빈 줄로 쪼개졌나 ──
# 표 본문 → 빈 줄 → 다시 `|` 행인데 구분선이 없으면, 뒷조각은 **머리글 없는 표**로 깨져 렌더된다.
# `끊긴 표`는 표 사이에 **글이 낀** 경우만 보고 빈 줄 하나로 갈린 이 경우를 안 본다.
for f in md_files():
    L = open(f).read().split('\n')
    fence = False
    i = 0
    while i < len(L):
        if L[i].lstrip().startswith('```'):
            fence = not fence
            i += 1
            continue
        if fence or not (L[i].startswith('|') and i + 1 < len(L)
                         and re.match(r'^\|[:\- |]+\|$', L[i + 1])):
            i += 1
            continue
        j = i + 2                            # 표 본문 끝
        while j < len(L) and L[j].startswith('|'):
            j += 1
        k = j                                # 빈 줄을 건너뛴 다음 내용
        while k < len(L) and not L[k].strip():
            k += 1
        if j < k < len(L) and L[k].startswith('|'):
            nxt = L[k + 1] if k + 1 < len(L) else ''
            if not re.match(r'^\|[:\- |]+\|$', nxt):
                fails.append(f"쪼개진 표 {f}:{k+1} — 빈 줄로 끊겨 이 행부터 머리글이 없다 "
                             f"(빈 줄을 지운다)")
        i = max(j, i + 1)

# ── 1-2. 링크가 실제로 있나 (파일 + 앵커) ──
# `path#앵커` 형태에서 프래그먼트만 보는 실수가 잦다. 헤딩 이름을 바꾸면 조용히 깨진다.
def _anchors(path):
    out = set()
    try:
        for l in open(path, encoding='utf-8'):
            m = re.match(r'#{1,6}\s+(.*)', l)
            if not m:
                continue
            t = re.sub(r'[`*\[\]():.,—·?/\\]', '', m.group(1).strip())
            out.add(t.lower().replace(' ', '-'))
    except OSError:
        pass
    return out

for f in md_files():
    d = os.path.dirname(f)
    for m in re.finditer(r'\]\(([^)]+)\)', open(f, encoding='utf-8').read()):
        u = m.group(1)
        if u.startswith(('http', '#', 'mailto:')):
            continue
        path, _, frag = u.partition('#')
        tgt = os.path.normpath(os.path.join(d, path)) if path else f
        ln = 1 + open(f, encoding='utf-8').read()[:m.start()].count('\n')
        if not os.path.exists(tgt):
            fails.append(f"링크 대상 없음 {f}:{ln} — {u}")
        elif frag and frag.lower() not in _anchors(tgt):
            fails.append(f"앵커 없음 {f}:{ln} — {u} (헤딩 이름이 바뀌었나)")

# ── 1-3. 실행 파일에 편집자용 메모가 섞였나 ──
# 커맨드·에이전트·스킬·presets 는 **AI 가 런타임에 따라 하는 지시서**다.
# 거기에 "이 주제의 사람용 문서가 어디 있나" 같은 유지보수 메모를 넣으면
# AI 는 쓸 수 없고, 사용자 설명서가 규칙 정본으로 오해된다.
# (`.claude/rules/plugin-authoring.md` 의 `참조 통제`)
#
# **완전 전수는 불가능하다** — "이 정보가 런타임에 쓸모 있나"는 의미 판단이다.
# 아래는 실제로 발견된 유형만 잡는다. 현재 걸리는 게 0인 패턴만 넣는다.
EXEC_FILES = (glob.glob('plugins/flow/commands/*.md') + glob.glob('plugins/flow/agents/*.md')
              + glob.glob('plugins/flow/skills/*/SKILL.md')
              + glob.glob('plugins/flow/presets/*/README.md'))

NOTE_SIGNALS = [
    (r'guide/',                     '사람용 문서를 가리킨다'),
    (r'bump-version|lint-docs|scripts/tests',
                                    'repo 개발 자산을 가리킨다'),
    (r'사람용은|편집자|이 문서를 고칠',  '편집자용 메모다'),
    (r'\(\d+회차\)',                '내부 작업 회차를 인용했다'),
    # 이관 흔적은 "구 <파일>" 형태만 본다 — `이관을 제안한다`(config 마이그레이션)는 정상 용례다
    (r'구 `[^`]+`.*흡수|구 `[^`]+`.*이관',  '이관 흔적이 남았다'),
    (r'TODO|FIXME',                 '미완 표시가 남았다'),
    # `나중에 채운다`(ID 발급 전략)는 정상 — 문서 작성을 미룬 것만 본다
    (r'추가 예정|작성 예정|미작성',      '미룬 일을 지시서에 적었다'),
]

for f in EXEC_FILES:
    # 규칙을 설명하는 스킬 자신은 대상이 아니다 — 금지어를 예시로 들 수밖에 없다
    if f.endswith('plain-writing/SKILL.md'):
        continue
    fence = False
    for i, l in enumerate(open(f, encoding='utf-8'), 1):
        if l.lstrip().startswith('```'):
            fence = not fence
            continue
        if fence:
            continue          # 출력 예시 안은 런타임 치환값이라 대상이 아니다
        for pat, why in NOTE_SIGNALS:
            if re.search(pat, l):
                fails.append(f"편집자 메모 {f}:{i} — {why} "
                             f"(`.claude/rules/plugin-authoring.md` 의 `참조 통제`)")
                break

# ── 2. 등급 절이 doc-verify 에 등재됐나 ──
dv = open('plugins/flow/skills/doc-verify/SKILL.md').read()


def norm(s):
    s = re.sub(r'^\d+\.\s*', '', s)          # "1. 사용 계약" → "사용 계약"
    s = re.sub(r'\s*\(.*?\)\s*', '', s)      # "발견 (severity 순)" → "발견"
    return s.strip()


for f in sorted(glob.glob(f'{TPL}/*/*.md')):
    tpl = os.path.basename(os.path.dirname(f))
    for m in re.finditer(r'^#+\s*(.+?)\s*\*\*\[(진행 필수|문서 필수)\]\*\*', open(f).read(), re.M):
        sec = norm(re.sub(r'\s*\*\*.*', '', m.group(1)))
        if sec and sec not in dv:
            fails.append(f"등급 절 미등재 {tpl} [{m.group(2)}] `{sec}` — doc-verify `절의 등급` 표에 추가")

# ── 2-1. 등급 표기 형식이 통일됐나 ──
# `**[진행 필수]**` · `**[문서 필수]**` 두 형태만 쓴다. 조건은 뒤에 `— 단 **…**` 로 붙인다.
# 표기 안에 조건을 넣으면(`[진행 필수 — 규칙이 있으면]`) 등급 절 등재 검사가 못 알아본다.
for f in sorted(glob.glob(f'{TPL}/*/*.md')):
    for i, l in enumerate(open(f).read().split('\n'), 1):
        for m in re.finditer(r'\*\*\[([^\]]+)\]\*\*', l):
            if m.group(1) not in ('진행 필수', '문서 필수'):
                fails.append(f"등급 표기 {f}:{i} — `[{m.group(1)}]` "
                             f"(`[진행 필수]` 또는 `[문서 필수]` 만. 조건은 뒤에 `— 단 …`)")

# ── 3. 자리표시자 유출 ──
for f in md_files():
    if f.startswith(TPL) or 'project-template' in f:
        continue
    if 'presets/architectures' in f:
        continue   # 원형 카탈로그의 `{{repo URL 미정}}` 는 의도된 미정 표시다
    for i, l in enumerate(open(f).read().split('\n'), 1):
        if '{{' not in l or '}}' not in l:
            continue
        # 자리표시자를 "설명하는" 줄은 유출이 아니다
        if any(k in l for k in ('자리표시자', 'placeholder', '예:', '예시', '그대로 남긴다',
                                '{{…}}', '{{...}}')):
            continue
        fails.append(f"자리표시자 유출 {f}:{i} — {l.strip()[:60]}")

# ── 4. 이름 실존 ──
cmds = {os.path.basename(p)[:-3] for p in glob.glob('plugins/flow/commands/*.md')}
agents = {os.path.basename(p)[:-3] for p in glob.glob('plugins/flow/agents/*.md')}
skills = {os.path.basename(os.path.dirname(p)) for p in glob.glob('plugins/flow/skills/*/SKILL.md')}
for f in md_files():
    s = open(f).read()
    for m in re.finditer(r'/flow:([a-z]+)', s):
        if m.group(1) in ('xxx',):   # 형식 자리표시자
            continue
        if m.group(1) not in cmds:
            fails.append(f"없는 커맨드 {f} — /flow:{m.group(1)}")
    for m in re.finditer(r'`(explorer|builder|verifier|reviewer|gatekeeper|[a-z]+-[a-z]+)`', s):
        n = m.group(1)
        if n in agents or n in skills:
            continue
        if n in ('drift-hook', 'guard-danger', 'api-contract', 'task-doc',
                 'sop-runbook', 'open-code-review', 'claude-security', 'lint-staged',
                 'session-report', 'frontend-design', 'mcp-server', 'agent-app', 'egov-msa',
                 'db-dev', 'db-prod', 'drift-gate', 'pre-commit', 'post-commit', 'pre-push',
                 'adversarial-review', 'mcp-server-dev', 'core-hooksPath', 'no-verify'):
            continue
        if '-' in n and n not in skills:
            pass   # 하이픈 이름은 오탐이 많아 흘린다
# (커맨드 이름만 강하게 본다 — 에이전트·스킬은 위 인벤토리 대조로 충분하다)

# ── 5. PlantUML 렌더 전제 ──
for f in md_files():
    s = open(f).read()
    for m in re.finditer(r'```plantuml\n(.*?)```', s, re.S):
        if 'pragma layout smetana' not in m.group(1):
            ln = s[:m.start()].count('\n') + 1
            fails.append(f"PlantUML {f}:{ln} — `!pragma layout smetana` 없음 (Graphviz 없이 렌더 안 됨)")

# ── 6. frontmatter 키 소문자 ──
for f in (glob.glob('plugins/flow/commands/*.md') + glob.glob('plugins/flow/agents/*.md')
          + glob.glob('plugins/flow/skills/*/SKILL.md')):
    s = open(f).read()
    if not s.startswith('---'):
        fails.append(f"frontmatter 없음 {f}")
        continue
    for k in re.findall(r'^([A-Za-z-]+):', s.split('---')[1], re.M):
        if k != k.lower():
            fails.append(f"frontmatter 대문자 키 {f} — `{k}` (Claude Code가 못 읽어 안 뜬다)")

# ── 6-1. 플러그인 파일 frontmatter 가 YAML 로 읽히나 ──
# **여기만 본다.** Claude Code 가 commands·agents·skills 의 frontmatter 를 실제로 YAML 로 파싱한다
# (그래서 CLAUDE.md 의 작은따옴표·소문자 키 규칙이 있다 — 어기면 파일이 아예 안 뜬다).
# 프로젝트 문서(2.task·04.theme)의 frontmatter 는 파서가 돌지 않는다 — 태그는 grep 으로 읽는다.
try:
    import yaml
    for f in (glob.glob('plugins/flow/commands/*.md') + glob.glob('plugins/flow/agents/*.md')
              + glob.glob('plugins/flow/skills/*/SKILL.md')):
        txt = open(f).read()
        if not txt.startswith('---'):
            continue
        try:
            yaml.safe_load(txt.split('---')[1])
        except Exception as e:
            fails.append(f"frontmatter YAML {f} — {str(e).splitlines()[0]} "
                         f"(Claude Code 가 못 읽어 파일이 안 뜬다)")
except ImportError:
    print("  ℹ️ pyyaml 없음 — frontmatter YAML 검사 건너뜀")

# ── 6-2. argument-hint 가 따옴표로 감싸였나 (pyyaml 없이도 돈다) ──
# 검사 6-1 은 `import yaml` 이 실패하면 통째로 꺼진다. 그런데 `argument-hint` 를 안 감싸면
# **파일이 통째로 안 뜬다** — 그 사고를 잡는 유일한 검사가 fail-open 이면 안 된다.
for f in sorted(glob.glob('plugins/flow/commands/*.md')):
    for i, l in enumerate(open(f).read().split('\n')[:12], 1):
        m = re.match(r"^argument-hint:\s*(\S.*)$", l)
        if m and m.group(1)[0] not in ("'", '"'):
            fails.append(f"argument-hint 무따옴표 {f}:{i} — {m.group(1)[:40]} "
                         f"(작은따옴표로 감싼다. 닫는 `]` 뒤에 무엇이 오면 파일이 안 뜬다)")

# ── 7. 갯수 표기 (plain-writing `갯수:`) ──
# 명사 + 수 + 단위 — `스킬 16개` · `템플릿 열네 개`
#
# 한글 수사 + 명사(`다섯 절`)는 **일부러 안 본다.** 한국어 산문에서 오탐이 너무 많다 —
# `상세`의 `세`, `한 칸 요약`, `세 칸을 조합한다` 같은 서술적 표현이 전부 걸린다.
# 린트가 게이트를 막는 자리라 정밀도가 재현율보다 중요하다. 그 형태는 사람이 본다.
COUNT = re.compile(r'(스킬|커맨드|에이전트|템플릿|훅|가드레일|폴더|층|절)\s*'
                   r'(하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열[가-힣]*|[0-9]+)\s*(개|종|가지)')
for f in md_files():
    # 규칙을 적는 파일은 금지 형태를 예로 들 수밖에 없다
    if 'plain-writing' in f or f.endswith('CLAUDE.md') or 'plugin-authoring' in f:
        continue
    for i, l in enumerate(open(f).read().split('\n'), 1):
        m = COUNT.search(l)
        if not m:
            continue
        # 규모 예시는 대상이 아니다 — 갯수 앞에 가정법("…면")이 오거나 한 줄에 갯수가 둘 이상이다
        if len(COUNT.findall(l)) >= 2 or re.search(r'면[\s,]', l[:m.start()]):
            continue
        fails.append(f"갯수 표기 {f}:{i} — {l.strip()[:60]}  (목록·표가 곧 갯수다)")

# ── 8. 절 참조 금지 ──
# `X`의 `Y` (절 참조)를 쓰지 않는다. 스킬은 절 단위로 안 실린다 — 발동되면 파일 전체다.
# 그러니 절 이름은 모델에게 정보를 주지 않으면서, 이름을 고치면 조용히 끊기는 자리만 만든다.
# 스킬·에이전트·커맨드 이름은 폴더명=name=호출 ID라 고치면 로딩 자체가 실패한다 — 시끄럽게 깨진다.
# 남의 커맨드 이름(`codex`의 `adversarial-review`)·문서 절(`task`의 `Verification`)은 대상이 아니다.
OURS = {os.path.basename(os.path.dirname(p)) for p in glob.glob('plugins/flow/skills/*/SKILL.md')}
OURS |= {os.path.basename(p)[:-3] for p in glob.glob('plugins/flow/agents/*.md')}
OURS |= {os.path.basename(p)[:-3] for p in glob.glob('plugins/flow/commands/*.md')}
SEC_REF = re.compile(r'`([a-z][a-z-]+)`\s*의\s*`([^`]+)`')
# `X`의 `A`·`B` 를 기계로 줄이면 뒤쪽 `B` 가 매달린 채 남는다 — 실제로 4곳이 그랬다.
# `traceability`·`라우팅` 처럼 이름 둘로 읽혀 뜻이 바뀐다.
# 템플릿 폴더명은 정상 병기다 — `test-spec`·`05.verify`.
TPLDIR = {os.path.basename(d) for d in glob.glob(f'{TPL}/*') if os.path.isdir(d)}
DANGLE = re.compile(r'`(' + '|'.join(map(re.escape, sorted(OURS))) + r')`[·、]`([^`]+)`')
for f in md_files():
    # 규칙을 적는 파일은 금지 형태를 예로 들 수밖에 없다.
    # `plugin-authoring` 은 그 규칙이 CLAUDE.md 에서 옮겨온 자리다.
    if f.endswith('CLAUDE.md') or 'plugin-authoring' in f:
        continue
    for i, l in enumerate(open(f).read().split('\n'), 1):
        for who, sec in SEC_REF.findall(l):
            if who in OURS:
                fails.append(f"절 참조 {f}:{i} — `{who}`의 `{sec}` → `{who}` 만 쓴다")
        for who, tail in DANGLE.findall(l):
            if tail not in OURS and tail not in TPLDIR:
                fails.append(f"매달린 절 이름 {f}:{i} — `{who}`·`{tail}` "
                             f"(절 이름을 지울 때 뒤쪽이 남았다)")

# ── 8-1. 절 이름에 번호·라벨이 붙었나 ──
# 검사 8 은 `X`의 `Y` 형태만 본다. 번호·라벨 절 **자체**는 아무 검사도 안 봤다 —
# 실제로 `## 절차 D — 문서 리뷰` 와 `### ① 무엇이 필요한가` 가 통과한 채 들어갔고,
# 둘 다 밖에서 **번호로** 가리키는 줄까지 딸려 있었다(`(아래 절차 3)`·`(아래 위임 판정 ②)`).
# 절을 하나 더하면 그 참조가 조용히 어긋난다.
# 산문·프롬프트 안의 번호는 대상이 아니다 — `run.md` 의 `① 합친다 ② 나눈다` 는
# 사용자가 번호로 고르는 메뉴고, 순서 있는 `**N. 이름**` 절차 줄도 번호가 뜻이다.
# 템플릿(`03.templates/`)은 사람이 절 번호로 자리를 찾는 골격이라 뺀다.
LABELED = re.compile(r'^#{2,4}\s+(?:[0-9]+\s*[.)]|[①-⑳]|절차\s+[A-Z0-9])')
for f in md_files():
    if f.endswith('CLAUDE.md') or 'plugin-authoring' in f or '03.templates' in f:
        continue
    for i, l in enumerate(open(f).read().split('\n'), 1):
        if LABELED.match(l) and '단계' not in l:
            fails.append(f"번호·라벨 절 {f}:{i} — {l.strip()[:50]}  (이름만 쓴다)")

# ── 9. 스킬 description 의 "누가 쓴다"가 사실인가 ──
# description 에 `누가 쓴다`를 적는다. 그 주장이 틀리면 **매 턴 거짓말이 실린다.**
# 실제 근거는 커맨드의 `## 연결` → `- **스킬**:` 줄이다.
# 실제로 3건이 틀린 채 들어갔다 — `sync.md`가 "이 커맨드가 그 스킬을 쓰지는 않는다"고
# 적어 둔 것을 description 에 쓴다고 적은 경우까지 있었다.
_named = {}
for p in glob.glob('plugins/flow/commands/*.md'):
    m = re.search(r'^- \*\*스킬\*\*:(.*)$', open(p).read(), re.M)
    if not m:
        continue
    for s in glob.glob('plugins/flow/skills/*/SKILL.md'):
        n = os.path.basename(os.path.dirname(s))
        if f'`{n}`' in m.group(1):
            _named.setdefault(n, set()).add(os.path.basename(p)[:-3])

def _desc(path):
    """folded(`>-`)로 감은 description 도 이어 붙여 한 줄로 돌려준다.

    한 물리 줄만 읽으면 folded 에서는 `>-` 만 잡혀 **검사가 조용히 꺼진다.**
    """
    L = open(path).read().split('\n')
    for i, l in enumerate(L):
        m = re.match(r'^description:\s*(.*)$', l)
        if not m:
            continue
        head = m.group(1).strip()
        if head not in ('>', '>-', '|', '|-'):
            return head
        out = []
        for nxt in L[i + 1:]:
            if not nxt.startswith('  ') or re.match(r'^\S', nxt):
                break
            out.append(nxt.strip())
        return ' '.join(out)
    return None


for p in sorted(glob.glob('plugins/flow/skills/*/SKILL.md')):
    n = os.path.basename(os.path.dirname(p))
    d = _desc(p)
    if not d:
        continue
    for c in set(re.findall(r'/flow:([a-z]+)', d)):
        if c not in _named.get(n, set()):
            fails.append(f"description 오주장 {p} — /flow:{c} 는 `{n}` 을 "
                         f"`## 연결` 의 스킬로 적지 않았다")

# ── 10. 스킬 `출력 형식` 의 절이 그 템플릿에 실제로 있나 ──
# 실물 출력 문자열을 스킬에 두면 홉이 0이 되지만 **템플릿과 두 곳**이 된다.
# 실제로 4개 스킬 전부 어긋났다 — `안 본 층`(템플릿은 `안 본 주제`)처럼 이름을 지어냈다.
# 어긋나면 생성한 문서가 doc-verify 채점에서 미등재로 걸린다.
#
# `##` 만 본다. `###` 는 상위 절 아래 덧붙이는 것이라 템플릿에 없어도 정상이다.
OUT_TPL = {'code-review': '06.review', 'theme-apply': '15.theme',
           'impact-analysis': '02.task-doc'}
MULTI = {'test-spec': ('05.verify', '14.integration')}   # 단위·통합 두 템플릿을 함께 쓴다


def _out_secs(path):
    got, inside, fence = [], False, False
    for l in open(path, encoding='utf-8'):
        if l.lstrip().startswith('```'):
            fence = not fence
            continue
        if not fence and l.startswith('## '):
            inside = l[3:].strip() == '출력 형식'
            continue
        if inside and fence and l.startswith('## '):
            got.append(norm(re.sub(r'\s{2,}.*', '', l[3:].strip())))
    return got


def _tpl_secs(*tpls):
    """조건 표기(`*(…일 때만)*`)와 등급 표기를 떼고 절 이름만 남긴다."""
    out = set()
    for t in tpls:
        for f in glob.glob(f'{TPL}/{t}/*.md'):
            for l in open(f, encoding='utf-8'):
                if re.match(r'^#{2,3} ', l):
                    x = re.sub(r'\s*\*\*\[.*', '', re.sub(r'^#+\s*', '', l)).strip()
                    out.add(norm(x).replace('*', '').strip())
    return out


for sk, tpls in list(OUT_TPL.items()) + list(MULTI.items()):
    p = f'plugins/flow/skills/{sk}/SKILL.md'
    if not os.path.exists(p):
        continue
    known = _tpl_secs(*((tpls,) if isinstance(tpls, str) else tpls))
    for sec in _out_secs(p):
        if sec not in known:
            fails.append(f"출력 형식 미등재 {p} — `{sec}` 이 템플릿에 없다 "
                         f"(템플릿이 기준이다 — 이름을 맞추거나 템플릿에 절을 추가한다)")

# ── 10-1. 왕복 — 스킬대로 만든 문서가 채점을 통과하나 ──
# 이름 대조만으로는 **빠진 절**을 못 본다. 실제로 `test-spec` 의 출력 형식에
# `판정`(진행 필수)이 없어, 그대로 만들면 gatekeeper 가 PASS/FAIL 을 읽을 자리가 없었다.
# 스킬의 코드블록을 그 템플릿의 필수 절 목록과 맞춰 본다.
def _out_blocks(p):
    """`출력 형식` 절의 펜스 블록 본문들 — 펜스 밖 `## ` 만 절 경계다"""
    out, inside, fence, cur = [], False, False, None
    for l in open(p, encoding='utf-8'):
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
            cur.append(l.rstrip('\n'))
    return out


def _tpl_required(t):
    req = {}
    for f in glob.glob(f'{TPL}/{t}/*.md'):
        for l in open(f, encoding='utf-8'):
            m = re.search(r'^##\s*(.+?)\s*\*\*\[(진행 필수|문서 필수)\]\*\*', l)
            if m:
                req[re.sub(r'^\d+\.\s*', '', m.group(1).strip())] = m.group(2)
    return req


# (스킬, 템플릿, 몇 번째 블록) — 한 스킬이 여러 템플릿을 쓰면 블록 순서가 짝이다
ROUNDTRIP = [('code-review', '06.review', 0), ('theme-apply', '15.theme', 0),
             ('test-spec', '05.verify', 0), ('test-spec', '14.integration', 1)]
for sk, t, idx in ROUNDTRIP:
    bs = _out_blocks(f'plugins/flow/skills/{sk}/SKILL.md')
    if idx >= len(bs):
        fails.append(f"왕복 {sk} → {t} — 출력 형식에 블록 {idx} 가 없다")
        continue
    got = {l[3:].strip() for l in bs[idx].split('\n') if l.startswith('## ')}
    for sec, grade in _tpl_required(t).items():
        if sec not in got:
            fails.append(f"왕복 {sk} → {t} — 출력 형식에 `{sec}`[{grade}] 가 없다 "
                         f"(그대로 만들면 채점에서 FAIL 이다)")

# ── 10-2. 글을 쓰는 커맨드가 `plain-writing` 을 적었나 ──
# 기본값은 `default-reference` 가 정한다. 안 쓰는 것은 판별·git·오케스트레이션 셋뿐이다.
# 실제로 build·review·verify·theme 가 문서를 만드는데 빠져 있었다 — 열거는 새 커맨드에서 또 빠진다.
NO_PROSE = {'ask', 'commit', 'run'}
for p in sorted(glob.glob('plugins/flow/commands/*.md')):
    c = os.path.basename(p)[:-3]
    m = re.search(r'^- \*\*스킬\*\*:(.*)$', open(p, encoding='utf-8').read(), re.M)
    has = bool(m and '`plain-writing`' in m.group(1))
    if c in NO_PROSE and has:
        fails.append(f"plain-writing 불필요 {p} — `{c}` 는 글을 쓰지 않는다 (`default-reference`)")
    if c not in NO_PROSE and not has:
        fails.append(f"plain-writing 누락 {p} — 글을 쓰는 커맨드는 `## 연결` 에 적는다 "
                     f"(`default-reference` 의 기본값)")

# ── 10-3. 커맨드 `## 연결` 에 세 줄이 다 있나 ──
# `에이전트`·`스킬`·`템플릿` 은 **없어도 "없음"이라고 적는다.**
# 안 적으면 "없는 것"과 "적기를 잊은 것"을 구분할 수 없다. 실제로 ask·setup 이 그랬다.
# `도구`·`참조`는 있을 때만 적는 선택 항목이다.
for p in sorted(glob.glob('plugins/flow/commands/*.md')):
    m = re.search(r'^## 연결\n(.*?)^## ', open(p, encoding='utf-8').read(), re.S | re.M)
    body = m.group(1) if m else ''
    for k in ('에이전트', '스킬', '템플릿'):
        if not re.search(rf'^- \*\*{k}\*\*:', body, re.M):
            fails.append(f"연결 누락 {p} — `- **{k}**:` 줄이 없다 (없으면 `없음`이라고 적는다)")

# ── 11. 스킬 골격·문장·중복 ──
# 실제로 오류를 낸 렌즈만 남겼다. 오탐이 있던 것(조사 판정·수치 상수·조건 표기)은 넣지 않는다.
SKILLS_MD = sorted(glob.glob('plugins/flow/skills/*/SKILL.md'))
_sname = lambda p: os.path.basename(os.path.dirname(p))


def _outside(p):
    """펜스 밖 (줄번호, 줄)"""
    out, fence = [], False
    for i, l in enumerate(open(p, encoding='utf-8'), 1):
        if l.lstrip().startswith('```'):
            fence = not fence
            continue
        if not fence:
            out.append((i, l.rstrip('\n')))
    return out


FLUFF = re.compile(r'(?<![가-힣])(매우|아주|정말|굉장히|훨씬|상당히|다양한|여러가지|손쉽게'
                   r'|간편하게|효율적으로|효과적으로|최적화된|강력한|유연한|풍부한|성공적으로'
                   r'|원활하게)(?![가-힣])')

_dupsrc = {}
for p in SKILLS_MD:
    n, lines = _sname(p), _outside(p)
    heads = [l[3:].strip() for _, l in lines if l.startswith('## ')]

    # 골격 — 마지막 절은 `경계`, 금지 절 없음, 분류에 번호 없음
    if not heads or heads[-1] != '경계':
        fails.append(f"스킬 골격 {p} — 마지막 절이 `{heads[-1] if heads else '없음'}` (`경계`여야 한다)")
    for bad in ('목적', '적용 시점', '가드레일', '함정', '검증', '참조'):
        if bad in heads:
            fails.append(f"스킬 골격 {p} — 금지 절 `{bad}` (`.claude/rules/plugin-authoring.md` 의 `작성 스타일`)")
    for i, l in lines:
        # `### N단계` 는 순서가 뜻을 가져 예외다. 분류에 붙인 번호만 잡는다
        if re.match(r'^#{2,3} \d+[.)]', l) or re.match(r'^#{2,3} \d+-\d', l):
            fails.append(f"스킬 골격 {p}:{i} — 분류 절에 번호 `{l.strip()[:30]}`")

    # 목적 문단 — 제목 뒤 바로 절로 들어가면 목적이 사라진다
    L = open(p, encoding='utf-8').read().split('---', 2)[2].strip().split('\n')
    k = 1 if L and L[0].startswith('# ') else 0
    while k < len(L) and not L[k].strip():
        k += 1
    if k >= len(L) or L[k].startswith('## '):
        fails.append(f"스킬 골격 {p} — 제목 뒤 목적 문단이 없다")

    # 문장 — 미사여구·굵게·절 이음. 규칙을 적는 스킬 자신은 예로 들 수밖에 없다
    if n != 'plain-writing':
        for i, l in lines:
            for m in FLUFF.finditer(l):
                fails.append(f"미사여구 {p}:{i} — `{m.group(1)}` (`plain-writing`)")
            if l.startswith(('|', '#', '>')):
                continue
            if len(re.findall(r'\*\*[^*]+\*\*', l)) >= 4:
                fails.append(f"굵게 과다 {p}:{i} — 한 줄에 4개 이상 (`plain-writing` 구조)")
            # 자수는 후보를 뽑는 값일 뿐이다. **절 이음이 실제 원인**이라 그걸로 걸러 낸다 —
            # 자수만 보면 경로·YAML·argument-hint 가 걸려 오탐이 71% 였다.
            for sent in re.split(r'(?<=[.다])\s+', re.sub(r'[`*]', '', l.strip())):
                c = sent.strip(' -·')
                if len(c) <= 72:
                    continue
                if len(re.findall(r'(?:하고|하며|되고|이고|않으면|으면|는데|지만|거나)', c)) >= 2:
                    fails.append(f"절 이음 {p}:{i} — 한 문장에 절이 셋 이상 ({len(c)}자). "
                                 f"두 문장으로 자른다 (`plain-writing` 문장)")

    _dupsrc[n] = [re.sub(r'\s+', ' ', re.sub(r'[`*|]', '', l).strip(' -'))
                  for _, l in lines if l.strip().startswith(('- ', '| ')) and len(l.strip()) > 34]

# 스킬 간 중복 — 정본이 둘이 되면 한쪽만 고쳐진다
_nz = lambda s: re.sub(r'[^가-힣a-zA-Z0-9]', '', s)
_ks = sorted(_dupsrc)
for _i, _a in enumerate(_ks):
    for _b in _ks[_i + 1:]:
        for _x in _dupsrc[_a]:
            for _y in _dupsrc[_b]:
                if SequenceMatcher(None, _nz(_x), _nz(_y)).ratio() >= 0.85:
                    fails.append(f"스킬 간 중복 [{_a}]↔[{_b}] — {_x[:52]} "
                                 f"(정본 하나를 정하고 다른 쪽은 이름으로 가리킨다)")

# ── 결과 ──
if fails:
    for x in fails:
        print(f"  ❌ {x}")
    print(f"\n문서 정합 — 실패 {len(fails)}")
    sys.exit(1)
print("문서 정합 — 전부 통과")
