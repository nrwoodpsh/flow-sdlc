#!/usr/bin/env bash
# 소스 파일에 쓰기 전에 그 파일을 담은 task 문서와 요구 태그를 확인한다 (PreToolUse Write|Edit).
#
# 왜 훅인가: v1 최대 결함이 **게이트를 4곳이 약속하고 실제로 거는 곳은 하나**였다(diag-A 4절).
# 커맨드 본문이 "설계 없이 구현하지 않는다"고 적어도 AI 가 어기면 아무것도 막지 못한다.
# 그래서 진행하는 쪽이 아닌 것이 판정한다 — 판정 근거는 `flow.topology.json` 의 `gate` 절이다.
# **차단 조건을 이 파일에 열거하지 마라.** 적는 순간 정본이 둘이 된다.
#
# ── 이 기계가 닿는 범위 (경로별로 적는다. 층 수를 세지 않는다) ──────
#   Write · Edit         **기계.** matcher 가 이 둘이라 반드시 지난다
#   Bash 경유 쓰기       guard-danger.sh 가 쓰기 대상을 뽑아 **이 스크립트에 물어본다**
#                        (`>` · `>>` · `tee` · `sed -i` 계열까지. 아래 한계를 봐라)
#   MCP 파일 도구        **못 막는다.** matcher 가 도구 이름이라 훅이 아예 안 돈다
#   사람이 편집기로       못 막는다. 훅은 Claude Code 세션에만 걸린다
#
# **한계 — "보장"이라 읽지 마라.**
#   `python -c "open('src/a.ts','w')..."` 처럼 경로가 코드 안에 있으면 셸이 알 수 없다.
#   `eval` · 변수로 쪼갠 경로 · 스크립트 파일에 써서 실행도 같다.
#   즉 기계인 것은 Write·Edit 경로이고, Bash 는 guard 가 닿는 범위까지다.
#
# ── 과차단을 더 무서워한다 ────────────────────────────────────
# task 문서 없는 쓰기를 전부 막으면 정상 작업이 걸리고, 그러면 사람이 훅을 꺼 버린다 —
# 그건 그 층이 **영구히** 없어지는 것이다. 그래서 면제를 **먼저** 본다.
# 면제 목록도 topology 가 갖는다(spike/ · 유닛 없음 · 레거시 면제 · 소스 아님).
#
# ── 부르는 법 ────────────────────────────────────────────────
#   훅으로:   stdin 에 PreToolUse JSON        → exit 0 통과 · exit 2 차단 · stdout JSON 으로 ask
#   물어볼 때: gate-source-write.sh --path <경로> [프로젝트루트]
#             → exit 0 통과 · 2 차단 · 3 ask.  차단 이유는 stderr 로.
#   `--why` 를 붙이면 판정 근거를 한 줄로 더 적는다(테스트가 읽는다).
set -uo pipefail

MODE=hook ; ARG_PATH= ; ARG_ROOT= ; WHY=
while [ $# -gt 0 ]; do
  case "$1" in
    --path) MODE=path; ARG_PATH="${2:-}"; shift 2 ;;
    --root) ARG_ROOT="${2:-}"; shift 2 ;;
    --why)  WHY=1; shift ;;
    *) ARG_ROOT="$1"; shift ;;
  esac
done

# 파서가 없으면 통과시킨다 — 여기서 막으면 정상 작업이 전부 멈춘다.
command -v python3 >/dev/null 2>&1 || command -v node >/dev/null 2>&1 || exit 0

ROOT="${ARG_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd) || here=.
TOPO="${FLOW_TOPOLOGY:-}"
if [ -z "$TOPO" ]; then
  for c in "${CLAUDE_PLUGIN_ROOT:-}/flow.topology.json" "$here/../../flow.topology.json"; do
    [ -f "$c" ] && { TOPO=$c; break; }
  done
fi

