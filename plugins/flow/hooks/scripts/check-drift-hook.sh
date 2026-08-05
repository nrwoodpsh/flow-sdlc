#!/usr/bin/env bash
# drift 훅이 실제로 도는 상태인가 세션 시작에 확인한다 (SessionStart). 막지 않고 알린다.
#
# 왜 필요한가: 훅 파일(.githooks/pre-commit)은 커밋되지만
# **git config core.hooksPath 는 clone 마다 따로다.** 설정이 없으면 파일이 있어도 안 돈다.
# 그리고 조용하다 — 에러도 경고도 없이 그냥 안 막는다.
#
# **막지 않는다(항상 exit 0).** 세션 시작을 막으면 flow 를 아예 못 쓴다.
# v1 에서 이 파일은 테스트가 0건이었다(diag-C 3절). 하는 일이
#   core.hooksPath 해석 · git-common-dir 폴백 · pre-commit 내용 확인
# 셋인데 전부 **조용히 틀리기 쉬운** 종류다 — 틀리면 "훅이 돈다"고 잘못 안심시킨다.
# 그래서 v2 는 hooks.test.sh 에 케이스를 붙였다. 고칠 때 되돌려서 실패하는지도 확인해라.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
[ -f "$root/workflow.config.json" ] || exit 0        # flow 프로젝트가 아니다
top=$(git -C "$root" rev-parse --show-toplevel 2>/dev/null) || exit 0

# 훅이 실제로 실행되는 폴더. core.hooksPath 가 있으면 .git/hooks 는 무시된다.
# 상대 경로는 **저장소 루트 기준**이다 (git 문서: relative to the top-level directory).
hp=$(git -C "$root" config --get core.hooksPath 2>/dev/null || true)
if [ -n "$hp" ]; then
  case "$hp" in /*) dir="$hp" ;; *) dir="$top/$hp" ;; esac
else
  # `--git-common-dir` 이어야 한다. 워크트리에서는 `--git-dir` 이
  # `.git/worktrees/<name>` 을 가리키고 그 아래엔 hooks/ 가 없다 — 본체를 봐야 한다.
  dir="$(git -C "$root" rev-parse --git-common-dir 2>/dev/null)/hooks"
fi

# `-l` 은 파일명을, `-q` 는 조용히 — 둘 다 주면 종료코드만 쓴다. 내용에 `drift` 가 있어야
# **우리** 훅이다. 남의 pre-commit 이 깔려 있으면 우리 검사는 안 도는 것이다.
grep -ql drift "$dir/pre-commit" 2>/dev/null && exit 0

echo "⚠ flow: drift 훅이 안 돕니다 — 코드-문서 어긋남을 아무도 잡지 않습니다." 1>&2
if [ -f "$top/.githooks/pre-commit" ]; then
  echo "  파일은 있는데 설정이 없습니다:  git config core.hooksPath .githooks" 1>&2
else
  echo "  /flow:setup 으로 설치하세요." 1>&2
fi
exit 0
