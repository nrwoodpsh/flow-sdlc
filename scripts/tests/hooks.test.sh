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

summary_ "flow 훅"
