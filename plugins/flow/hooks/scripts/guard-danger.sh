#!/usr/bin/env bash
# 되돌릴 수 없는 명령을 실행 전에 차단한다 (PreToolUse).
#
# 프롬프트 가드레일(CLAUDE.md 가드레일)은 AI가 어기면 아무것도 막지 못한다.
# push·merge·이력 파괴·운영 데이터 변경은 되돌릴 수 없으므로 기계로 막는다.
#
# ── v1 과 달라진 것: 차단 목록이 이 파일에 없다 ──────────────────
# **차단 목록의 정본은 `guard-rules.json` 이다.** 이 스크립트는 그걸 읽어 판정만 한다.
# v1 은 같은 목록이 셸 `case` 문 + 주석 + 산문 5곳에 복제되어 하나 늘리는 비용이
# 9곳이었다. 그래서 아무도 안 늘렸고 실측 미탐이 9건 남았다 (diag-C 4절).
# 목록을 여기 다시 적지 마라 — 적는 순간 v1 의 병이 돌아온다.
#
# 등급은 셋이다 (자세한 뜻은 guard-rules.json 의 `classes`).
#   block  irreversible    되돌릴 수 없다
#   block  defense-off     다른 방어 층을 끈다 (--no-verify · -c core.hooksPath=)
#   block  external-state  저장소 밖에 상태를 만든다 (gh pr/issue/repo create · workflow run)
#   ask    judgement       판단이 갈린다 — 무조건 막으면 사람이 훅을 끈다
#
# **한계는 guard-rules.json 의 `limits` 가 정본이다.** 여기 적지 않는다 —
# v1 은 한계도 주석에 적어 두고 목록에서 빠진 명령은 한계로도 안 적었다.
# 요약: 이건 실수를 막는 장치고, 마음먹은 우회(eval·변수 쪼갬·다른 실행 경로)는 못 막는다.
#       안전 측으로 기울였다 — 세그먼트 안 **어느 자리**의 `git`·`gh` 도 명령으로 본다.
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

deny() {   # <라벨> <조언> <왜>
  echo "" 1>&2
  echo "⛔ flow guard: 차단했습니다 — $1" 1>&2
  echo "   명령: $flat" 1>&2
  echo "" 1>&2
  [ -n "${3:-}" ] && echo "   왜: $3" 1>&2
  echo "   $2" 1>&2
  echo "" 1>&2
  echo "   (차단 목록 정본: plugins/flow/guard-rules.json · 이 훅은 Claude Code 세션에만 걸립니다)" 1>&2
  echo "" 1>&2
  exit 2
}

# ask 등급 — 막지 않고 사람에게 넘긴다. PreToolUse 의 permissionDecision 을 쓴다.
# 무조건 막으면 정상 작업이 걸리고, 그러면 사람이 훅 자체를 꺼 버린다.
ask() {   # <라벨> <조언> <왜>
  local reason
  reason="⚠ flow guard: $1 — $3 $2"
  # 우리 JSON 에서 온 문자열이지만 방어적으로 이스케이프한다. 깨진 JSON 은 훅을 죽인다.
  reason=$(printf '%s' "$reason" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n\t' '  ')
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
}

# ── 차단 목록 정본을 읽는다 ────────────────────────────────────
# 플러그인으로 깔리면 CLAUDE_PLUGIN_ROOT 가 있고, 저장소에서 돌리면 스크립트 위치로 찾는다.
# FLOW_GUARD_RULES 는 테스트가 픽스처를 물릴 때만 쓴다 — 판정을 느슨하게 하지는 않는다.
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd) || here=.
RULES_FILE="${FLOW_GUARD_RULES:-}"
if [ -z "$RULES_FILE" ]; then
  for c in "${CLAUDE_PLUGIN_ROOT:-}/guard-rules.json" "$here/../../guard-rules.json"; do
    [ -f "$c" ] && { RULES_FILE=$c; break; }
  done
fi

# 필드를 \037(unit separator)로 이어 한 줄에 담는다.
# 탭·공백은 IFS 화이트스페이스라 빈 필드가 접힌다 — 정규식 필드가 비면 다음 필드가 밀린다.
RF="id tool words level on caseSensitive when unless notWords label why advice"
rules_load() {   # <파일> [로더] → 규칙 줄들. 정본을 못 읽으면 exit 3.
  local f="$1" want="${2:-}"
  # 로더 지정은 **테스트가 세 구현을 나란히 대조하기 위한 것**이다. 셋이 어긋나면
  # 설치 환경(python3 있냐 node 있냐)에 따라 같은 명령이 막히고 안 막힌다.
  # 없는 로더를 요구하면 **무시하고 자동 선택으로 떨어진다** — 여기서 실패하게 두면
  # 로더 이름을 하나 틀리게 주는 것이 가드를 끄는 길이 된다.
  case "$want" in
    python3|node|perl) command -v "$want" >/dev/null 2>&1 || want= ;;
    *) want= ;;
  esac
  if [ "$want" = python3 ] || { [ -z "$want" ] && command -v python3 >/dev/null 2>&1; }; then
    python3 -c 'import json,sys
