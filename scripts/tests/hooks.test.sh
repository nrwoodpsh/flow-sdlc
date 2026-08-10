#!/usr/bin/env bash
# flow 훅 검증 — 훅은 깨져도 **조용히 안 막는다**. 눈으로는 알 수 없어 여기서 본다.
#
# 대상
#   guard-danger.sh      되돌릴 수 없는 명령을 차단하나 · 정본(guard-rules.json)을 제대로 읽나
#   drift-hook.sh        소스만 커밋할 때 막나 · 판정이 CI 와 같나
#   check-drift-hook.sh  훅이 안 도는 상태를 알아채나  ← v1 은 테스트가 0건이었다 (diag-C 3절)
#
# 돌리는 법:  bash scripts/tests/hooks.test.sh
#
# ── v1 과 달라진 것: 가드 케이스를 손으로 적지 않는다 ────────────────
# 케이스는 `plugins/flow/guard-rules.json` 의 `expect` 에서 **생성한다.**
# 그래서 목록과 테스트가 어긋날 수 없다. 두 방향을 다 본다.
#   ① expect 가 가리키는 규칙이 rules 에 없으면 실패  → 규칙을 지우면 그 케이스가 실패한다
#   ② rules 의 규칙에 block/ask 케이스가 없으면 실패  → 케이스 없는 규칙을 못 넣는다
# **되돌림 확인**: guard-rules.json 에서 규칙 하나를 지우고 돌려 봐라. ①과 그 규칙의
# block 케이스가 함께 실패해야 한다. 안 실패하면 그 케이스는 아무것도 지키지 않는다.
#
# 아래 "스캐너 회귀"만 이 파일에 손으로 남긴다 — 그건 차단 목록이 아니라
# **인용/here-doc 파서가 실제로 낸 사고의 기록**이다. 규칙을 지워도 파서는 그대로다.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLOW="$REPO/plugins/flow"
RULES="${FLOW}/guard-rules.json"
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
  if [ "$1" = "$2" ]; then ok_ "$(printf '%-52s %s' "$3" "$2")"
  else no_ "$(printf '%-52s %s (기대 %s)' "$3" "$2" "$1")"; fi
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
# guard-danger.sh
# ══════════════════════════════════════════════════════════
S="$FLOW/hooks/scripts/guard-danger.sh"
head_ "guard-danger.sh — 뼈대"
bash -n "$S" && ok_ "문법" || no_ "문법"
[ -f "$RULES" ] && ok_ "차단 목록 정본 존재 ($RULES)" || no_ "차단 목록 정본이 없다 — $RULES"
python3 -c 'import json,sys; json.load(open(sys.argv[1],encoding="utf-8"))' "$RULES" \
  && ok_ "정본 JSON 파싱" || no_ "정본 JSON 파싱 실패"

# t <기대: 차단|확인|통과> <명령> [라벨]
#   차단 = exit 2 · 확인 = exit 0 + permissionDecision ask · 통과 = exit 0 + 출력 없음
t() {
  local out rc got
  out=$(hook_json_ tool_input.command "$2" | bash "$S" 2>&1); rc=$?
  if [ "$rc" -eq 2 ]; then got=차단
  elif printf '%s' "$out" | grep -q '"permissionDecision"[[:space:]]*:[[:space:]]*"ask"'; then got=확인
  else got=통과; fi
  eq_ "$1" "$got" "${3:-$2}"
}

# ── 케이스를 정본에서 생성한다 ────────────────────────────────
# 한 줄 = <기대>\037<명령>\037<규칙 id>. 개행 있는 명령은 여기 안 담는다(정본에도 없다).
gen_expect() {
  python3 -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
V={"block":"차단","ask":"확인","pass":"통과"}
for e in d.get("expect",[]):
    v=V.get(e.get("verdict"))
    if v is None: sys.exit("expect 의 verdict 가 block/ask/pass 가 아니다: %r" % (e,))
    cmd=e.get("cmd","")
    if not cmd or "\n" in cmd: sys.exit("expect 의 cmd 가 비었거나 개행이 있다: %r" % (e,))
    print("\x1f".join([v, cmd, e.get("rule","")]))' "$1"
}

# 정본이 스스로 어긋나지 않는지 — 이게 "목록과 테스트가 어긋날 수 없다"의 본체다
head_ "정본↔케이스 상호 대조 (규칙을 지우면 여기가 실패한다)"
xref=$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
rules=d.get("rules") or []
ids=[r.get("id") for r in rules]
out=[]
dup=set(x for x in ids if ids.count(x)>1)
if dup: out.append("규칙 id 중복: "+", ".join(sorted(dup)))
idset=set(ids)
covered=set()
for e in d.get("expect",[]):
    rid=e.get("rule",""); v=e.get("verdict")
    if v in ("block","ask"):
        if not rid: out.append("block/ask 케이스에 rule 이 없다: "+e.get("cmd",""))
        elif rid not in idset: out.append("케이스가 없는 규칙을 가리킨다 — rule=%s · cmd=%s" % (rid, e.get("cmd","")))
        else: covered.add(rid)
    elif rid and rid not in idset:
        out.append("pass 케이스가 없는 규칙을 가리킨다 — rule=%s · cmd=%s" % (rid, e.get("cmd","")))
missing=[i for i in ids if i not in covered]
if missing: out.append("block/ask 케이스가 없는 규칙: "+", ".join(missing))
for r in rules:
    if not r.get("why"): out.append("why 가 없는 규칙: "+str(r.get("id")))
    if r.get("class") not in (d.get("classes") or {}): out.append("classes 에 없는 등급: %s (%s)" % (r.get("class"), r.get("id")))
sys.stdout.write("\n".join(out))' "$RULES")
if [ -z "$xref" ]; then
  ok_ "$(printf '규칙 %s개 · 케이스 %s개 — 서로 가리키는 것이 다 있다' \
      "$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1],encoding="utf-8"))["rules"]))' "$RULES")" \
      "$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1],encoding="utf-8"))["expect"]))' "$RULES")")"
else
  no_ "정본↔케이스가 어긋난다" "$xref"
fi

# 정본을 읽는 구현이 셋(python3·node·perl)인데 **한 번에 도는 것은 하나**다.
# 나머지 둘은 테스트가 직접 부르지 않으면 조용히 썩는다 — 실제로 그랬다:
#   node 로더는 argv 색인이 하나 밀려 있었고, perl 로더는 인코딩 때문에
#   경고를 뱉거나 통째로 실패했다. **둘 다 통과 숫자에 아무 흔적도 남기지 않았다.**
# 그래서 스크립트의 `--dump-rules` 문으로 **실제 로더 코드**를 부른다 — 테스트가 사본을 두지 않는다.
head_ "정본을 읽는 세 구현 대조 (python3 ↔ node ↔ perl)"
dumpref= ; dumpref_name=
for L in python3 node perl; do
  if ! command -v "$L" >/dev/null 2>&1; then
    printf '  ⚠ %s\n' "$L 이 없어 건너뜀 (통과로 세지 않는다)"; continue
  fi
  derr="$TMP/dump-err.$L"
  dout=$(bash "$S" --dump-rules "$L" 2>"$derr"); drc=$?
  if [ "$drc" -ne 0 ] || [ -z "$dout" ]; then
    no_ "$L 로더가 정본을 못 읽는다 — 이 환경에서는 가드가 안 돈다" "rc=$drc $(cat "$derr")"; continue
  fi
  # stderr 가 조용해야 한다. 훅의 stderr 는 사용자에게 그대로 보인다.
  if [ -s "$derr" ]; then
    no_ "$L 로더가 stderr 로 무언가 뱉는다" "$(cat "$derr")"; continue
  fi
  if [ -z "$dumpref" ]; then
    dumpref=$dout; dumpref_name=$L
    ok_ "$(printf '%s 로더 — 규칙 %s줄 · stderr 조용' "$L" "$(printf '%s\n' "$dout" | wc -l | tr -d ' ')")"
  elif [ "$dout" = "$dumpref" ]; then
    ok_ "$L 로더 — $dumpref_name 와 같은 결과"
  else
    no_ "$L 로더가 $dumpref_name 와 어긋난다 — 설치 환경에 따라 판정이 달라진다" \
        "$(diff <(printf '%s' "$dumpref") <(printf '%s' "$dout") | head -20)"
  fi
