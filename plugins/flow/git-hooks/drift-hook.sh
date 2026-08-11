#!/usr/bin/env bash
# flow drift-hook — 커밋 전에 코드↔문서 어긋남을 막는다 (pre-commit).
#
# 왜 git 훅인가: Claude 안에서는 /flow:sync·/flow:commit 이 같은 검사를 한다.
# **Sourcetree·IDE·CLI 로 커밋하면 그게 안 돈다** — 그때를 잡는 것이 이 훅의 유일한 일이다.
#
# pre-commit 하나만 쓴다.
#   post-commit 은 이미 커밋된 뒤라 고칠 수 없고,
#   pre-push 는 push 가 우리 역할이 아니라서 쓰지 않는다.
#
# 켜고 끄는 설정 키가 없다 — 훅을 깔면 켜지고 빼면 꺼진다.
# 범위 조절만 workflow.config.json 의 drift.sourceGlobs · drift.ignore 로 한다.
#
# ── 우회: 경로별로 다르다 (층 수를 세지 말고 경로를 봐라) ──────────
#   사람 경로  `git commit --no-verify` 로 넘어간다. 사람의 판단이라 남겨 둔다.
#   AI 경로    guard-danger.sh 가 `--no-verify` 와 `-c core.hooksPath=` 를 **차단한다**
#              (guard-rules.json 의 defense-off 등급). 앞선 판은 안 막았고,
#              그래서 /flow:commit 자신이 이 훅을 끄고 커밋했다 (diag-C 3절).
set -uo pipefail

proj="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
cfg="$proj/workflow.config.json"

# 아직 문서 체인을 안 쓰는 프로젝트는 검사하지 않는다.
# 레거시에 flow 를 막 깔면 doc/01.work/ 가 비어 있는데, 그때 모든 커밋을 막으면 못 쓴다.
# 첫 유닛(도메인/유닛 두 단계 폴더)이 생기면 그때부터 검사가 켜진다.
# **이 조건을 빼지 마라** — 레거시 도입 첫날 전 커밋이 막히는 것이 실제로 겪은 일이다.
# CI(drift-gate.yml.example)의 규칙 ④ 가 같은 것이고, hooks.test.sh 가 둘을 확인한다.
if ! find "$proj/doc/01.work" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | grep -q .; then
  exit 0
fi

# --- config 배열 읽기 (drift.sourceGlobs · drift.ignore) ---
# json_get은 스칼라만 꺼내므로 배열용을 따로 둔다. 개행 구분으로 반환.
json_arr() {
  local data="$1" path="$2"
  if command -v node >/dev/null 2>&1; then
    printf '%s' "$data" | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{let o=JSON.parse(s);for(const k of process.argv[1].split("."))o=(o==null?null:o[k]);if(Array.isArray(o))process.stdout.write(o.join("\n"))}catch(e){}})' "$path"
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$data" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 for k in sys.argv[1].split("."): d=d.get(k) if isinstance(d,dict) else None
 sys.stdout.write("\n".join(d) if isinstance(d,list) else "")
except Exception: pass' "$path"
  elif command -v perl >/dev/null 2>&1; then
    printf '%s' "$data" | perl -MJSON::PP -0777 -ne 'BEGIN{@k=split/\./,$ARGV[0];shift @ARGV} my $d=eval{decode_json($_)}; for my $key (@k){$d = ref($d) eq "HASH" ? $d->{$key} : undef} print join("\n",@$d) if ref($d) eq "ARRAY";' "$path"
  fi
}

cfgdata_all=""
[ -f "$cfg" ] && cfgdata_all=$(cat "$cfg")
source_globs=$(json_arr "$cfgdata_all" drift.sourceGlobs)
ignore_globs=$(json_arr "$cfgdata_all" drift.ignore)

# 경로가 glob 목록 중 하나에 맞나. `**/x` 패턴은 `**/`를 벗긴 것도 함께 본다
# (bash case의 `**/`는 `/`를 요구해 최상위 파일에 안 맞기 때문).
matches_any() {
  local f="$1" g g2
  shift
  for g in "$@"; do
    [ -n "$g" ] || continue
    case "$f" in $g) return 0 ;; esac
    g2="${g#\*\*/}"
    [ "$g2" != "$g" ] && case "$f" in $g2) return 0 ;; esac
  done
  return 1
}

# 소스 판정 — 판정 규칙 정본은 `drift-check` 스킬이다. 여기와 CI(drift-gate.yml)를 함께 맞춘다.
#   ① drift.ignore 에 맞으면 소스가 아니다 (기본: **/*.md · **/*.test.* · spike/**)
#   ② drift.sourceGlobs 가 있으면 그 안에 있는 것만 소스
#   ③ 없으면 기본값 — doc/ · spike/ · .claude/ · .github/ 밖이고 .md 가 아닌 것
is_source() {
  local f="$1"
  # `set -f`로 파일명 확장을 끈다. 끄지 않으면 따옴표 없는 $ignore_globs·$source_globs가
  # 단어 분리와 함께 **파일명 확장**까지 받아 config의 glob이 디스크의 실제 이름으로 바뀐다.
  #   src/ 에 deep/ 이 있으면  `src/**` → `src/deep`  →  src/deep/nested/d.ts 를 놓친다.
  # 조용히 소스 판정에서 빠지므로 반드시 끈 상태로 비교한다.
  # **`set -f` 를 빼지 마라** — 실제로 하위 파일을 놓쳤던 사고고, 통과 숫자로는 안 보인다.
  set -f
  # shellcheck disable=SC2086
  if matches_any "$f" $ignore_globs; then set +f; return 1; fi
  if [ -n "$source_globs" ]; then
    # shellcheck disable=SC2086
    if matches_any "$f" $source_globs; then set +f; return 0; fi
    set +f; return 1
  fi
  set +f
  case "$f" in
    doc/*|spike/*|.claude/*|.github/*) return 1 ;;
    *.md) return 1 ;;
  esac
  return 0
}

# 소스 변경이 있는데 작업 문서(doc/01.work/)가 함께 안 왔으면 드리프트.
# `2.task`·`3.contract`·`7.summary` 어느 것이든 인정한다 — 작은 변경에 요약을 강제하지 않는다.
is_drift() {
  local files f src=0 docs=0
  files=$(git diff --cached --name-only)
  [ -n "$files" ] || return 1
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in doc/01.work/*) docs=1 ;; esac
    is_source "$f" && src=1
  done <<EOF
$files
EOF
  [ "$src" -eq 1 ] && [ "$docs" -eq 0 ]
}

if is_drift; then
  echo "" 1>&2
  echo "⛔ flow drift: 소스만 바뀌고 작업 문서(doc/01.work/)가 안 왔습니다. 커밋을 막습니다." 1>&2
  echo "" 1>&2
  echo "   문서가 낡으면 다음 세션이 그 낡은 문서를 진실로 믿습니다." 1>&2
  echo "   → Claude Code 에서 /flow:sync 로 문서를 맞춘 뒤 커밋하세요." 1>&2
  echo "   → /flow:commit 을 쓰면 이 검사를 먼저 하고 커밋합니다." 1>&2
  echo "" 1>&2
  echo "   작업 중 커밋이라 지금은 넘기려면:  git commit --no-verify" 1>&2
  echo "   (사람이 자기 터미널에서 하는 경우입니다. Claude 세션에서는 guard 가 막습니다.)" 1>&2
  echo "" 1>&2
  exit 1
fi

exit 0