F=sys.argv[2].split()
try: d=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: sys.exit(3)
rs=d.get("rules")
if not isinstance(rs,list) or not rs: sys.exit(3)
out=[]
for r in rs:
    if not isinstance(r,dict): sys.exit(3)
    for k in ("id","tool","words","level","why"):
        if not r.get(k): sys.exit(3)
    if r["level"] not in ("block","ask"): sys.exit(3)
    row=[]
    for k in F:
        v=r.get(k,"")
        v="1" if v is True else ("" if v is False or v is None else str(v))
        if "\x1f" in v or "\n" in v: sys.exit(3)
        row.append(v)
    out.append("\x1f".join(row))
sys.stdout.write("\n".join(out))' "$f" "$RF"
  elif [ "$want" = node ] || { [ -z "$want" ] && command -v node >/dev/null 2>&1; }; then
    node -e 'const fs=require("fs");const F=process.argv[2].split(" ");let d;
try{d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"))}catch(e){process.exit(3)}
const rs=d.rules; if(!Array.isArray(rs)||!rs.length)process.exit(3);
const out=[];
for(const r of rs){
  if(!r||typeof r!=="object")process.exit(3);
  for(const k of ["id","tool","words","level","why"])if(!r[k])process.exit(3);
  if(r.level!=="block"&&r.level!=="ask")process.exit(3);
  const row=F.map(k=>{let v=r[k];v=(v===true)?"1":((v===false||v==null)?"":String(v));
    if(v.indexOf("\u001f")>=0||v.indexOf("\n")>=0)process.exit(3); return v});
  out.push(row.join("\u001f"));
}
process.stdout.write(out.join("\n"))' -- "$f" "$RF"
  elif [ "$want" = perl ] || { [ -z "$want" ] && command -v perl >/dev/null 2>&1; }; then
    # 두 가지가 짝이다 — **하나만 하면 조용히 틀린다.**
    #   `binmode(STDOUT,":utf8")` 없으면 한글 규칙에서 "Wide character in print" 경고가
    #     stderr 로 새어 나온다. 훅의 stderr 는 사용자에게 보이니 그것만으로 고장이다.
    #   파일은 **바이트로** 읽어야 한다. `:encoding(UTF-8)` 로 열어 문자로 바꿔 주면
    #     `decode_json` 이 거부해 로더가 통째로 실패한다(= 가드가 안 돈다).
    perl -MJSON::PP -e 'binmode(STDOUT,":utf8"); my @F=split / /,$ARGV[1];
open(my $fh,"<",$ARGV[0]) or exit 3; local $/; my $t=<$fh>;
my $d=eval{decode_json($t)}; exit 3 unless ref($d) eq "HASH";
my $rs=$d->{rules}; exit 3 unless ref($rs) eq "ARRAY" && @$rs;
my @out;
for my $r (@$rs){ exit 3 unless ref($r) eq "HASH";
  for my $k (qw(id tool words level why)){ exit 3 unless defined $r->{$k} && $r->{$k} ne "" }
  exit 3 unless $r->{level} eq "block" || $r->{level} eq "ask";
  my @row = map { my $v=$r->{$_};
    $v = (ref($v) eq "JSON::PP::Boolean") ? ($v ? "1" : "") : (defined $v ? "$v" : "");
    exit 3 if $v =~ /[\x1f\n]/; $v } @F;
  push @out, join("\x1f",@row) }
print join("\n",@out)' "$f" "$RF"
  else
    exit 3
  fi
}

# 테스트용 덤프 — `guard-danger.sh --dump-rules <로더> [파일]`.
# **환경변수가 아니라 argv 로 받는다.** Claude Code 는 이 훅을 인자 없이 부르고
# AI 는 훅의 argv 를 정할 수 없다 — 환경변수로 두면 그게 곧 가드를 끄는 스위치가 된다.
# 이 문(門)이 있는 이유: 로더가 셋인데 실행되는 것은 하나라, 나머지 둘은
# 테스트가 직접 부르지 않으면 조용히 썩는다. 실제로 node 로더는 argv 색인이,
# perl 로더는 인코딩이 틀린 채 통과 숫자에 아무 흔적도 남기지 않았다.
if [ "${1:-}" = --dump-rules ]; then
  rules_load "${3:-$RULES_FILE}" "${2:-}"
  exit $?
fi

# stdin 은 덤프 문을 지난 뒤에 읽는다 — 덤프는 훅 입력 없이 부른다.
input=$(cat)
cmd=$(json_get "$input" tool_input.command)
[ -n "$cmd" ] || exit 0