done
# 없는 로더를 요구하면 **자동 선택으로 떨어져야** 한다 — 실패하면 그게 가드를 끄는 길이 된다
zzout=$(bash "$S" --dump-rules zzz-nope 2>/dev/null); zzrc=$?
if [ "$zzrc" -eq 0 ] && [ -n "$zzout" ]; then ok_ "모르는 로더 이름 → 자동 선택으로 떨어진다"
else no_ "모르는 로더 이름이 로더를 통째로 끈다 — 가드를 끄는 길이다" "rc=$zzrc"; fi

head_ "차단 목록 — 케이스는 guard-rules.json 에서 생성"
while IFS=$'\037' read -r want cmd rid; do
  [ -n "$cmd" ] || continue
  t "$want" "$cmd" "$(printf '[%s] %s' "$rid" "$cmd")"
done <<EOF
$(gen_expect "$RULES")
EOF

# 정본이 없으면 **조용히** 통과하면 안 된다 — 그 상태가 "안전하다"로 읽힌다
head_ "정본이 없을 때 — 조용히 통과하지 않는다"
missout=$(FLOW_GUARD_RULES="$TMP/nope.json" hook_json_ tool_input.command "git push" \
  | FLOW_GUARD_RULES="$TMP/nope.json" bash "$S" 2>&1); missrc=$?
if [ "$missrc" -eq 0 ] && printf '%s' "$missout" | grep -q "정본"; then
  ok_ "정본 없음 → 통과하지만 경고를 낸다"
else
  no_ "정본 없음 → 경고 없이 통과했다(또는 전부 막았다)" "rc=$missrc out=$missout"
fi
printf '{"rules":[]}' > "$TMP/empty.json"
emptyout=$(FLOW_GUARD_RULES="$TMP/empty.json" hook_json_ tool_input.command "git push" \
  | FLOW_GUARD_RULES="$TMP/empty.json" bash "$S" 2>&1); emptyrc=$?
if [ "$emptyrc" -eq 0 ] && printf '%s' "$emptyout" | grep -q "정본"; then
  ok_ "빈 규칙 목록 → 경고를 낸다"
else
  no_ "빈 규칙 목록을 정상으로 받아들였다" "rc=$emptyrc out=$emptyout"
fi
printf '{"rules":[{"id":"x","tool":"git","words":"push","level":"nope","why":"y"}]}' > "$TMP/bad.json"
badout=$(FLOW_GUARD_RULES="$TMP/bad.json" hook_json_ tool_input.command "git push" \
  | FLOW_GUARD_RULES="$TMP/bad.json" bash "$S" 2>&1); badrc=$?
if printf '%s' "$badout" | grep -q "정본"; then ok_ "모르는 등급 → 정본을 거부한다"
else no_ "모르는 등급을 조용히 받아들였다" "rc=$badrc out=$badout"; fi

# ══════════════════════════════════════════════════════════
# 스캐너 회귀 — **차단 목록이 아니라 파서의 사고 기록이다.**
# v1 에서 그대로 이식했다. 규칙을 지워도 이 케이스들은 남아야 한다.
# ══════════════════════════════════════════════════════════
head_ "스캐너 회귀 — strip_heredoc 이 만든 가드 해제 경로 (6회차)"
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

head_ "스캐너 회귀 — 이스케이프 인용 · 래퍼+셸 · 대문자 (5회차)"
t 차단 'git commit -m "fix \"quoted\" bug" && git push'
t 차단 'python3 -c "print(\"done\")" && git push'
t 차단 'timeout 30 bash -c "git push"'
t 차단 'env FOO=1 sh -c "git push"'
t 차단 'GIT push'
t 차단 'Git merge dev'
t 통과 'cat >> doc/note.md <<EOF
- git merge 는 사람이 한다
EOF'

head_ "스캐너 회귀 — 세그먼트 판정이 놓친 형태 (4회차)"
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

head_ "스캐너 회귀 — 앵커 정규식이 놓친 형태 (3회차)"
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

head_ "스캐너 회귀 — 인용 삽입으로 낱말을 쪼개는 것 (반증 H1)"
# **셸에서 인용은 단어 경계가 아니다.** `git p"u"sh` 는 한 낱말 `push` 다.
# 원래는 낱말을 SB(인용 내용을 공백으로 바꾼 것)에서 뽑아서 `p`·`sh` 로 갈렸고,
# `reset --hard`·`commit --no-verify` 까지 한 글자 인용으로 통과했다.
# 이 케이스들이 "단어를 먼저 나누고 낱말 안에서 인용을 벗긴다"를 지킨다.
t 차단 'git p"u"sh origin main'
t 차단 "git p'u'sh origin main"
t 차단 'git pu""sh origin main'
t 차단 'git "push"'
t 차단 'g"i"t push'
t 차단 'git res"e"t --hard HEAD'
t 차단 'git commit --no-veri"f"y'
t 차단 'gh secret "set" X --body y'
t 차단 'gh "pr" merge 1'
t 차단 'git "merge" dev'
t 차단 '"git" "push"'
t 차단 'git br"a"nch -D feature/x'
# 반대 방향 — 인용 안의 **한 낱말**은 명령이 아니다. 이게 깨지면 커밋 메시지가 전부 막힌다
t 통과 'git commit -m "git push"'
t 통과 'git commit -m "git push 하지 마세요"'
t 통과 'echo "git push"'
t 통과 'echo "git reset --hard"'
t 통과 'git commit -m "-n 을 쓰지 마세요"'
t 통과 'git commit -m "--no-verify 는 쓰지 않는다"'
t 통과 'nice -n 10 git commit -m x'
t 통과 'git commit -m "gh secret set"'
t 통과 'git commit --message "-n"'
t 통과 'git log --grep="reset --hard"'
# 이스케이프도 낱말 안이면 붙는다 (`\` 를 낱말 경계로 보면 또 갈린다)
t 차단 'g\it push'
t 차단 'git pus\h origin'
t 차단 'git commit --no\-verify'
t 차단 'gh api --met"h"od POST /x'

# **여기 둘은 남은 한계를 못 박는 케이스다.** 고쳐지면 이 기대값을 바꿔라 —
# 지금 통과하는 것이 사고가 아니라 적어 둔 한계임을 테스트가 증명해야 한다.
# (guard-rules.json 의 limits · guard-danger.sh 머리말의 limit 줄과 짝이다)
t 통과 "git \$'p\\x75sh'"       "[한계] ANSI-C 인용 — 셸은 push 로 실행한다"
t 통과 'p=push; git $p'         "[한계] 변수로 쪼갠 명령"
# 반대로 이건 **새로 생긴 과차단**이다. 낱말별로 인용하면 실행과 구별할 수 없다
t 차단 'echo "git" "push"'      "[과차단] 낱말별 인용은 막는다"
t 통과 'echo "git push"'        "한 낱말로 인용하면 통과한다"