# ── 입력에서 경로를 꺼낸다 ────────────────────────────────────
if [ "$MODE" = hook ]; then
  input=$(cat)
  ARG_PATH=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin); ti=d.get("tool_input") or {}
 # Write 는 file_path, Edit 도 file_path. notebook 계열은 notebook_path.
 sys.stdout.write(str(ti.get("file_path") or ti.get("notebook_path") or ""))
except Exception: pass' 2>/dev/null)
fi
[ -n "$ARG_PATH" ] || exit 0

# ── flow 프로젝트가 아니면 조용히 통과한다 ────────────────────
# 남의 프로젝트에서 우리 훅이 말을 걸면 안 된다. ask 도 아니고 침묵이다.
[ -f "$ROOT/workflow.config.json" ] || exit 0

deny_out() {   # <제목> <이유> <어떻게 하나>
  echo "" 1>&2
  echo "⛔ flow gate: $1" 1>&2
  echo "   경로: $ARG_PATH" 1>&2
  echo "" 1>&2
  echo "   왜: $2" 1>&2
  echo "   → $3" 1>&2
  echo "" 1>&2
  echo "   (판정 근거: plugins/flow/flow.topology.json 의 gate 절 · 면제는 spike/ · 유닛 없음 · 소스 아님)" 1>&2
  echo "" 1>&2
}

