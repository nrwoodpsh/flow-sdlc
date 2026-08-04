#!/usr/bin/env bash
# flow 훅 검증 — 훅은 깨져도 **조용히 안 막는다**. 눈으로는 알 수 없어 여기서 본다.
#
# 대상
#   guard-danger.sh    되돌릴 수 없는 명령을 차단하나
#   drift-hook.sh      소스만 커밋할 때 막나 · 판정이 CI 와 같나
#
# 돌리는 법:  bash scripts/tests/hooks.test.sh
# 훅을 고쳤으면 **되돌려서 실패하는지도** 확인한다 — 안 잡히면 그 케이스는 아무것도 안 지킨다.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLOW="$REPO/plugins/flow"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

# 제목
head_() { printf '\n── %s ──\n' "$1"; }

# ok <설명>            — 통과 기록
ok_()   { PASS=$((PASS+1)); printf '  ✅ %s\n' "$1"; }
# no <설명> [상세…]    — 실패 기록
no_()   { FAIL=$((FAIL+1)); printf '  ❌ %s\n' "$1"; shift; [ $# -gt 0 ] && printf '%s\n' "$*" | sed 's/^/        /'; return 0; }

# eq <기대> <실제> <설명>
eq_() {
  if [ "$1" = "$2" ]; then ok_ "$(printf '%-46s %s' "$3" "$2")"
  else no_ "$(printf '%-46s %s (기대 %s)' "$3" "$2" "$1")"; fi
}

# git 저장소를 만든다 (기본 브랜치 main 고정 · 커밋 가능 상태)
mkrepo_() {
  local d="$1"
  mkdir -p "$d"
  git -c init.defaultBranch=main init -q "$d"
  git -C "$d" config user.email test@flow.local
  git -C "$d" config user.name "flow test"
  git -C "$d" config commit.gpgsign false
}

# 훅 입력 JSON 한 줄 만들기 — <점경로> <값>
hook_json_() {
  python3 -c 'import json,sys
d={}; cur=d
ks=sys.argv[1].split(".")
for k in ks[:-1]:
    cur[k]={}; cur=cur[k]
cur[ks[-1]]=sys.argv[2]
print(json.dumps(d))' "$1" "$2"
}

summary_() {
  printf '\n%s — 통과 %d · 실패 %d\n' "${1:-테스트}" "$PASS" "$FAIL"
  [ "$FAIL" -eq 0 ]
}

# ══════════════════════════════════════════════════════════
S="$FLOW/hooks/scripts/guard-danger.sh"
bash -n "$S" && ok_ "문법" || no_ "문법"

t() {  # <기대: 차단|통과> <명령>
  local out rc got
  out=$(hook_json_ tool_input.command "$2" | bash "$S" 2>&1); rc=$?
  got=$([ "$rc" -eq 2 ] && echo 차단 || echo 통과)
  eq_ "$1" "$got" "$2"
}

head_ "차단해야 하는 것"
t 차단 "git push"
t 차단 "git push origin main"
t 차단 "git push --force"
t 차단 "git push -f origin main"
t 차단 "git   push"
t 차단 "git -C /repo push"
t 차단 "git --no-pager push"
t 차단 "npm test && git push"
t 차단 "git add . ; git push"
t 차단 "git merge feature/x"
t 차단 "git rebase main"
t 차단 "git reset --hard"
t 차단 "git reset --hard HEAD~3"
t 차단 "git clean -f"
t 차단 "git clean -fd"

head_ "통과해야 하는 것"
t 통과 "git commit -m 'x'"
t 통과 "git add ."
t 통과 "git status"
t 통과 "git diff --stat"
t 통과 "git log --oneline -5"
t 통과 "git reset HEAD~1"
t 통과 "git clean -n"
t 차단 "gh api --method POST /repos"
# ── 8회차: --abort 예외 구멍 + 7회차 차단의 케이스 공백
t 차단 'git -c note=--abort push origin main'
t 차단 'git merge --continue'
t 차단 'git rebase --continue'
t 차단 'git push --abort'
t 통과 'git rebase --abort'
t 통과 'git merge --abort'
t 통과 'git rebase --skip'
t 차단 'git pull --rebase origin main'
t 차단 'git checkout -- .'
t 차단 'git checkout -f main'
t 차단 'git restore src/a.ts'
t 차단 'git stash clear'
t 차단 'git stash drop'
t 차단 'git reflog expire --expire=now --all'
t 차단 'git update-ref -d refs/heads/x'
t 차단 'git subtree push --prefix dist origin gh-pages'
t 차단 'gh release delete v1 --yes'
t 차단 'gh secret set TOKEN --body x'
t 통과 'git restore --staged src/a.ts'
t 통과 'git checkout -b feature/x'
t 통과 'git checkout main'
t 통과 'git stash list'
t 통과 'git pull origin main'
t 통과 'gh release list'
t 통과 'gh api graphql -f query=query{viewer{login}}'

# ── 6회차: strip_heredoc 이 만든 가드 해제 경로 (구분자 오추출·인용 안 << 오인)
t 차단 'cat <<EOF; echo hi
data
EOF
git push'
t 차단 'echo "1 << two"
git push'
t 차단 'grep "<<<<<<< HEAD" f
git push'
t 차단 'cat <<EOF&&echo hi
x
EOF
git push'
t 통과 'cat <<EOF
x
  EOF
git push
EOF'

# ── 5회차: 이스케이프 인용 · 래퍼+셸 · 대문자 · here-doc 과차단 · gh 셋
t 차단 'git commit -m "fix \"quoted\" bug" && git push'
t 차단 'python3 -c "print(\"done\")" && git push'
t 차단 'timeout 30 bash -c "git push"'
t 차단 'env FOO=1 sh -c "git push"'
t 차단 'GIT push'
t 차단 'Git merge dev'
t 차단 'gh pr merge 12'
t 차단 'gh release create v1.0.0'
t 차단 'gh repo delete owner/x'
t 통과 'cat >> doc/note.md <<EOF
- git merge 는 사람이 한다
EOF'

# ── 4회차: 세그먼트 판정이 놓친 형태 (셸 -c · 래퍼 · 환경변수 · 줄이음 · 백틱)
t 차단 "sh -c \"git push\""
t 차단 "bash -lc 'git push'"
t 차단 "timeout 5 git push"
t 차단 "exec git push"
t 차단 "nice -n 10 git push"
t 차단 "if git push; then echo ok; fi"
t 차단 "while git push; do :; done"
t 차단 "PATH=/usr/bin git push"
t 차단 "GIT_SSH_COMMAND=/usr/bin/ssh git push"
t 차단 "sudo -u deploy git push"
t 차단 "git \\
push"
t "차단" "\`git push\`"
t 차단 "find . -name '*.md' -exec git push \\;"
t 차단 "gh api --field a=b /x"
t 차단 "gh api --raw-field a=b /x"
# 과차단 회귀 — 다른 세그먼트·인용 안의 플래그가 얹히면 안 된다
t 통과 "git clean --dry-run && rm -f tmp.txt"
t 통과 "git clean -n && docker build -f Dockerfile ."
t 통과 "git reset --soft HEAD~1; echo \"--hard 는 쓰지 마세요\""
t 통과 "git reset HEAD~1 && grep -rn \"reset --hard\" ."
t 통과 "git commit -m \"it's a fix\" && echo 'ok'"
t 통과 "git help push"
t 통과 "git log --grep=\"merge\""
t 통과 "./scripts/git-push.sh"
t 통과 "bash -c \"npm test\""

# ── 3회차: 앵커 정규식이 놓친 형태 (개행·선행 단어·후행 문자·롱폼)
t 차단 "cd /tmp
git push origin main"
t 차단 "sudo git push"
t 차단 "env git push"
t 차단 "GIT_SSH_COMMAND=x git push"
t 차단 "if true; then git push; fi"
t 차단 "{ git push; }"
t 차단 "echo a | xargs -I{} git push"
t 차단 "git push;echo done"
t 차단 "(git push)"
t 차단 "git push|cat"
t 차단 "git clean --force"
t 차단 "git clean -d --force"
t 차단 "gh api -X 'POST' /x"
t 차단 "gh api -f title=x /repos/o/r/issues"
t 차단 "gh api --input body.json /repos/o/r/issues"
t 차단 "gh api graphql -f query=mutation{x}"
t 차단 "gh api -X post /x"
t 차단 "git filter-branch --all"
t 차단 "git filter-repo --path x"
t 통과 "npm test"
t 통과 "git branch -a"
t 통과 "git checkout -b feature/x"
t 통과 "git rev-parse --show-toplevel"
t 통과 "echo 'git push 하지 마세요'"

# ══════════════════════════════════════════════════════════
H="$FLOW/git-hooks/drift-hook.sh"
YML="$FLOW/project-template/.github/workflows/drift-gate.yml.example"
CI="$TMP/ci-gate.js"
CHANGED="$TMP/changed.txt"

bash -n "$H" && ok_ "훅 문법" || no_ "훅 문법"

# yml 안의 node 블록을 추출하고, 파일 목록 경로만 이 테스트 것으로 바꾼다.
awk "/node - <<'EOF'/{f=1;next} f&&/^          EOF/{f=0} f" "$YML" \
  | sed 's/^          //' \
  | sed "s#/tmp/changed.txt#$CHANGED#" > "$CI"
if node --check "$CI" >/dev/null 2>&1; then ok_ "CI 스크립트 추출·문법 ($(wc -l < "$CI" | tr -d ' ') 줄)"
else no_ "CI 스크립트 추출 실패"; fi

R="$TMP/repo"
mkrepo_ "$R"
cp "$H" "$R/.git/hooks/pre-commit"; chmod +x "$R/.git/hooks/pre-commit"
# 유닛이 하나는 있어야 검사가 켜진다 — 없으면 훅이 그냥 통과한다(레거시 배려)
mkdir -p "$R/doc/01.work/user/00.login"
echo seed > "$R/doc/01.work/user/00.login/.keep"
git -C "$R" add -A >/dev/null 2>&1
git -C "$R" commit -q -m init

# config 커밋 자체는 검사 대상이 아니다 — --no-verify 로 넘긴다.
# (안 그러면 앞 케이스가 남긴 소스 파일이 딸려 가 훅에 막히고, 그게 다음 케이스를 오염시킨다)
set_cfg() {
  printf '%s\n' "$1" > "$R/workflow.config.json"
  git -C "$R" add -A >/dev/null 2>&1
  git -C "$R" commit -q --no-verify -m cfg >/dev/null 2>&1 || true
}

# 훅을 **직접** 돌린다. 커밋을 거치면 훅이 아닌 이유(전역 .gitignore·변경 없음)로
# 실패한 것을 드리프트로 잘못 읽는다 — 실제로 `.claude/*` 가 그렇게 걸렸다.
hook_says() {  # <파일> → 드리프트|아님
  mkdir -p "$(dirname "$R/$1")"; echo x >> "$R/$1"
  git -C "$R" add -f "$1" >/dev/null 2>&1
  local rc
  ( cd "$R" && bash "$H" >/dev/null 2>&1 ); rc=$?
  git -C "$R" reset -q HEAD >/dev/null 2>&1
  rm -f "$R/$1"
  [ "$rc" -ne 0 ] && echo 드리프트 || echo 아님
}

ci_says() {  # <파일> → 드리프트|아님
  printf '%s\n' "$1" > "$CHANGED"
  ( cd "$R" && node "$CI" >/dev/null 2>&1 )
  [ $? -eq 1 ] && echo 드리프트 || echo 아님
}

t() {  # <기대> <파일>
  local h c
  h=$(hook_says "$2"); c=$(ci_says "$2")
  if [ "$h" = "$1" ] && [ "$c" = "$1" ]; then
    ok_ "$(printf '%-42s 훅=%s CI=%s' "$2" "$h" "$c")"
  elif [ "$h" != "$c" ]; then
    no_ "$(printf '%-42s 훅=%s CI=%s — 두 구현이 어긋난다' "$2" "$h" "$c")"
  else
    no_ "$(printf '%-42s 훅=%s CI=%s (기대 %s)' "$2" "$h" "$c" "$1")"
  fi
}

head_ "sourceGlobs 지정 (src/** · app/**)"
set_cfg '{"drift":{"mode":"warn","sourceGlobs":["src/**","app/**"],"ignore":["**/*.md","**/*.test.*","spike/**"]}}'
t 드리프트 "src/a.ts"
t 드리프트 "app/b.js"
t 드리프트 "src/deep/nested/d.ts"
t 드리프트 "app/nested/deep/b2.js"
t 드리프트 "src/deep/nested/e.ts"
t 아님   "src/a.test.ts"
t 아님   "src/deep/nested/f.test.ts"
t 아님   "src/notes.md"
t 아님   "src/deep/nested/g.md"
t 아님   "spike/x.ts"
t 아님   "spike/deep/y.ts"
t 아님   "lib/c.ts"
t 아님   "lib/deep/c9.ts"
t 아님   "README.md"
t 아님   "app/x.test.js"
t 아님   "doc/01.work/user/00.login/2.task/00.a.md"

head_ "sourceGlobs 없음 — 기본 규칙"
set_cfg '{"drift":{"mode":"warn","ignore":["**/*.md","**/*.test.*","spike/**"]}}'
t 드리프트 "lib/c2.ts"
t 드리프트 "src/e2.ts"
t 아님   ".github/workflows/x.yml"
t 아님   ".claude/settings.json"
t 아님   "doc/README2.md"
t 아님   "spike/z.ts"

head_ "ignore 없음 — .md 는 기본 규칙이 뺀다"
set_cfg '{"drift":{"mode":"warn"}}'
t 드리프트 "lib/c3.ts"
t 드리프트 "src/f.test.ts"
t 아님   "notes2.md"

# ══════════════════════════════════════════════════════════
head_ "drift-hook.sh — pre-commit 차단"
D="$FLOW/git-hooks/drift-hook.sh"
bash -n "$D" && ok_ "문법" || no_ "문법"

# 유닛을 먼저 **커밋해 두고**(=검사 켜짐) 그다음 무엇을 스테이징하나로 가른다
dt() {  # <기대> <설명> <유닛 만드나: yes|no> <스테이징할 것>
  local r="$TMP/dh$RANDOM" rc got
  mkrepo_ "$r"
  printf '{}\n' > "$r/workflow.config.json"
  if [ "$3" = yes ]; then
    mkdir -p "$r/doc/01.work/user/00.login"
    echo seed > "$r/doc/01.work/user/00.login/.keep"
  fi
  ( cd "$r" && git add -A >/dev/null 2>&1 && git commit -q -m init >/dev/null 2>&1 )
  ( cd "$r" && eval "$4" >/dev/null 2>&1 && git add -A >/dev/null 2>&1 )
  ( cd "$r" && bash "$D" >/dev/null 2>&1 ); rc=$?
  got=$([ "$rc" -ne 0 ] && echo 차단 || echo 통과)
  eq_ "$1" "$got" "$2"
}
dt 통과 "유닛 없음 — 검사 자체를 안 한다"  no  'mkdir -p src && echo x > src/a.ts'
dt 차단 "유닛 있음 · 소스만"              yes 'mkdir -p src && echo x > src/a.ts'
dt 통과 "유닛 있음 · 소스+문서"            yes 'mkdir -p src && echo x > src/a.ts && echo d > doc/01.work/user/00.login/2.task.md'
dt 통과 "유닛 있음 · 문서만"               yes 'echo d > doc/01.work/user/00.login/2.task.md'
dt 통과 "유닛 있음 · .md 만"              yes 'echo x > README.md'
dt 통과 "스테이징이 비었다"                yes 'true'

summary_ "flow 훅"