head_ "스캐너 회귀 — 과차단 (다른 세그먼트·인용 안의 플래그가 얹히면 안 된다)"
t 통과 "git clean --dry-run && rm -f tmp.txt"
t 통과 "git clean -n && docker build -f Dockerfile ."
t 통과 "git reset --soft HEAD~1; echo \"--hard 는 쓰지 마세요\""
t 통과 "git reset HEAD~1 && grep -rn \"reset --hard\" ."
t 통과 "git commit -m \"it's a fix\" && echo 'ok'"
t 통과 "git help push"
t 통과 "git log --grep=\"merge\""
t 통과 "./scripts/git-push.sh"
t 통과 "bash -c \"npm test\""
t 통과 "npm test"
t 통과 "git rev-parse --show-toplevel"
t 통과 "echo 'git push 하지 마세요'"
# v2 새 규칙의 과차단 회귀 — 정본을 데이터로 옮기며 늘어난 표면이다
t 통과 "git status && grep -rn \"core.hooksPath\" ."
t 통과 "git log --oneline -5"
t 통과 "git add ."
# ask 가 block 을 가리면 안 된다 — 명령 전체를 다 보고 판정해야 한다
t 차단 "git commit --amend -m x && git push"
t 차단 "git stash pop && git push"

# ══════════════════════════════════════════════════════════
# drift-hook.sh ↔ CI(drift-gate.yml.example) 나란히 판정
# 같은 규칙의 두 구현을 같은 입력에 물려 **"두 구현이 어긋난다"를 별도 실패로 분리**한다.
# ══════════════════════════════════════════════════════════
H="$FLOW/git-hooks/drift-hook.sh"
YML="$FLOW/project-template/.github/workflows/drift-gate.yml.example"
CI="$TMP/ci-gate.js"
CHANGED="$TMP/changed.txt"

head_ "drift-hook.sh ↔ CI — 뼈대"
bash -n "$H" && ok_ "훅 문법" || no_ "훅 문법"

CI_OK=
if [ ! -f "$YML" ]; then
  printf '  ⚠ %s\n' "CI 예시($YML)가 없어 나란히 판정을 건너뜀 — 훅만 본다 (통과로 세지 않는다)"
elif ! command -v node >/dev/null 2>&1; then
  printf '  ⚠ %s\n' "node 가 없어 나란히 판정을 건너뜀 — 훅만 본다 (통과로 세지 않는다)"
else
  # yml 안의 node 블록을 추출하고, 파일 목록 경로만 이 테스트 것으로 바꾼다.
  awk "/node - <<'EOF'/{f=1;next} f&&/^          EOF/{f=0} f" "$YML" \
    | sed 's/^          //' \
    | sed "s#/tmp/changed.txt#$CHANGED#" > "$CI"
  if node --check "$CI" >/dev/null 2>&1; then
    ok_ "CI 스크립트 추출·문법 ($(wc -l < "$CI" | tr -d ' ') 줄)"; CI_OK=1
  else no_ "CI 스크립트 추출 실패"; fi
fi

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
  h=$(hook_says "$2")
  if [ -z "$CI_OK" ]; then eq_ "$1" "$h" "$(printf '%-38s 훅만' "$2")"; return 0; fi
  c=$(ci_says "$2")
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
# `set -f` 회귀 — 글로브가 디스크 파일로 확장되면 하위 파일을 조용히 놓친다. 3단 깊이로 본다.
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
  ( cd "$r" && bash "$H" >/dev/null 2>&1 ); rc=$?
  got=$([ "$rc" -ne 0 ] && echo 차단 || echo 통과)
  eq_ "$1" "$got" "$2"
}
# **이 첫 줄을 지우지 마라** — 레거시에 flow 를 갓 깔면 doc/01.work/ 가 비는데,
# 그때 전 커밋을 막으면 프로젝트를 못 쓴다. CI 규칙 ④ 와 짝이다.
dt 통과 "유닛 없음 — 검사 자체를 안 한다"  no  'mkdir -p src && echo x > src/a.ts'
dt 차단 "유닛 있음 · 소스만"              yes 'mkdir -p src && echo x > src/a.ts'
dt 통과 "유닛 있음 · 소스+문서"            yes 'mkdir -p src && echo x > src/a.ts && echo d > doc/01.work/user/00.login/2.task.md'
dt 통과 "유닛 있음 · 문서만"               yes 'echo d > doc/01.work/user/00.login/2.task.md'
dt 통과 "유닛 있음 · .md 만"              yes 'echo x > README.md'
dt 통과 "스테이징이 비었다"                yes 'true'

# ══════════════════════════════════════════════════════════
# check-drift-hook.sh — **v1 은 테스트가 0건이었다** (diag-C 3절).
# 하는 일 셋(core.hooksPath 해석 · git-common-dir 폴백 · pre-commit 내용 확인)이
# 전부 조용히 틀리기 쉽고, 틀리면 "훅이 돈다"고 **잘못 안심시킨다.**
# ══════════════════════════════════════════════════════════
head_ "check-drift-hook.sh — 훅이 안 도는 상태를 알아채나"
C="$FLOW/hooks/scripts/check-drift-hook.sh"
bash -n "$C" && ok_ "문법" || no_ "문법"

# ct <기대: 경고|조용> <설명> <셋업 함수 본문>
#   경고 = stderr 에 "drift 훅이 안 돕니다" · 조용 = 아무 말 없음
#   **어느 쪽이든 exit 0 이어야 한다** — 세션 시작을 막으면 flow 를 아예 못 쓴다.
ct() {
  local r="$TMP/ck$RANDOM" out rc got
  mkrepo_ "$r"
  ( cd "$r" && eval "$3" ) >/dev/null 2>&1
  out=$( cd "$r" && CLAUDE_PROJECT_DIR="$r" bash "$C" 2>&1 ); rc=$?
  if printf '%s' "$out" | grep -q "drift 훅이 안 돕니다"; then got=경고; else got=조용; fi
  eq_ "$1" "$got" "$2"
  eq_ 0 "$rc" "  └ 막지 않는다 (exit 0)"
}

ct 조용 "flow 프로젝트가 아니다 — 아무 말 안 한다" '
  true'
ct 경고 "설정도 파일도 없다 → setup 안내" '
  printf "{}\n" > workflow.config.json'
ct 경고 ".githooks/pre-commit 은 있고 설정이 없다" '
  printf "{}\n" > workflow.config.json
  mkdir -p .githooks
  printf "#!/usr/bin/env bash\n# flow drift-hook\n" > .githooks/pre-commit'
ct 조용 "core.hooksPath 상대 경로 + drift 훅" '
  printf "{}\n" > workflow.config.json
  mkdir -p .githooks
  printf "#!/usr/bin/env bash\n# flow drift-hook\n" > .githooks/pre-commit
  git config core.hooksPath .githooks'
ct 조용 ".git/hooks 에 drift 훅 (설정 없음 · 기본 경로)" '
  printf "{}\n" > workflow.config.json
  printf "#!/usr/bin/env bash\n# flow drift-hook\n" > .git/hooks/pre-commit'
