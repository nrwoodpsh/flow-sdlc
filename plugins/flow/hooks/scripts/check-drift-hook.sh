#!/usr/bin/env bash
# drift 훅이 실제로 도는 상태인가 세션 시작에 확인한다 (SessionStart). 막지 않고 알린다.
#
# 왜 필요한가: 훅 파일(.githooks/pre-commit)은 커밋되지만
# **git config core.hooksPath 는 clone 마다 따로다.** 설정이 없으면 파일이 있어도 안 돈다.
# 그리고 조용하다 — 에러도 경고도 없이 그냥 안 막는다.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -f "$root/workflow.config.json" ] || exit 0        # flow 프로젝트가 아니다
top=$(git -C "$root" rev-parse --show-toplevel 2>/dev/null) || exit 0

# 훅이 실제로 실행되는 폴더. core.hooksPath 가 있으면 .git/hooks 는 무시된다.
hp=$(git -C "$root" config --get core.hooksPath 2>/dev/null || true)
if [ -n "$hp" ]; then
  case "$hp" in /*) dir="$hp" ;; *) dir="$top/$hp" ;; esac
else
  dir="$(git -C "$root" rev-parse --git-common-dir 2>/dev/null)/hooks"
fi

grep -ql drift "$dir/pre-commit" 2>/dev/null && exit 0

echo "⚠ flow: drift 훅이 안 돕니다 — 코드-문서 어긋남을 아무도 잡지 않습니다." 1>&2
if [ -f "$top/.githooks/pre-commit" ]; then
  echo "  파일은 있는데 설정이 없습니다:  git config core.hooksPath .githooks" 1>&2
else
  echo "  /flow:setup 으로 설치하세요." 1>&2
fi
exit 0
