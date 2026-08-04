#!/usr/bin/env bash
# 되돌릴 수 없는 명령을 실행 전에 차단한다 (PreToolUse).
#
# 프롬프트 가드레일(CLAUDE.md 가드레일)은 AI가 어기면 아무것도 막지 못한다.
# push·merge·이력 파괴·운영 데이터 변경은 되돌릴 수 없으므로 기계로 막는다.
#
# 차단 — **이 목록이 정본이다.** CLAUDE.md 가드레일이 여기를 가리킨다.
#   원격·이력
#     git   push(force 포함) · merge · rebase · pull --rebase · subtree push
#           filter-branch · filter-repo
#   작업 손실
#     git   reset --hard · clean -f · checkout -- <경로> · checkout -f · switch -f
#           restore(--staged 없이) · stash clear · stash drop · reflog expire · update-ref -d
#   GitHub
#     gh    pr merge · release create · release delete · repo delete · secret set · variable set
#           api 의 쓰기 메서드(-X · --method) · 필드 플래그(-f · -F · --field · --raw-field · --input)
#           · graphql 의 mutation      ← 필드만 줘도 gh 가 POST 로 보낸다
#   경로가 붙어도 잡는다 — /usr/bin/git push · ./node_modules/.bin/gh
# 허용
#   git   commit(우리 /flow:commit 이 쓴다) · add · status · diff · log · branch · checkout -b
#         push --dry-run · restore --staged · stash list · reset(--hard 없이) · clean -n
#         merge/rebase 의 --abort · --quit · --skip   ← 빠져나오는 것이다
#         **--continue 는 막는다** — 머지를 완료하고 이력을 다시 쓴다
#   gh    pr list · view · auth status 등 읽기 · api 에 -X GET 을 못 박은 것
#         graphql 의 읽기 쿼리(mutation 이 없으면 통과)
# **한계 — 이건 실수를 막는 장치고, 마음먹은 우회는 못 막는다.**
#   못 막음: eval "git pu""sh" · P=push; git $P · 스크립트 파일에 써서 실행
#            python subprocess · MCP 도구 (matcher 가 Bash 라서 훅이 아예 안 돈다)
#   안전 측으로 기울였다: 세그먼트 안 **어느 자리**의 `git`·`gh` 도 명령으로 본다.
#            here-doc 구분자를 못 닫으면 본문을 명령으로 스캔한다(과차단).
#            `echo git push`(인용 없이)처럼 실행이 아닌 것도 막힌다 — 인용하면 통과한다.
#   막으려면 셸을 해석해야 하는데 훅이 할 일이 아니다.
#   그래서 "기계가 막으니 안심"이 아니라 "무심코 치는 것을 막는다"로 읽어야 한다.
#
# 우회 수단을 두지 않는다 — 환경변수로 열면 AI가 그걸 설정해 통과한다.
# 사람이 해야 하는 일이면 사람이 자기 터미널에서 한다(훅은 Claude Code 세션에만 걸린다).
set -uo pipefail

# --- 훅 입력 JSON에서 값 꺼내기 (node → python3 → perl) ---
json_get() {
  local data="$1" path="$2"
  if command -v node >/dev/null 2>&1; then
    printf '%s' "$data" | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{try{let o=JSON.parse(s);for(const k of process.argv[1].split("."))o=(o==null?null:o[k]);process.stdout.write(o==null?"":String(o))}catch(e){}})' "$path"
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$data" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 for k in sys.argv[1].split("."): d=d.get(k) if isinstance(d,dict) else None
 sys.stdout.write("" if d is None else str(d))
except Exception: pass' "$path"
  elif command -v perl >/dev/null 2>&1; then
    printf '%s' "$data" | perl -MJSON::PP -0777 -ne 'BEGIN{binmode(STDOUT,":utf8");@k=split/\./,$ARGV[0];shift @ARGV} my $d=eval{decode_json($_)}; for my $key (@k){$d = ref($d) eq "HASH" ? $d->{$key} : undef} print defined($d)?$d:"";' "$path"
  fi
}

# 파서가 없으면 통과시킨다 — 여기서 막으면 정상 작업이 전부 멈춘다.
if ! command -v node >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1 && ! command -v perl >/dev/null 2>&1; then
  exit 0
fi

input=$(cat)
cmd=$(json_get "$input" tool_input.command)
[ -n "$cmd" ] || exit 0