ct 경고 "pre-commit 은 있는데 drift 가 아니다 (남의 훅)" '
  printf "{}\n" > workflow.config.json
  printf "#!/usr/bin/env bash\nnpx lint-staged\n" > .git/hooks/pre-commit'
ct 경고 "core.hooksPath 가 빈 폴더를 가리킨다" '
  printf "{}\n" > workflow.config.json
  mkdir -p .githooks
  printf "#!/usr/bin/env bash\n# flow drift-hook\n" > .git/hooks/pre-commit
  git config core.hooksPath .githooks'

# core.hooksPath 절대 경로 — 상대 경로만 처리하면 조용히 틀린다
absr="$TMP/ck-abs"; mkrepo_ "$absr"
mkdir -p "$TMP/abs-hooks"
printf '#!/usr/bin/env bash\n# flow drift-hook\n' > "$TMP/abs-hooks/pre-commit"
printf '{}\n' > "$absr/workflow.config.json"
git -C "$absr" config core.hooksPath "$TMP/abs-hooks"
absout=$( cd "$absr" && CLAUDE_PROJECT_DIR="$absr" bash "$C" 2>&1 )
if printf '%s' "$absout" | grep -q "drift 훅이 안 돕니다"; then
  no_ "core.hooksPath 절대 경로를 해석하지 못한다" "$absout"
else ok_ "core.hooksPath 절대 경로"; fi

# 워크트리 — `--git-dir` 은 .git/worktrees/<name> 을 가리키고 그 아래엔 hooks/ 가 없다.
# `--git-common-dir` 로 본체를 봐야 한다. 이걸 틀리면 훅이 도는데도 경고가 뜬다.
wtr="$TMP/ck-wt"; mkrepo_ "$wtr"
printf '{}\n' > "$wtr/workflow.config.json"
printf '#!/usr/bin/env bash\n# flow drift-hook\n' > "$wtr/.git/hooks/pre-commit"
git -C "$wtr" add -A >/dev/null 2>&1; git -C "$wtr" commit -q -m init >/dev/null 2>&1
if git -C "$wtr" worktree add -q "$TMP/ck-wt-linked" -b wt >/dev/null 2>&1; then
  printf '{}\n' > "$TMP/ck-wt-linked/workflow.config.json"
  wtout=$( cd "$TMP/ck-wt-linked" && CLAUDE_PROJECT_DIR="$TMP/ck-wt-linked" bash "$C" 2>&1 )
  if printf '%s' "$wtout" | grep -q "drift 훅이 안 돕니다"; then
    no_ "워크트리에서 훅을 못 찾는다 — git-common-dir 폴백이 깨졌다" "$wtout"
  else ok_ "워크트리 — git-common-dir 폴백"; fi
else
  printf '  ⚠ %s\n' "git worktree add 실패 — 폴백 케이스를 건너뜀 (통과로 세지 않는다)"
fi

# ══════════════════════════════════════════════════════════
# hooks.json 배선 — **matcher 가 도구 이름이라 어느 훅이 어느 경로를 덮는지가 여기서 정해진다.**
# 경로가 틀리면 훅이 조용히 안 돈다. 그게 v1 이 앓던 "약속만 있고 기계는 없다"의 배선 판이다.
# ══════════════════════════════════════════════════════════
head_ "hooks.json 배선"
HJ="$FLOW/hooks/hooks.json"
if [ ! -f "$HJ" ]; then
  no_ "hooks.json 이 없다 — 훅이 하나도 안 걸린다"
else
  python3 -c 'import json,sys; json.load(open(sys.argv[1],encoding="utf-8"))' "$HJ" \
    && ok_ "hooks.json JSON 파싱" || no_ "hooks.json JSON 파싱 실패"
  # 걸린 스크립트가 실제로 있나 — ${CLAUDE_PLUGIN_ROOT} 를 플러그인 폴더로 바꿔 본다
  miss=$(python3 - "$HJ" "$FLOW" <<'PY'
import json, os, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
root = sys.argv[2]
bad = []
for ev, groups in (d.get('hooks') or {}).items():
    for gidx, gr in enumerate(groups or []):
        for h in gr.get('hooks') or []:
            cmd = (h.get('command') or '').strip('"')
            p = cmd.replace('${CLAUDE_PLUGIN_ROOT}', root).strip('"')
            if not os.path.exists(p):
                bad.append(f"{ev}[{gidx}] → {cmd}")
print('\n'.join(bad))
PY
)
  [ -z "$miss" ] && ok_ "걸린 스크립트가 모두 존재" || no_ "hooks.json 이 없는 스크립트를 가리킨다" "$miss"
  # 세 경로가 다 걸렸나. 하나라도 빠지면 그 경로가 통째로 무방비다
  for want in check-drift-hook guard-danger gate-source-write; do
    grep -q "$want" "$HJ" && ok_ "배선 — $want" || no_ "배선에 $want 가 없다"
  done
  grep -q '"matcher": *"Bash"' "$HJ" && ok_ "matcher Bash" || no_ "matcher Bash 가 없다"
  grep -qE '"matcher": *"[^"]*Write' "$HJ" && ok_ "matcher Write 계열" || no_ "matcher Write 가 없다"
fi

# ══════════════════════════════════════════════════════════
# gate-source-write.sh — 소스 쓰기 게이트
# **과차단을 더 무서워한다.** 면제가 안 먹으면 사람이 훅을 꺼 버리고, 그러면 그 층이 영구히 없어진다.
# 그래서 면제(spike/ · 유닛 없음 · 소스 아님)를 차단 케이스보다 먼저·많이 본다.
# ══════════════════════════════════════════════════════════
head_ "gate-source-write.sh — 뼈대"
GT="$FLOW/hooks/scripts/gate-source-write.sh"
TOPO="$FLOW/flow.topology.json"
bash -n "$GT" && ok_ "문법" || no_ "문법"
[ -f "$TOPO" ] && ok_ "판정 근거 정본 존재" || no_ "flow.topology.json 이 없다"
python3 -c 'import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
g=d.get("gate") or {}
assert g.get("exemptions"), "gate.exemptions 가 없다"
ids={e.get("id") for e in g["exemptions"]}
for need in ("no-units","spike","legacy-exempt"):
    assert need in ids, f"면제 {need} 가 없다"
assert g.get("missingCanon",{}).get("decision"), "missingCanon.decision 이 없다"
# 레거시 면제의 심사 규칙이 topology 에 있나 — 스크립트가 이 값을 읽어 판정한다.
# 비면 스크립트 기본값으로 돌아 **정본이 둘**이 된다. D2 는 이 자리가 비어서 생겼다.
le=[e for e in g["exemptions"] if e.get("id")=="legacy-exempt"][0]
assert le.get("configKey"), "legacy-exempt 에 configKey 가 없다"
assert le.get("whoFills"), "면제를 누가 채우나가 없다 — 그게 D2 였다"
f=le.get("entryForm") or {}
for k in ("required","scopes","decide"):
    assert f.get(k), f"entryForm.{k} 가 없다"
for k in ("recorded","unrecorded","expired","tooBroad"):
    assert f["decide"].get(k), f"decide.{k} 가 없다"
assert f["decide"]["recorded"]=="allow", "기록된 면제는 통과여야 한다"
assert f["decide"]["tooBroad"]=="deny", "너무 넓은 면제는 받지 않는다"
assert f["decide"]["unrecorded"]=="ask", "기록 없는 면제는 ask 다 — allow 면 조용한 fail-open"
assert le.get("tooBroad",{}).get("rule"), "넓이 규칙 이름이 없다"' "$TOPO" \
  && ok_ "gate 절 — 면제 셋 + 정본 부재 판정 + 면제 심사 규칙" || no_ "gate 절이 불완전하다"

