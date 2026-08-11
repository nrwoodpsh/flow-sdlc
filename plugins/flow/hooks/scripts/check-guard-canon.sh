#!/usr/bin/env bash
# 가드·게이트의 **판정 근거가 읽히는 상태인가** 세션 시작에 확인한다 (SessionStart). 막지 않고 알린다.
#
# ── 왜 이 스크립트가 있나 (비대칭을 메운다) ─────────────────────────
# 두 층이 정본 부재에 다르게 반응하고, 둘 다 근거가 있다.
#   guard-danger.sh    guard-rules.json 없음 → **경고 후 통과**(fail-open).
#                      막으면 모든 Bash 가 멈춰 사람이 훅을 지운다. 그러면 층이 영구히 없어진다.
#   gate-source-write.sh  flow.topology.json 없음 → **ask**. 쓰기 때만 도는 드문 훅이라 감당된다.
#
# 문제는 fail-open 쪽이다. **되돌릴 수 없는 명령을 막는 층이 stderr 한 줄과 함께 조용히 꺼진다.**
# 바쁜 세션에서 그 한 줄은 놓친다 — 그리고 놓친 상태가 "안전하다"로 읽힌다.
# 아무 말 없이 안 막는 상태가 가장 나쁘다 — 있다고 읽히면서 없다.
#
# **그래서 fail-open 은 유지하고, 세션 시작에 한 번 크게 알린다.**
#   막는 쪽으로 바꾸지 않는 이유: 과차단은 사람이 훅을 끄게 만들고, 끄면 되돌릴 수 없는 명령까지
#   전부 열린다. 즉 fail-closed 의 최악(층 삭제)이 fail-open 의 최악(그 세션 무방비)보다 나쁘다.
#   대신 "조용함"만 없앤다 — 그게 이 스크립트가 고치는 유일한 것이다.
#
# check-drift-hook.sh 와 같은 모양이다: **항상 exit 0.** 세션 시작을 막으면 flow 를 아예 못 쓴다.
set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd) || here=.

# 정본 찾기 — 훅 본체와 **같은 순서**로 찾는다. 다르면 "여기 있다"고 알리는데 훅은 못 찾는다.
find_canon() {   # <환경변수 값> <파일 이름>
  local envv="$1" name="$2" c
  if [ -n "$envv" ]; then printf '%s' "$envv"; return 0; fi
  for c in "${CLAUDE_PLUGIN_ROOT:-}/$name" "$here/../../$name"; do
    [ -f "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

# 메시지를 stderr(사람)와 `additionalContext`(모델) **양쪽**으로 낸다.
# 실측이 가르친 것 — **stderr 만 쓰면 아무도 못 본다.**
# 실제로 이 훅이 발화한 세션이 가드가 열린 줄 모르고 `--no-verify` 를 시도했다.
# 머리말이 "조용함만 없앤다"고 적어 둔 그 하나를 못 하고 있었다.
MSGS=
say() {                       # <줄> — 사람에게 지금, 모델에게 마지막에
  printf '%s\n' "$1" 1>&2
  case "$MSGS" in '') MSGS=$1 ;; *) MSGS="$MSGS · $1" ;; esac
}

bad=0

rules=$(find_canon "${FLOW_GUARD_RULES:-}" guard-rules.json) || rules=
if [ -z "$rules" ] || [ ! -f "$rules" ]; then
  say "⛔ flow: 차단 목록 정본(guard-rules.json)이 없습니다 — **되돌릴 수 없는 명령을 아무것도 막지 않습니다.**"
  say "   push·reset --hard·commit --no-verify 가 전부 통과합니다."
  bad=1
elif command -v python3 >/dev/null 2>&1 &&
     ! python3 -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
rs=d.get("rules")
assert isinstance(rs,list) and rs' "$rules" >/dev/null 2>&1; then
  say "⛔ flow: 차단 목록 정본(guard-rules.json)이 깨졌습니다 — **아무것도 막지 않습니다.**"
  say "   파일: $rules"
  bad=1
fi

topo=$(find_canon "${FLOW_TOPOLOGY:-}" flow.topology.json) || topo=
if [ -z "$topo" ] || [ ! -f "$topo" ]; then
  say "⚠ flow: 게이트 판정 근거(flow.topology.json)가 없습니다 — 소스 쓰기마다 확인을 묻습니다."
  bad=1
elif command -v python3 >/dev/null 2>&1 &&
     ! python3 -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
assert isinstance(d.get("gate"),dict)' "$topo" >/dev/null 2>&1; then
  say "⚠ flow: 게이트 판정 근거(flow.topology.json)가 깨졌습니다 — 소스 쓰기마다 확인을 묻습니다."
  say "   파일: $topo"
  bad=1
fi

if [ "$bad" -ne 0 ]; then
  say "→ 플러그인 설치를 다시 확인하세요. 이 상태로 계속하면 그 층은 없는 것입니다."
  # 따옴표·개행이 섞이면 JSON 이 깨진다(실측으로 한 번 깨뜨렸다) — 한 줄로 잇고 `"` 를 뗀다.
  ctx=$(printf '%s' "$MSGS" | tr -d '"' | tr '\n' ' ')
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
fi
exit 0