flat=$(printf '%s' "$cmd" | tr '\n' ' ' | tr -s ' ')

deny() {
  echo "" 1>&2
  echo "⛔ flow guard: 되돌릴 수 없는 명령이라 차단했습니다 — $1" 1>&2
  echo "   명령: $flat" 1>&2
  echo "" 1>&2
  echo "   $2" 1>&2
  echo "   (CLAUDE.md 가드레일 · 이 훅은 Claude Code 세션에만 걸립니다)" 1>&2
  echo "" 1>&2
  exit 2
}

# --- 인용을 아는 스캐너로 세그먼트를 쪼갠다 ---
# `sed` 로 인용을 지우면 `"it\'s a fix"` 의 `\'` 가 여는 인용이 되어 뒤쪽 인용과 짝이 맞고,
# 그 사이의 진짜 명령이 통째로 사라진다. 그래서 왼쪽부터 상태를 들고 훑는다.
#   SB — 인용 안 내용을 공백으로 바꾼 세그먼트. **명령을 찾는다.**
#   SU — 인용 기호만 뗀 세그먼트. **플래그 값을 본다** (`-X \'POST\'`).
# 플래그를 명령 전체에서 찾으면 다른 세그먼트의 `-f` 가 얹혀 과차단이 난다 — 세그먼트별로 본다.
SB=() ; SU=() ; b= ; u=
# `${b//[[:space:]]/}` 는 bash 3.2(macOS 기본)에서 2차식이다 — 긴 명령에서 수 초 걸렸다
push_seg() { case "$b" in *[![:space:]]*) SB+=("$b"); SU+=("$u") ;; esac; b= ; u= ; }