# 프로젝트 픽스처를 만든다. <디렉터리> <유닛?> <task?> <FileMap 경로|-> <요구태그?>
mkproj_() {
  local d="$1" unit="$2" task="$3" fmpath="$4" tag="$5"
  mkdir -p "$d"
  printf '{}\n' > "$d/workflow.config.json"
  if [ "$unit" = yes ]; then
    mkdir -p "$d/doc/01.work/user/00.login"
    echo seed > "$d/doc/01.work/user/00.login/.keep"
  fi
  if [ "$task" = yes ]; then
    mkdir -p "$d/doc/01.work/user/00.login/2.task"
    {
      echo '---'
      if [ "$tag" = yes ]; then echo 'requirement: [USER-LOGIN-1]'
      else echo 'requirement: [{{USER-LOGIN-1}}]'; fi
      echo '---'
      echo ''
      echo '## 3. File Map'
      echo ''
      [ "$fmpath" != '-' ] && echo "- \`[New] $fmpath\` — 로그인 API"
    } > "$d/doc/01.work/user/00.login/2.task/00.login.md"
  fi
}

# gt <기대: 차단|확인|통과> <경로> <프로젝트> [설명]
gt() {
  local rc
  bash "$GT" --path "$2" --root "$3" >/dev/null 2>&1; rc=$?
  local got
  case "$rc" in 0) got=통과 ;; 2) got=차단 ;; 3) got=확인 ;; *) got="이상($rc)" ;; esac
  eq_ "$1" "$got" "${4:-$2}"
}

head_ "게이트 면제 — 유닛이 하나도 없으면 검사를 안 켠다"
P0="$TMP/gate-nounit"; mkproj_ "$P0" no no - no
gt 통과 "src/a.ts"   "$P0" "유닛 없음 · 소스"
gt 통과 "src/deep/b.ts" "$P0" "유닛 없음 · 하위 소스"
gt 통과 "spike/x.ts" "$P0" "유닛 없음 · spike"

head_ "게이트 — 유닛은 있고 task 문서가 없다"
P1="$TMP/gate-notask"; mkproj_ "$P1" yes no - no
gt 차단 "src/a.ts"   "$P1" "task 문서 없이 소스를 쓴다"
gt 통과 "spike/x.ts" "$P1" "spike/ 면제"
gt 통과 "spike/deep/y.ts" "$P1" "spike/ 하위 면제"
gt 통과 "README.md"  "$P1" "소스 아님 — .md"
gt 통과 "doc/01.work/user/00.login/2.task/00.a.md" "$P1" "소스 아님 — 문서"
gt 통과 "src/a.test.ts" "$P1" "소스 아님 — 테스트"

head_ "게이트 — task 문서가 그 경로를 담았나 (File Map)"
P2="$TMP/gate-declared"; mkproj_ "$P2" yes yes "src/a.ts" yes
gt 통과 "src/a.ts" "$P2" "File Map 이 담은 경로"
gt 차단 "src/b.ts" "$P2" "File Map 에 없는 경로"
gt 통과 "spike/a.ts" "$P2" "spike 면제는 그대로"

head_ "게이트 — 면제 우회 (반증 C1) · 경로 정규화"
# **면제는 접두어로 판정하므로 `..` 를 먼저 풀어야 한다.** 안 풀면
#   `doc/../src/b.ts`   → 접두어 `doc/` → "소스 아님" 으로 통과
#   `spike/../src/b.ts` → `spike/` 면제로 통과
# 인데 디스크에는 `src/b.ts` 가 써진다. 게이트의 존재 이유가 문자 셋으로 무력화됐다.
gt 차단 "doc/../src/b.ts"           "$P2" "doc/../ 로 면제를 훔친다"
gt 차단 "spike/../src/b.ts"         "$P2" "spike/../ 로 면제를 훔친다"
gt 차단 ".claude/../src/b.ts"       "$P2" ".claude/../ 로 면제를 훔친다"
gt 차단 ".github/../src/b.ts"       "$P2" ".github/../ 로 면제를 훔친다"
gt 차단 "src/../src/b.ts"           "$P2" "빙 돌아온 경로"
gt 차단 "./src/b.ts"                "$P2" "./ 접두어"
gt 차단 "src/./b.ts"                "$P2" "중간의 ./"
gt 차단 "src/x/../b.ts"             "$P2" "중간의 ../"
# 정규화 뒤에도 통과해야 하는 것 — 면제가 진짜 면제인 경우
gt 통과 "spike/./probe.ts"          "$P2" "spike/./ 는 여전히 면제"
gt 통과 "doc/./notes.md"            "$P2" "doc/./ 는 여전히 소스 아님"
gt 통과 "src/../doc/notes.md"       "$P2" "돌아서 문서로 가면 소스 아님"
gt 통과 "src/../src/a.ts"           "$P2" "돌아서 **선언된** 경로로 가면 통과"
# `lstrip('./')` 부작용 (반증 M2) — 앞쪽 `.` 을 전부 먹어 `.claude/x` → `claude/x` 가 됐다.
# 그래서 dotfile 경로가 소스로 오분류돼 **정상 설정 파일 쓰기가 막혔다.**
gt 통과 ".claude/settings.json"     "$P2" ".claude/ 는 소스 아님 (오분류 회귀)"
gt 통과 ".github/workflows/ci.yml"  "$P2" ".github/ 는 소스 아님"
# `.gitignore` 는 **소스로 본다** — drift-hook.sh 의 규칙 ③(doc·spike·.claude·.github 밖이고
# .md 아님)과 같은 판정이다. 두 훅이 갈리면 "커밋은 막히는데 쓰기는 통과" 가 된다.
gt 차단 ".gitignore"                "$P2" "점 파일도 규칙 ③ 을 따른다 (drift 훅과 같은 판정)"
# 상대 경로로 리포를 탈출하면 **통과가 아니라 거부**다
gt 차단 "../../etc/passwd"          "$P2" "리포 밖으로 탈출"
gt 차단 "../sibling/x.ts"           "$P2" "옆 디렉터리로 탈출"
# 절대 경로로 리포 밖은 이 층의 범위가 아니다 (`/tmp` 쓰기를 막으면 정상 작업이 걸린다)
gt 통과 "/tmp/scratch.ts"           "$P2" "리포 밖 절대 경로는 범위 밖"
gt 차단 "$P2/src/b.ts"              "$P2" "리포 안 절대 경로는 판정한다"

head_ "게이트 — 요구 태그가 템플릿 그대로면 태그가 없는 것이다"
P3="$TMP/gate-notag"; mkproj_ "$P3" yes yes "src/a.ts" no
gt 차단 "src/a.ts" "$P3" "requirement 가 {{…}} 다"

head_ "게이트 — File Map 이 없는 task 문서 (거친 바닥)"
P4="$TMP/gate-fallback"; mkproj_ "$P4" yes yes - yes
gt 통과 "src/a.ts" "$P4" "요구 태그가 있으면 거친 판정으로 통과"
P5="$TMP/gate-fallback-notag"; mkproj_ "$P5" yes yes - no
gt 차단 "src/a.ts" "$P5" "요구 태그도 없으면 차단"