flat=$(printf '%s' "$cmd" | tr '\n' ' ' | tr -s ' ')

RULES=()
rl_out=
if [ -n "$RULES_FILE" ] && [ -f "$RULES_FILE" ]; then
  rl_out=$(rules_load "$RULES_FILE") || rl_out=
fi
if [ -z "$rl_out" ]; then
  # **조용히 통과하지 않는다.** 정본이 없으면 가드는 아무것도 막지 못하는데,
  # 아무 말도 없으면 그 상태가 "안전하다"로 읽힌다 — v1 이 정확히 그렇게 낡았다.
  # 그렇다고 막으면(exit 2) 모든 Bash 가 멈춰 사람이 훅을 지운다. 그래서 시끄럽게 통과한다.
  echo "⚠ flow guard: 차단 목록 정본을 못 읽었습니다 — 아무것도 막지 않는 상태입니다." 1>&2
  echo "   찾은 곳: ${RULES_FILE:-(없음)}  (plugins/flow/guard-rules.json 이 있어야 합니다)" 1>&2
  exit 0
fi
while IFS= read -r ln; do
  [ -n "$ln" ] && RULES+=("$ln")
done <<EOF
$rl_out
EOF

# ── 여기부터 아래는 v1 에서 **그대로** 이식한 인용 인식 스캐너다 ──────
# 재작성하지 마라. 이 파서에는 실제로 난 사고의 회귀 방어가 박혀 있고(주석 참조)
# 그 회귀가 hooks.test.sh 의 케이스로 남아 있다.
#
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

# `--` 가 반드시 있어야 한다. 규칙의 정규식이 `-` 로 시작하면 grep 이 그걸 **옵션으로 읽고**
# usage 를 뱉으며 실패한다 — 즉 그 규칙이 조용히 아무것도 막지 않는다. 실제로 그랬다
# (`-c[[:space:]=]*core\.hooksPath` → grep: invalid option). 정본이 데이터라서
# 정규식을 사람이 쓰는 만큼, 첫 글자가 무엇이든 견뎌야 한다.
segh()  { printf '%s' "$1" | grep -qiE -- "$2"; }   # 그 세그먼트 안에서만 찾는다
# 대소문자를 구별해야 하는 규칙이 있다 — `git branch -D`(미머지 커밋 삭제) 와
# `-d`(머지된 것만) 는 **같은 플래그의 대소문자 차이**다. `-i` 로 보면 안전한 쪽까지 막힌다.
seghc() { printf '%s' "$1" | grep -qE  -- "$2"; }

# 규칙의 `words` 가 그 세그먼트의 낱말 목록의 **앞머리**인가. `*` 는 서브커맨드를 안 본다.
w_match() {   # <규칙 words> <세그먼트 words>
  [ "$1" = "*" ] && return 0
  case "$2" in "$1") return 0 ;; "$1 "*) return 0 ;; esac
  return 1
}

# ask 는 **명령 전체를 다 본 뒤** 낸다. `git commit --amend && git push` 는
# ask 가 아니라 차단이어야 하는데, 먼저 만난 ask 로 나가면 push 를 못 본다.
ASK_LABEL= ; ASK_ADVICE= ; ASK_WHY=

i=0
while [ "$i" -lt "${#SB[@]}" ]; do
  if seg_cmd "${SB[$i]}"; then
    args=${SU[$i]} ; rest=$REST ; w=$(words "$REST")
    j=0
    while [ "$j" -lt "${#RULES[@]}" ]; do
      IFS=$'\037' read -r rid rtool rwords rlevel ron rcs rwhen runless rnot rlabel rwhy radvice <<<"${RULES[$j]}"
      j=$((j+1))
      [ "$rtool" = "$LEAD" ] || continue
      w_match "$rwords" "$w" || continue
      if [ -n "$rnot" ] && w_match "$rnot" "$w"; then continue; fi
      case "$ron" in rest) hay=$rest ;; *) hay=$args ;; esac
      if [ -n "$rcs" ]; then
        [ -n "$runless" ] && seghc "$hay" "$runless" && continue
        [ -n "$rwhen" ] && { seghc "$hay" "$rwhen" || continue; }
      else
        [ -n "$runless" ] && segh "$hay" "$runless" && continue
        [ -n "$rwhen" ] && { segh "$hay" "$rwhen" || continue; }
      fi
      [ -n "$rlabel" ] || rlabel="$LEAD ${w%% *}"
      if [ "$rlevel" = block ]; then deny "$rlabel" "$radvice" "$rwhy"; fi
      if [ -z "$ASK_LABEL" ]; then ASK_LABEL=$rlabel; ASK_ADVICE=$radvice; ASK_WHY=$rwhy; fi
    done
  fi
  i=$((i+1))
done

[ -n "$ASK_LABEL" ] && ask "$ASK_LABEL" "$ASK_ADVICE" "$ASK_WHY"

exit 0