scan() {
  local s=$1 i c n q=
  b= ; u=
  for (( i=0; i<${#s}; i++ )); do
    c=${s:i:1}
    if [ -n "$q" ]; then
      # `"..."` 안의 `\"` 는 **내용**이다. 닫는 인용으로 읽으면 그 뒤 전부가
      # "인용 안"으로 분류돼 진짜 명령이 사라진다 — 커밋 메시지에 흔한 형태다.
      if [ "$q" = '"' ] && [ "$c" = '\' ]; then
        case ${s:i+1:1} in
          '"'|'\'|'$'|'`') u+=${s:i+1:1}; b+=' '; i=$((i+1)); continue ;;
        esac
      fi
      if [ "$c" = "$q" ]; then q= ; else b+=' ' ; u+=$c ; fi
      continue
    fi
    case "$c" in
      "'"|'"') q=$c ;;
      '\') n=${s:i+1:1}; i=$((i+1))
           [ "$n" = $'\n' ] || { b+="$n"; u+="$n"; } ;;   # 줄이음(`\`+개행)은 접는다
      ';'|'&'|'|'|'('|')'|'{'|'}'|'`'|'<'|'>'|$'\n') push_seg ;;
      *) b+=$c ; u+=$c ;;
    esac
  done
  push_seg
}
# here-doc 본문은 **데이터**다. 개행이 구분자라 본문 각 줄이 세그먼트가 되어,
# 문서에 `git push` 를 적는 것까지 막혔다 — 인용으로 피할 방법도 없다. 먼저 떼어낸다.
#
# **잘못 떼면 가드가 통째로 꺼진다.** 실제로 그랬다 —
#   `cat <<EOF; echo hi` 는 구분자를 `EOF;` 로 읽어 영구히 본문 모드였고,
#   `echo "1 << two"`·`grep "<<<<<<< HEAD"` 는 here-doc 으로 오인됐다. 뒤 명령이 다 사라졌다.
# 그래서 **구분자를 못 닫으면 실패**시키고, 호출부가 원문을 스캔한다(최악이 과차단이다).
strip_heredoc() {
  printf '%s' "$1" | awk '
    { if (!skip) {
        if (match($0, /<<-?[[:space:]]*[\047\042]?[A-Za-z_][A-Za-z0-9_.-]*/)) {
          tok = substr($0, RSTART, RLENGTH); dash = (substr(tok, 3, 1) == "-")
          d = tok; sub(/^<<-?[[:space:]]*/, "", d); gsub(/[\047\042]/, "", d)
          delim = d; skip = 1; print; next }
        print; next }
      l = $0; if (dash) sub(/^\t+/, "", l)      # bash 는 `<<-` 에서 **탭만** 뗀다
      if (l == delim) skip = 0                  # 정규식이 아니라 문자열 비교
      next }
    END { if (skip) exit 1 }'
}
stripped=$(strip_heredoc "$cmd") || stripped=$cmd
scan "$stripped"

LEAD= ; REST=
seg_cmd() {   # $1 = 세그먼트 → 어느 자리든 basename 이 git·gh 인 토큰을 찾는다
  local s=$1 tok base
  while [ -n "$s" ]; do
    s=${s#"${s%%[![:space:]]*}"}; [ -n "$s" ] || break
    tok=${s%%[[:space:]]*}; s=${s#"$tok"}
    tok=${tok#\$}          # `$'...'` 의 앞 `$`
    # 대소문자 무시 볼륨(macOS)에서는 `GIT push` 가 실제로 돈다
    base=$(printf '%s' "${tok##*/}" | tr 'A-Z' 'a-z')
    case "$base" in git|gh) LEAD=$base; REST=$s; return 0 ;; esac
  done
  return 1
}

# `sh -c "…"` 는 명령이 인용 안이라 SB 에서 사라진다. 그 payload 를 한 겹 더 훑는다.
#   셸 토큰도 **어느 자리든** 찾는다 — 첫 낱말만 보면 `timeout 30 bash -c "git push"` 가 빠진다.
shell_payload() {   # $1 = 세그먼트 → 셸 뒤 `-…c…` 플래그 다음부터
  local s=$1 tok seen=
  while [ -n "$s" ]; do
    s=${s#"${s%%[![:space:]]*}"}; [ -n "$s" ] || break
    tok=${s%%[[:space:]]*}; s=${s#"$tok"}
    if [ -n "$seen" ]; then
      case "$tok" in -*c*) printf '%s' "${s#"${s%%[![:space:]]*}"}"; return 0 ;; esac
    else
      case "$(printf '%s' "${tok##*/}" | tr 'A-Z' 'a-z')" in sh|bash|zsh|dash|ksh) seen=1 ;; esac
    fi
  done
  return 1
}

i=0
while [ "$i" -lt "${#SB[@]}" ]; do
  pl=$(shell_payload "${SU[$i]}") && [ -n "$pl" ] && [ "$pl" != "${SU[$i]}" ] && scan "$pl"
  i=$((i+1))
done

words() {   # 옵션(과 값을 먹는 것의 값)을 빼고 낱말만
  local s=$1 tok out=
  while [ -n "$s" ]; do
    s=${s#"${s%%[![:space:]]*}"}; [ -n "$s" ] || break
    tok=${s%%[[:space:]]*}; s=${s#"$tok"}
    case "$tok" in
      -c|-C|--git-dir|--work-tree|--namespace|--exec-path|-u|-g|-n|-R|--repo)
        s=${s#"${s%%[![:space:]]*}"}; s=${s#"${s%%[[:space:]]*}"} ;;
      -*) ;;
      *) out="$out $tok" ;;
    esac
  done
  printf '%s' "${out# }"
}

segh() { printf '%s' "$1" | grep -qiE "$2"; }   # 그 세그먼트 안에서만 찾는다

i=0
while [ "$i" -lt "${#SB[@]}" ]; do
  if seg_cmd "${SB[$i]}"; then
    args=${SU[$i]} ; w=$(words "$REST")
    if [ "$LEAD" = git ]; then
      case "${w%% *}" in
        push)   # `-n` 은 안 본다 — `nice -n 10 git push` 의 `-n` 이 얹힌다
                segh "$args" '(^|[[:space:]])\-\-dry-run([[:space:]]|$)' && { i=$((i+1)); continue; }
                deny "git push"          "push·merge는 사람이 외부 툴로 합니다(Sourcetree 등). 커밋까지는 /flow:commit 이 합니다." ;;
        # `--abort`·`--quit`·`--skip` 은 **빠져나오는** 것이라 통과시킨다.
        #   `--continue` 는 아니다 — 머지를 완료하고 이력을 다시 쓴다.
        #   세그먼트 전체에서 찾으면 `git -c note=--abort push` 로 가드가 꺼진다 → **낱말 경계**로 본다.
        merge)  segh "$args" '(^|[[:space:]])\-\-(abort|quit)([[:space:]]|$)' && { i=$((i+1)); continue; }
                deny "git merge"         "머지는 사람이 합니다 — 충돌 판단과 이력 결정이 사람 몫입니다." ;;
        rebase) segh "$args" '(^|[[:space:]])\-\-(abort|quit|skip|show-current-patch)([[:space:]]|$)' \
                  && { i=$((i+1)); continue; }
                deny "git rebase"        "이력을 바꿉니다. 사람이 직접 하세요." ;;
        filter-branch) deny "git filter-branch" "이력을 파괴합니다. 사람이 직접 하세요." ;;
        filter-repo)   deny "git filter-repo"   "이력을 파괴합니다. 사람이 직접 하세요." ;;
        reset)  segh "$args" '(^|[[:space:]])\-\-hard([[:space:]]|=|$)' \
                  && deny "git reset --hard" "커밋되지 않은 변경이 사라집니다. 되돌릴 수 없습니다." ;;
        clean)  segh "$args" '(^|[[:space:]])(\-\-force|-[a-zA-Z]*f[a-zA-Z]*)([[:space:]]|$)' \
                  && deny "git clean -f" "추적되지 않는 파일이 사라집니다. 되돌릴 수 없습니다." ;;
        # `pull --rebase` 는 rebase 와 같은 일을 한다
        pull)   segh "$args" '(^|[[:space:]])(\-\-rebase|-r)([[:space:]]|$)' \
                  && deny "git pull --rebase" "이력을 바꿉니다. 사람이 직접 하세요." ;;
        # `checkout -- .`·`restore .` 는 `reset --hard` 와 같은 손실이다
        checkout|switch)
                segh "$args" '(^|[[:space:]])(--|\-\-force|-f)([[:space:]]|$)' \
                  && deny "git ${w%% *} (변경 버림)" "커밋되지 않은 변경이 사라집니다. 되돌릴 수 없습니다." ;;
        restore)
                segh "$args" '(^|[[:space:]])\-\-staged([[:space:]]|$)' || \
                  deny "git restore" "커밋되지 않은 변경이 사라집니다. 되돌릴 수 없습니다." ;;
        # 안전망을 없애는 것
        reflog) segh "$args" '(^|[[:space:]])expire([[:space:]]|$)' \
                  && deny "git reflog expire" "되돌릴 안전망이 사라집니다." ;;
        stash)  segh "$args" '(^|[[:space:]])(clear|drop)([[:space:]]|$)' \
                  && deny "git stash clear/drop" "스태시가 사라집니다. 되돌릴 수 없습니다." ;;
        update-ref)
                segh "$args" '(^|[[:space:]])-d([[:space:]]|$)' \
                  && deny "git update-ref -d" "참조가 사라집니다." ;;
      esac
      case "$w" in "subtree push"*) deny "git subtree push" "원격을 바꿉니다. 사람이 외부 툴로 합니다." ;; esac
    else
      case "$w" in
        "pr merge"*)       deny "gh pr merge"      "머지는 사람이 합니다 — 충돌 판단과 이력 결정이 사람 몫입니다." ;;
        "release create"*) deny "gh release create" "릴리스는 사람이 냅니다. 태그가 원격에 남습니다." ;;
        "repo delete"*)    deny "gh repo delete"   "저장소가 사라집니다." ;;
        "release delete"*) deny "gh release delete" "릴리스·태그가 사라집니다." ;;
        "secret set"*|"variable set"*) deny "gh secret set" "GitHub 상태를 바꿉니다. 사람이 직접 하세요." ;;
        api*)
          segh "$args" '(\-X|\-\-method)[[:space:]=]*(POST|PUT|DELETE|PATCH)' \
            && deny "gh api 쓰기" "GitHub 상태를 바꿉니다. 사람이 직접 하세요."
          # 검색·페이지네이션은 `-f` 가 유일한 방법이고 GraphQL 읽기도 POST 다.
          # `-X GET` 을 못 박았거나 `mutation` 이 없으면 읽기로 본다.
          if ! segh "$args" '(\-X|\-\-method)[[:space:]=]*GET'; then
            case "$w" in
              "api graphql"*) segh "$args" 'mutation' \
                && deny "gh api graphql mutation" "GitHub 상태를 바꿉니다. 사람이 직접 하세요." ;;
              *) segh "$args" '(^|[[:space:]])(-f|-F|\-\-field|\-\-raw-field|\-\-input)([[:space:]=]|$)' \
                   && deny "gh api 쓰기(필드 플래그)" "필드를 주면 gh 가 POST 로 보냅니다. 사람이 직접 하세요." ;;
            esac
          fi ;;
      esac
    fi
  fi
  i=$((i+1))
done

exit 0