# ── 레거시 면제 (D2) ────────────────────────────────────────
# 기계는 처음부터 돌았다. 없던 것은 **채우는 길**이고, 길을 열면 반대쪽 실패가 생긴다 —
# `legacyExempt` 에 `**` 한 줄이면 게이트가 이름만 남는다(사람이 스스로 여는 fail-open).
# 그래서 판정을 셋으로 갈랐다.
#   기록됨(why·scope 있음)  → allow   조용히 통과한다
#   기록 없음 · 만료됨       → **ask**  막지 않되 조용하지도 않다. 막으면 사람이 훅을 끈다
#   너무 넓음(리터럴 조각 0) → deny   면제가 아니라 게이트 끄기다. 받지 않는다
# **걸러진 면제가 문서·설정 쓰기까지 막으면 안 된다** — 아래 not-source 케이스가 그 경계다.
head_ "게이트 — 레거시 면제는 기록된 것만 조용히 통과한다"
P6="$TMP/gate-legacy"; mkproj_ "$P6" yes yes "src/a.ts" yes

setex_() {  # <legacyExempt 의 JSON 값>
  python3 -c 'import json,sys
json.dump({"gate":{"legacyExempt":json.loads(sys.argv[2])}},
          open(sys.argv[1],"w",encoding="utf-8"),ensure_ascii=False)' \
    "$P6/workflow.config.json" "$1"
}
gtn_() {  # <기대 판정> <기대 근거(note)> <경로> <설명>
  local out rc got
  out=$(bash "$GT" --path "$3" --root "$P6" --why 2>&1 >/dev/null); rc=$?
  case "$rc" in 0) got=통과 ;; 2) got=차단 ;; 3) got=확인 ;; *) got="이상($rc)" ;; esac
  eq_ "$1" "$got" "$4"
  if printf '%s' "$out" | grep -q "($2)"; then ok_ "$(printf '  └ %-48s %s' 근거 "$2")"
  else no_ "  └ 근거가 $2 가 아니다" "$out"; fi
}

setex_ '[]'
gtn_ 차단 not-declared "legacy/old.ts" "면제 없음이 기본 — 레거시 파일도 막힌다"

setex_ '["legacy/**"]'
gtn_ 확인 exempt-unrecorded "legacy/old.ts"    "글로브만 적었다 — 막지 않되 매번 묻는다"
gtn_ 확인 exempt-unrecorded "legacy/deep/x.ts" "  하위도 같다"
gtn_ 차단 not-declared      "src/b.ts"         "면제 밖은 그대로 막힌다"
gtn_ 통과 declared-file-map "src/a.ts"         "선언된 경로는 그대로 통과"

setex_ '[{"path":"legacy/**","why":"벤더 배포본","scope":"unmanaged","added":"20260101"}]'
gtn_ 통과 legacy-exempt "legacy/old.ts" "기록된 unmanaged 면제 — 조용히 통과"
gtn_ 차단 not-declared  "src/b.ts"      "  면제 밖은 여전히 막힌다"

setex_ '[{"path":"*/thirdparty/**","why":"벤더","scope":"unmanaged"}]'
gtn_ 통과 legacy-exempt "vendor/thirdparty/x.ts" "중간에 리터럴 조각이 있으면 받는다"

# **글로브도 대상 경로와 같은 규칙으로 정규화한다.** 안 하면 `./legacy/**` 이 아무것에도 안 맞아
# **조용히 죽은 면제**가 된다 — 사람은 걸었다고 믿는데 계속 막히고, 그러면 훅을 꺼 버린다.
setex_ '[{"path":"./legacy/**","why":"벤더","scope":"unmanaged"}]'
gtn_ 통과 legacy-exempt "legacy/old.ts" "./ 접두어 글로브도 산다 (죽은 면제 회귀)"
setex_ '[{"path":"/legacy/**","why":"벤더","scope":"unmanaged"}]'
gtn_ 통과 legacy-exempt "legacy/old.ts" "앞 슬래시 글로브도 산다"
setex_ '[{"path":"legacy/x/../**","why":"벤더","scope":"unmanaged"}]'
gtn_ 통과 legacy-exempt "legacy/old.ts" "글로브 안의 ../ 도 푼다"

setex_ '[{"why":"벤더","scope":"unmanaged"}]'
gtn_ 확인 exempt-unrecorded "legacy/old.ts" "path 없는 항목 — 넓이가 아니라 기록 문제로 본다"

setex_ '[{"path":"legacy/**","why":"역추출 전","scope":"legacy","until":"29991231"}]'
gtn_ 통과 legacy-exempt "legacy/old.ts" "scope=legacy · 만료 전"
setex_ '[{"path":"legacy/**","why":"역추출 전","scope":"legacy"}]'
gtn_ 확인 exempt-unrecorded "legacy/old.ts" "scope=legacy 인데 until 이 없다"
setex_ '[{"path":"legacy/**","why":"역추출 전","scope":"legacy","until":"20000101"}]'
gtn_ 확인 exempt-expired "legacy/old.ts" "만료된 면제 — 차단이 아니라 다시 묻는다"
setex_ '[{"path":"legacy/**","why":"x","scope":"forever"}]'
gtn_ 확인 exempt-unrecorded "legacy/old.ts" "모르는 scope"

# **면제 남용** — 리포 전체·확장자 전체 글로브는 받지 않는다
for wide in '["**"]' '["*"]' '["**/*"]' '["**/*.ts"]' '["./**"]' \
            '[{"path":"**","why":"레거시라서","scope":"unmanaged"}]'; do
  setex_ "$wide"
  gtn_ 차단 exempt-too-broad "legacy/old.ts" "너무 넓은 면제 $wide 를 무시한다"
done
# 넓은 면제가 **소스 아닌 것까지 막으면** 그게 과차단이고 사람이 훅을 끈다
setex_ '["**"]'
gtn_ 통과 not-source        "README.md"  "  걸러진 면제가 문서 쓰기를 막지 않는다"
gtn_ 통과 declared-file-map "src/a.ts"   "  선언된 경로도 막지 않는다"
gtn_ 통과 spike             "spike/x.ts" "  spike 면제도 그대로다"

# 목록이 아니면 지금 면제가 하나도 안 걸린 것이다 — 조용히 지나가지 않는다
setex_ '"legacy/**"'
gtn_ 확인 exempt-not-a-list "legacy/old.ts" "legacyExempt 가 배열이 아니다"
printf '{"gate":{"legacyExempt":[]}}\n' > "$P6/workflow.config.json"

head_ "게이트 — 판정 근거가 없을 때 (fail-open 도 fail-closed 도 아니다)"
gtc() {  # <기대> <설명> <FLOW_TOPOLOGY 값>
  local rc
  FLOW_TOPOLOGY="$3" bash "$GT" --path src/a.ts --root "$P1" >/dev/null 2>&1; rc=$?
  local got; case "$rc" in 0) got=통과 ;; 2) got=차단 ;; 3) got=확인 ;; *) got="이상($rc)" ;; esac
  eq_ "$1" "$got" "$2"
}
gtc 확인 "정본 없음 → 사람에게 넘긴다(ask)"       "$TMP/no-such-topology.json"
printf '{ this is not json' > "$TMP/broken-topo.json"
gtc 확인 "정본이 깨졌음 → ask"                     "$TMP/broken-topo.json"
printf '{"version":1}' > "$TMP/no-gate.json"
gtc 확인 "gate 절이 없음 → ask"                    "$TMP/no-gate.json"
# flow 프로젝트가 아니면 ask 도 아니고 침묵이다 — 남의 프로젝트에서 말을 걸지 않는다
NP="$TMP/not-flow"; mkdir -p "$NP"
gt 통과 "src/a.ts" "$NP" "flow 프로젝트가 아니다 → 조용히 통과"
nfout=$(bash "$GT" --path src/a.ts --root "$NP" 2>&1)
[ -z "$nfout" ] && ok_ "  └ 아무 말도 안 한다" || no_ "  └ 남의 프로젝트에서 말을 걸었다" "$nfout"