ask_out() {   # <이유>
  local reason
  reason=$(printf '%s' "⚠ flow gate: $1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n\t' '  ')
  if [ "$MODE" = hook ]; then
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
    exit 0
  fi
  echo "$reason" 1>&2
  exit 3
}

# ── 정본을 못 읽으면 ask 다 (fail-open 도 fail-closed 도 아니다) ──
# 근거는 topology 의 `gate.missingCanon.$why` 에 적어 두었다. 요약:
#   fail-closed 는 이 파일을 고치는 것조차 막아 사람이 훅을 지우게 만든다.
#   fail-open 은 조용해서 "게이트가 있다"는 착각만 남긴다 — v1 이 그렇게 낡았다.
#   게이트는 쓰기 때만 도는 드문 훅이라 ask 의 빈도가 감당된다. 그래서 사람에게 넘긴다.
if [ -z "$TOPO" ] || [ ! -f "$TOPO" ]; then
  ask_out "게이트 판정 근거(flow.topology.json)를 못 찾았습니다 — 지금은 아무 게이트도 없는 상태입니다. 찾은 곳: ${TOPO:-(없음)}"
fi

# ── 판정은 python3 에 맡긴다 ──────────────────────────────────
# 셸로 glob·frontmatter·File Map 을 다루면 인용·단어분리 사고가 다시 난다.
# guard-danger.sh 의 토크나이저를 재작성하지 않는 것과 같은 이유다.
verdict=$(python3 - "$TOPO" "$ROOT" "$ARG_PATH" <<'PY' 2>/dev/null
import fnmatch, json, os, re, sys

topo_p, root, target = sys.argv[1], sys.argv[2], sys.argv[3]

def out(code, title, why, how='', note=''):
    print('\x1f'.join([code, title, why, how, note]))
    raise SystemExit(0)

try:
    with open(topo_p, encoding='utf-8') as fh:
        topo = json.load(fh)
except Exception as e:
    out('ask', '판정 근거를 읽을 수 없다', f'flow.topology.json 파싱 실패 — {type(e).__name__}')

g = topo.get('gate')
if not isinstance(g, dict):
    out('ask', '판정 근거에 gate 절이 없다', 'flow.topology.json 의 gate 절이 정본이다')
if not g.get('enabled', True):
    out('allow', '', 'gate.enabled 가 false 다')

# 경로를 repo 상대로 —
rel = target
if os.path.isabs(rel):
    try:
        rel = os.path.relpath(rel, root)
    except ValueError:
        out('allow', '', '프로젝트 밖 경로다')
rel = rel.replace(os.sep, '/').lstrip('./')
if rel.startswith('..'):
    out('allow', '', '프로젝트 밖 경로다')

cfg = {}
try:
    with open(os.path.join(root, 'workflow.config.json'), encoding='utf-8') as fh:
        cfg = json.load(fh)
except Exception:
    cfg = {}


def dig(d, dotted):
    for k in dotted.split('.'):
        d = d.get(k) if isinstance(d, dict) else None
    return d


def any_glob(path, pats):
    for p in pats or []:
        if not p:
            continue
        if fnmatch.fnmatch(path, p):
            return True
        # `**/x` 는 최상위 파일에도 맞아야 한다 (drift-hook.sh 의 같은 배려)
        if p.startswith('**/') and fnmatch.fnmatch(path, p[3:]):
            return True
        # `src/**` 는 `src/` 아래 전부
        if p.endswith('/**') and (path == p[:-3] or path.startswith(p[:-2])):
            return True
    return False


# ── 면제를 먼저 본다 ──
src = g.get('source') or {}
ex_ids = {e.get('id'): e for e in (g.get('exemptions') or [])}

# spike/ · 레거시 면제 — 경로 목록은 topology + workflow.config 양쪽에서 온다
for eid in ('spike', 'legacy-exempt'):
    e = ex_ids.get(eid)
    if not e:
        continue
    pats = list(e.get('paths') or [])
    ck = e.get('configKey')
    if ck:
        extra = dig(cfg, ck)
        if isinstance(extra, list):
            pats += [str(x) for x in extra]
    if any_glob(rel, pats):
        out('allow', '', f'면제 — {e.get("what")}', note=eid)

# 소스인가 — drift-hook.sh 의 is_source 와 같은 규칙이어야 한다
ignore = dig(cfg, src.get('ignoreKey') or 'drift.ignore')
ignore = ignore if isinstance(ignore, list) else src.get('defaultIgnore') or []
globs = dig(cfg, src.get('configKey') or 'drift.sourceGlobs')
globs = globs if isinstance(globs, list) else []

if any_glob(rel, ignore):
    out('allow', '', '소스가 아니다 (drift.ignore)', note='not-source')
if globs:
    if not any_glob(rel, globs):
        out('allow', '', '소스가 아니다 (drift.sourceGlobs 밖)', note='not-source')
else:
    for pre in src.get('defaultNonSource') or []:
        if rel.startswith(pre):
            out('allow', '', f'소스가 아니다 ({pre} 아래)', note='not-source')
    if rel.endswith('.md'):
        out('allow', '', '소스가 아니다 (.md)', note='not-source')

# 유닛이 하나도 없으면 검사를 안 켠다 — drift-hook.sh 와 같은 판정
work = os.path.join(root, *(g.get('workRoot') or 'doc/01.work').split('/'))
depth = int(g.get('unitDepth') or 2)


def units(base, d):
    if d == 0:
        return [base] if os.path.isdir(base) else []

    got = []
    try:
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                got += units(p, d - 1)
    except OSError:
        return []
    return got


unit_dirs = units(work, depth)
if not unit_dirs:
    out('allow', '', '유닛이 하나도 없다 — flow 도입 직후라 검사를 안 켠다', note='no-units')

# ── task 문서를 모은다 ──
td = g.get('taskDoc') or {}
rt = g.get('requirementTag') or {}
fm_pat = re.compile((g.get('fileMap') or {}).get('pattern')
                    or r'\[(New|Mod)\][ \t]*`?([^`\s]+)`?')
ph = re.compile(rt.get('placeholderPattern') or r'\{\{')
field = rt.get('field') or 'requirement'

docs = []          # (상대경로, 요구태그 있나, [선언한 경로...])
for u in unit_dirs:
    for pat in td.get('globs') or []:
        import glob as _glob
        for f in sorted(_glob.glob(os.path.join(u, *pat.split('/')))):
            if not os.path.isfile(f):
                continue
            try:
                with open(f, encoding='utf-8') as fh:
                    text = fh.read()
            except OSError:
                continue
            tag = False
            if text.startswith('---'):
                parts = text.split('---', 2)
                if len(parts) >= 3:
                    m = re.search(rf'^{re.escape(field)}:\s*(.*)$', parts[1], re.M)
                    if m:
                        v = m.group(1).strip().strip('[]').strip()
                        tag = bool(v) and not ph.search(v)
            declared = []
            for mm in fm_pat.finditer(text):
                p = mm.group(2)
                if ph.search(p):
                    continue
                declared.append(p.lstrip('./'))
            docs.append((os.path.relpath(f, root).replace(os.sep, '/'), tag, declared))

if not docs:
    out('deny', 'task 문서가 없다',
        '유닛은 있는데 task 문서가 하나도 없다 — 설계 없이 구현이 앞서가는 중이다',
        '/flow:design 으로 task 문서를 만든 뒤 구현하세요. 버릴 코드면 spike/ 아래에 쓰세요.',
        note='no-task-doc')

# ── 유닛 해석 ──
mode = (g.get('unitResolution') or {}).get('mode') or 'declared-file-map'
fallback = (g.get('unitResolution') or {}).get('fallback') or ''

hits = [(p, tag) for p, tag, dec in docs
        if any(rel == d or any_glob(rel, [d]) or (d.endswith('/') and rel.startswith(d))
               for d in dec)]

if hits:
    tagged = [p for p, tag in hits if tag]
    if tagged:
        out('allow', '', f'task 문서가 이 경로를 담았고 요구 태그가 있다 — {tagged[0]}',
            note='declared-file-map')
    out('deny', 'task 문서에 요구 태그가 없다',
        f'{hits[0][0]} 가 이 경로를 담았지만 frontmatter `{field}:` 가 비었거나 템플릿 그대로다',
        f'그 task 문서의 `{field}:` 에 요구 ID 를 적으세요 (예: {field}: [USER-LOGIN-1]).',
        note='no-req-tag')

# File Map 을 쓰는 task 문서가 **하나도** 없으면 정확 판정이 불가능하다.
# 이때 전 쓰기를 막으면 레거시 프로젝트가 훅을 꺼 버린다 — 거친 바닥으로 내려간다.
if mode == 'declared-file-map' and not any(dec for _, _, dec in docs):
    if fallback == 'any-unit-has-task':
        if any(tag for _, tag, _ in docs):
            out('allow', '',
                'File Map 을 쓰는 task 문서가 없어 거친 판정으로 통과 — 요구 태그 있는 task 문서가 있다',
                note='fallback-any-unit')
        out('deny', 'task 문서에 요구 태그가 없다',
            'task 문서는 있지만 요구 태그가 하나도 없다 (거친 판정 — File Map 을 쓰는 문서가 없다)',
            'task 문서 frontmatter 에 요구 ID 를 적으세요.',
            note='fallback-no-req-tag')

out('deny', '이 경로를 담은 task 문서가 없다',
    f'File Map 에 `{rel}` 을 적은 task 문서가 없다 — 무슨 요구로 이 파일을 쓰는지 추적할 수 없다',
    'task 문서의 `## 3. File Map` 에 `- `[New] ' + rel + '`` 을 적으세요. '
    '버릴 코드면 spike/ 아래에 쓰세요.',
    note='not-declared')
PY
)

if [ -z "$verdict" ]; then
  # 판정기가 아무것도 못 냈다 — 조용히 통과하지 않는다(위 missingCanon 과 같은 이유)
  ask_out "게이트 판정기가 결과를 내지 못했습니다 — 지금은 아무 게이트도 없는 상태입니다."
fi

IFS=$'\037' read -r code title why how note <<<"$verdict"

[ -n "$WHY" ] && echo "gate: $code${note:+ ($note)}${why:+ — $why}" 1>&2

case "$code" in
  allow) exit 0 ;;
  ask)   ask_out "$title — $why" ;;
  deny)  deny_out "$title" "$why" "$how"; exit 2 ;;
  *)     ask_out "게이트 판정을 읽을 수 없습니다 ($code)" ;;
esac