head_ "게이트 — 훅 모드 (PreToolUse Write·Edit 의 stdin JSON)"
hgt() {  # <기대> <절대경로> <프로젝트> <설명>
  local rc out
  out=$(hook_json_ tool_input.file_path "$2" | (cd "$3" && CLAUDE_PROJECT_DIR="$3" bash "$GT" 2>&1)); rc=$?
  local got
  if [ "$rc" -eq 2 ]; then got=차단
  elif printf '%s' "$out" | grep -q '"permissionDecision"[[:space:]]*:[[:space:]]*"ask"'; then got=확인
  else got=통과; fi
  eq_ "$1" "$got" "$4"
}
hgt 차단 "$P2/src/b.ts"   "$P2" "Write src/b.ts (절대 경로)"
hgt 통과 "$P2/src/a.ts"   "$P2" "Write src/a.ts (File Map 이 담았다)"
hgt 통과 "$P2/spike/z.ts" "$P2" "Write spike/z.ts"
hgt 차단 "src/b.ts"       "$P2" "상대 경로도 받는다 (프로젝트 루트 기준)"
# 빈 입력·경로 없는 입력에 죽지 않는다 (훅이 죽으면 그 도구가 통째로 막힌다)
echo '{}' | bash "$GT" >/dev/null 2>&1 && ok_ "빈 입력에 통과" || no_ "빈 입력에 죽었다"
echo 'not json' | bash "$GT" >/dev/null 2>&1 && ok_ "깨진 입력에 통과" || no_ "깨진 입력에 죽었다"

# ══════════════════════════════════════════════════════════
# Bash 경유 쓰기 — matcher 가 도구 이름이라 Write·Edit 훅이 아예 안 보는 경로다.
# 추출이 틀리면 게이트가 아무리 맞아도 이 경로가 통째로 새는데 **판정 결과로는 안 보인다.**
# ══════════════════════════════════════════════════════════
head_ "Bash 경유 쓰기 — 대상 추출"
wt() {  # <기대(쉼표로 이은 것)> <명령>
  local got
  got=$(bash "$S" --dump-write-targets "$2" 2>/dev/null | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
  eq_ "$1" "$got" "$(printf '%s' "$2" | tr '\n' ' ')"
}
wt "src/a.ts"           'cat x > src/a.ts'
wt "src/a.ts"           'echo hi >> src/a.ts'
wt "src/a.ts"           'cat x>src/a.ts'
wt "src/a.ts"           'tee src/a.ts'
wt "src/a.ts"           'cat x | tee src/a.ts'
# 표현식(`s/x/y/`)까지 딸려 나오는 것은 **의도다** — 게이트가 소스 아닌 것을 걸러 주므로
# 더 뽑는 것은 무해하고, 덜 뽑는 것은 구멍이다. 그 판단을 케이스로 박아 둔다.
wt "s/x/y/,src/a.ts"    'sed -i "" -e s/x/y/ src/a.ts'
wt "s/x/y/,src/a.ts"    'gsed -i s/x/y/ src/a.ts'
wt "/dev/null"          'echo a > /dev/null'
wt ""                   'npm test 2>&1'
wt ""                   'git status'
wt ""                   'echo "a > b"'
wt ""                   'sed s/x/y/ src/a.ts'
wt "src/a.ts"           'cat <<EOF > src/a.ts
x
EOF'

head_ "Bash 경유 쓰기 — 파일을 만드는 다른 명령 (반증 H2)"
# `WRITE_CMDS` 가 tee·sed -i 넷뿐이라 아래가 **게이트를 아예 안 불렀다.**
# 판정 결과로는 "통과"로 보여서 흔적이 없었다 — 그래서 추출 자체를 케이스로 박는다.
wt "src/a.ts"           'cp a.ts src/a.ts'
wt "src/a.ts"           'mv /tmp/x src/a.ts'
wt "src/a.ts"           'ln -sf /tmp/x src/a.ts'
wt "src/a.ts"           'install -m644 a.ts src/a.ts'
wt "src/a.ts"           'truncate -s0 src/a.ts'
wt "src/a.ts"           'dd of=src/a.ts if=/dev/zero'
wt "src/a.ts"           'rsync a.ts src/a.ts'
wt "src/a.ts"           'rsync -av /tmp/x src/a.ts'
wt "src/a.ts"           'echo x >| src/a.ts'
# `last` 모드 — 원본까지 뽑으면 **읽기만 하는 복사가 막힌다.** 대상만 뽑는다
wt "/tmp/backup.ts"     'cp src/a.ts /tmp/backup.ts'
wt "/tmp/b"             'mv src/a.ts /tmp/b'
wt ""                   'cat src/a.ts'
wt "b,/dev/null"        'cp -r a b && echo done > /dev/null'
# 인용된 경로도 한 낱말이다 — 공백으로 자르면 `src/a` 로 잘려 게이트가 딴 파일을 본다
wt "src/a b.ts"         'cat x > "src/a b.ts"'

head_ "Bash 경유 쓰기 — 게이트에 넘긴다 (guard → gate)"
bw() {  # <기대> <명령> <프로젝트>
  local out rc got
  out=$(hook_json_ tool_input.command "$2" | (cd "$3" && CLAUDE_PROJECT_DIR="$3" bash "$S" 2>&1)); rc=$?
  if [ "$rc" -eq 2 ]; then got=차단
  elif printf '%s' "$out" | grep -q '"permissionDecision"[[:space:]]*:[[:space:]]*"ask"'; then got=확인
  else got=통과; fi
  eq_ "$1" "$got" "$2"
}
bw 통과 'cat x > src/a.ts'          "$P2"
bw 차단 'cat x > src/b.ts'          "$P2"
bw 차단 'echo hi >> src/nope.ts'    "$P2"
bw 차단 'tee src/b.ts'              "$P2"
bw 차단 'sed -i "" s/x/y/ src/b.ts' "$P2"
bw 통과 'echo x > spike/z.ts'       "$P2"
bw 통과 'echo x > README.md'        "$P2"
bw 통과 'npm test 2>&1'             "$P2"
bw 통과 'cat src/b.ts'              "$P2"
# 유닛이 없으면 이 경로도 안 켜진다 — 두 훅이 같은 면제를 쓴다
bw 통과 'cat x > src/b.ts'          "$P0"
# 되돌릴 수 없는 명령 차단은 그대로다 (게이트가 얹혀도 안 가려진다)
bw 차단 'git push'                  "$P2"
# 반증 C1 — Bash 경로에서도 `..` 우회가 막혀야 한다 (Write 경로만 고치면 반쪽이다)
bw 차단 'echo x > doc/../src/b.ts'      "$P2"
bw 차단 'echo x > spike/../src/b.ts'    "$P2"
bw 차단 'cp a.ts doc/../src/b.ts'       "$P2"
bw 통과 'echo x > src/../spike/z.ts'    "$P2"
# 반증 H2 — 파일 만드는 명령도 게이트를 지난다
bw 차단 'cp a.ts src/b.ts'              "$P2"
bw 차단 'mv /tmp/x src/b.ts'            "$P2"
bw 차단 'dd of=src/b.ts if=/dev/zero'   "$P2"
bw 차단 'truncate -s0 src/b.ts'         "$P2"
bw 차단 'ln -sf /tmp/x src/b.ts'        "$P2"
bw 차단 'install -m644 a.ts src/b.ts'   "$P2"
bw 차단 'rsync a.ts src/b.ts'          "$P2"
bw 통과 'rsync src/a.ts /tmp/backup.ts' "$P2"
bw 차단 'echo x >| src/b.ts'            "$P2"
bw 통과 'cp src/a.ts /tmp/backup.ts'    "$P2"
bw 통과 'mv src/a.ts /tmp/b'            "$P2"

# ══════════════════════════════════════════════════════════
# check-guard-canon.sh — 정본이 없을 때 **조용하지 않은가** (반증 M1)
# 가드는 fail-open 을 유지한다(막으면 사람이 훅을 지우고, 그러면 층이 영구히 없어진다).
# 대신 "조용함"을 없앤다 — 세션 시작에 한 번 크게 알린다.
# ══════════════════════════════════════════════════════════
head_ "check-guard-canon.sh — 정본 부재를 세션 시작에 알리나"
CGC="$FLOW/hooks/scripts/check-guard-canon.sh"
if [ ! -f "$CGC" ]; then
  no_ "check-guard-canon.sh 가 없다 — 가드가 조용히 꺼지는 것을 알릴 곳이 없다"
else
  bash -n "$CGC" && ok_ "문법" || no_ "문법"
  grep -q 'check-guard-canon' "$HJ" && ok_ "SessionStart 에 배선" || no_ "hooks.json 에 배선이 없다"
  # 정상 상태 — 아무 말도 하지 않아야 한다 (매 세션 잔소리는 사람이 무시하게 만든다)
  cout=$(bash "$CGC" 2>&1); crc=$?
  eq_ 0 "$crc" "막지 않는다 (exit 0)"
  [ -z "$cout" ] && ok_ "정본이 멀쩡하면 조용하다" || no_ "정상인데 말을 걸었다" "$cout"
  # 정본 없음 — 크게 알려야 한다
  cout=$(FLOW_GUARD_RULES="$TMP/no-rules.json" bash "$CGC" 2>&1); crc=$?
  eq_ 0 "$crc" "정본 없어도 막지 않는다 (exit 0)"
  printf '%s' "$cout" | grep -q '아무것도 막지 않습니다' \
    && ok_ "차단 목록 부재를 알린다" || no_ "차단 목록 부재를 안 알린다" "$cout"
  printf '{ broken' > "$TMP/broken-rules.json"
  cout=$(FLOW_GUARD_RULES="$TMP/broken-rules.json" bash "$CGC" 2>&1)
  printf '%s' "$cout" | grep -q '깨졌습니다' \
    && ok_ "차단 목록 손상을 알린다" || no_ "손상을 안 알린다" "$cout"
  printf '{"rules":[]}' > "$TMP/empty-rules.json"
  cout=$(FLOW_GUARD_RULES="$TMP/empty-rules.json" bash "$CGC" 2>&1)
  printf '%s' "$cout" | grep -q '깨졌습니다' \
    && ok_ "빈 규칙 목록을 손상으로 본다" || no_ "빈 목록을 정상으로 봤다" "$cout"
  cout=$(FLOW_TOPOLOGY="$TMP/no-topo.json" bash "$CGC" 2>&1)
  printf '%s' "$cout" | grep -q '게이트 판정 근거' \
    && ok_ "게이트 정본 부재를 알린다" || no_ "게이트 정본 부재를 안 알린다" "$cout"
  # 가드 본체와 **같은 순서**로 정본을 찾나 — 다르면 "있다"고 알리는데 훅은 못 찾는다
  grep -q 'CLAUDE_PLUGIN_ROOT' "$CGC" && ok_ "훅과 같은 탐색 순서" || no_ "탐색 순서가 다르다"
fi

# ══════════════════════════════════════════════════════════
# SessionStart 훅이 **모델에게** 닿나 (실측 B1)
#
# 위 케이스들은 `2>&1` 로 stdout·stderr 를 합쳐 본다 — 그래서 **어느 쪽으로 나가든 통과했다.**
# 실측에서 그 구멍이 드러났다: 훅은 정확히 발화했는데 같은 세션 모델이 `경고 없음` 이라 답했고,
# 헤드리스 stdout 에도 안 나왔다. `check-guard-canon` 은 가드가 fail-open 인 것을 알리는 훅인데
# 그 알림이 안 닿아, 그 세션이 가드가 열린 줄 모르고 `--no-verify` 를 시도했다.
#
# 모델에 닿는 길은 stdout 의 `hookSpecificOutput.additionalContext` 다(공식 플러그인과 같은 형식).
# **그래서 여기서는 stdout 만 따로 본다.** stderr 는 사람 몫이라 섞어 세지 않는다.
head_ "SessionStart — 경고가 모델에게 닿나 (stdout 만 본다)"

ctx_of_() {   # stdin JSON → additionalContext (없으면 빈 문자열)
  python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); h=d.get("hookSpecificOutput") or {}
    print(h.get("additionalContext","") if h.get("hookEventName")=="SessionStart" else "")
except Exception: print("")'
}

if [ -f "$CGC" ]; then
  so=$(FLOW_GUARD_RULES="$TMP/no-rules.json" bash "$CGC" 2>/dev/null)
  cx=$(printf '%s' "$so" | ctx_of_)
  [ -n "$cx" ] && ok_ "가드 정본 부재 — stdout 이 SessionStart JSON 이다" \
    || no_ "가드 정본 부재 — stdout 에 additionalContext 가 없다 (모델이 못 본다)" "$so"
  printf '%s' "$cx" | grep -q '막지 않습니다' \
    && ok_ "  └ 무엇이 안 막히는지 본문에 있다" || no_ "  └ 본문이 비었다" "$cx"
  so=$(bash "$CGC" 2>/dev/null)
  [ -z "$so" ] && ok_ "정본이 멀쩡하면 stdout 도 비었다" || no_ "정상인데 stdout 에 뭔가 냈다" "$so"
fi

CDH="$FLOW/hooks/scripts/check-drift-hook.sh"
if [ -f "$CDH" ]; then
  dr="$TMP/sess-drift"; mkrepo_ "$dr"; printf '{}\n' > "$dr/workflow.config.json"
  so=$(CLAUDE_PROJECT_DIR="$dr" bash "$CDH" 2>/dev/null)
  cx=$(printf '%s' "$so" | ctx_of_)
  [ -n "$cx" ] && ok_ "drift 훅 미설치 — stdout 이 SessionStart JSON 이다" \
    || no_ "drift 훅 미설치 — stdout 에 additionalContext 가 없다 (모델이 못 본다)" "$so"
  # 설치된 상태에서는 조용해야 한다 — 매 세션 잔소리는 사람이 무시하게 만든다
  mkdir -p "$dr/.githooks"; printf '#!/bin/sh\n# drift\n' > "$dr/.githooks/pre-commit"
  git -C "$dr" config core.hooksPath .githooks
  so=$(CLAUDE_PROJECT_DIR="$dr" bash "$CDH" 2>&1)
  [ -z "$so" ] && ok_ "drift 훅이 걸려 있으면 조용하다" || no_ "걸려 있는데 말을 걸었다" "$so"
fi

summary_ "flow 훅"
