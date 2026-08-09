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
#
# ── 셸에 남은 규칙 (JSON 으로 못 내리는 것) ───────────────────────
# 아래 블록은 **기계가 읽는 고정 형식**이다. `scripts/gen_docs.py` 가 긁어 문서 차단표의
# `셸 정본` 절을 만들고, `scripts/lint.py` 의 `shell-guard-header` 검사가
# 이 머리말과 셸 본문의 `@rule` 표시를 대조한다. **한쪽만 고치면 CI 가 실패한다.**
# 갈라진 정본 중 셸 쪽이 낡는 것이 diag-C 4절이 말한 그 병이라, 그 병만 기계로 막는다.
#
# 형식 — 줄 하나에 필드를 ` | ` 로 잇는다. 필드 수가 다르면 lint 가 실패한다.
#   `# rule: <id> | <등급> | <무엇을 막나> | <왜 JSON 이 아니라 셸에 있나>`
#
# **`limit:` 줄을 여기 넣지 마라. 한계의 정본은 `guard-rules.json` 의 `limits` 다.**
# 한때 여기에도 8줄이 있었고, 겹친 6개가 생성 표에 두 번 실렸으며 그중 하나(`rsync`)는
# 낡은 채 남았다 — rsync 를 잡게 고쳤는데 문서는 통과한다고 적고 있었다.
# `rule` 은 구현이 이 파일에 있어 본문의 `@rule` 표시와 대조되지만, `limit` 은 대조할 짝이 없다.
# 근접성만 얻고 보장은 못 얻으면서 정본이 둘이 된다. `lint.py` 의 `limits-single-canon` 이 막는다.
#
# @flow-shell-rules v1
# rule: bash-write-redirect | block | 리다이렉션으로 소스 파일에 쓰는 것 — `>` · `>>` · noclobber 무시 형태 | 리다이렉션 대상은 토크나이저가 세그먼트 경계로 써서 버린다 — 명령 이름 목록으로 표현할 수 없다
# rule: bash-write-command | block | 파일을 만드는 명령으로 소스를 쓰는 것 — tee · sed -i · gsed -i · perl -i · cp · mv · ln · install · truncate · rsync · dd(of=) | 어느 인자가 파일인지가 명령마다 달라(전부/마지막/of=) 인자 해석이 필요하다
# rule: word-split-quotes | block | 낱말 안에 인용을 끼워 명령을 쪼개는 것 — `git p"u"sh` · `gh "pr" merge` | 셸의 단어 분리 규칙(인용은 단어 경계가 아니다)을 구현해야 판정된다. 목록으로 표현할 수 없다
# @flow-shell-rules-end
#
# 위 둘은 **스스로 판정하지 않는다.** 쓰기 대상 경로를 뽑아 `gate-source-write.sh` 에 물어본다 —
# 게이트 조건이 두 곳에 생기면 Write·Edit 경로와 Bash 경로의 판정이 어긋난다.
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
# `--dump-write-targets <명령>` 도 같은 이유로 argv 다. 쓰기 대상 추출만 떼어 보여 준다 —
# 추출이 틀리면 게이트가 아무리 맞아도 Bash 경로가 통째로 새는데, 판정 결과로는 안 보인다.
DUMP_WT=
if [ "${1:-}" = --dump-write-targets ]; then
  DUMP_WT=1
  cmd="${2:-}"
else
  input=$(cat)
  cmd=$(json_get "$input" tool_input.command)
fi
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
#   SW — **낱말 목록**. 셸의 단어 분리를 그대로 흉내낸다. 명령·서브커맨드를 여기서 찾는다.
#
# ── SW 를 왜 더했나 (반증이 뚫은 구멍) ────────────────────────────
# 원래는 낱말도 SB 에서 뽑았다. SB 는 인용 **내용을 공백으로** 바꾸므로
#   `git p"u"sh`  →  SB `git p sh`  →  낱말 `p`·`sh`  →  push 규칙이 안 맞는다
# 인데 셸은 그대로 `git push` 를 실행한다. 한 글자 인용으로 `reset --hard` 까지 뚫렸다.
#
# **셸의 실제 규칙은 인용이 단어 경계가 아니라는 것이다.**
#   `git p"u"sh`            → 한 낱말 `push`      (명령이다)
#   `git commit -m "git push"` → 낱말 `git push`  (한 낱말이니 명령 이름이 아니다 — 데이터다)
# 그래서 **단어를 먼저 나누고 각 낱말 안에서 인용을 벗긴다.** 두 경우가 이것으로 갈린다.
# 인용을 공백으로 바꾼 뒤 단어를 나누면 갈릴 수가 없다 — 그게 구멍의 원인이었다.
#
# SB·SU·세그먼트 분리·strip_heredoc·shell_payload 는 **그대로 둔다**(케이스가 거기 박혀 있다).
SB=() ; SU=() ; SW=() ; SP_=() ; b= ; u= ; pre= ; cw= ; hasw= ; segw= ; W=
# `${b//[[:space:]]/}` 는 bash 3.2(macOS 기본)에서 2차식이다 — 긴 명령에서 수 초 걸렸다
#
# `SP_[i]` 는 **그 세그먼트 앞에 무엇이 있었나**다. `>` 면 이 세그먼트가 리다이렉션 대상이다.
# 토크나이저는 `>` 를 세그먼트 경계로 쓰고 버리므로, 버리기 전에 표시만 남긴다 —
# 세그먼트를 나누는 방식은 v1 그대로다(케이스가 그것에 박혀 있다).
USEP=$'\037'

# 낱말 목록(USEP 로 이은 것)을 하나씩 꺼내는 틀. **낱말 안에 공백이 있을 수 있다**
# (`-m "두 낱말"` 은 한 낱말이다) — 공백으로 자르면 안 되므로 USEP 로만 자른다.
next_word() {   # <남은 목록> → NW=낱말 · NREST=나머지.  더 없으면 1
  local rest=$1
  while [ -n "$rest" ]; do
    rest=${rest#"$USEP"}
    NW=${rest%%"$USEP"*}
    case "$rest" in *"$USEP"*) NREST=${rest#"$NW"} ;; *) NREST= ;; esac
    [ -n "$NW" ] && return 0
    rest=$NREST
  done
  NW= ; NREST= ; return 1
}

# 낱말 하나를 닫는다. `hasw` 가 따로 있는 이유: `""` 는 **빈 낱말**이라 내용이 없어도
# 낱말 하나가 생긴다. 그래야 `git pu""sh` 가 `pu`+`sh` 로 갈리지 않고 한 낱말 `push` 가 된다.
flush_word() {
  if [ -n "$hasw" ]; then
    W="$W$USEP$cw"
    [ -n "$cw" ] && segw=1
  fi
  cw= ; hasw=
}
# 세그먼트를 닫는다. SB 가 공백뿐이어도 **낱말이 있으면** 담는다 —
# `"git" "push"` 처럼 전부 인용된 세그먼트가 통째로 사라지던 것을 막는다.
push_seg() {
  flush_word
  local keep=$segw
  case "$b" in *[![:space:]]*) keep=1 ;; esac
  if [ -n "$keep" ]; then SB+=("$b"); SU+=("$u"); SW+=("$W"); SP_+=("$pre"); fi
  b= ; u= ; W= ; pre= ; segw=
}

# @rule word-split-quotes
scan() {
  local s=$1 i c n q=
  b= ; u= ; pre= ; W= ; cw= ; hasw= ; segw=
  for (( i=0; i<${#s}; i++ )); do
    c=${s:i:1}
    if [ -n "$q" ]; then
      # `"..."` 안의 `\"` 는 **내용**이다. 닫는 인용으로 읽으면 그 뒤 전부가
      # "인용 안"으로 분류돼 진짜 명령이 사라진다 — 커밋 메시지에 흔한 형태다.
      if [ "$q" = '"' ] && [ "$c" = '\' ]; then
        case ${s:i+1:1} in
          '"'|'\'|'$'|'`') u+=${s:i+1:1}; b+=' '; cw+=${s:i+1:1}; hasw=1
                           i=$((i+1)); continue ;;
        esac
      fi
      # 인용 안의 공백은 **낱말을 나누지 않는다** — 그게 인용의 뜻이다.
      if [ "$c" = "$q" ]; then q= ; else b+=' ' ; u+=$c ; cw+=$c ; hasw=1 ; fi
      continue
    fi
    case "$c" in
      # 인용 기호 자체는 값이 아니지만 **낱말은 시작시킨다**(`""` 가 빈 낱말인 이유)
      "'"|'"') q=$c ; hasw=1 ;;
      '\') n=${s:i+1:1}; i=$((i+1))
           [ "$n" = $'\n' ] || { b+="$n"; u+="$n"; cw+="$n"; hasw=1; } ;;   # 줄이음은 접는다
      # 인용 밖의 공백만 낱말 경계다. SB·SU 에는 v1 처럼 그대로 넣는다
      ' '|$'\t') flush_word ; b+=$c ; u+=$c ;;
      ';'|'&'|'|'|'('|')'|'{'|'}'|'`'|'<'|$'\n') push_seg ;;
      # `>` 도 v1 과 똑같이 경계다. 다른 것은 **다음 세그먼트에 표시를 남기는 것**뿐이다.
      # `>|`(noclobber 무시)는 뒤의 `|` 를 여기서 먹는다 — 안 먹으면 `|` 가 경계가 되어
      # push_seg 가 `pre` 를 지우고, 리다이렉션 대상 표시가 사라진다(실측으로 뚫렸다).
      '>') push_seg ; pre='>' ; case ${s:i+1:1} in '|') i=$((i+1)) ;; esac ;;
      *) b+=$c ; u+=$c ; cw+=$c ; hasw=1 ;;
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

LEAD= ; RESTW=
seg_cmd() {   # $1 = 세그먼트의 **낱말 목록**(SW) → 어느 자리든 basename 이 git·gh 인 낱말을 찾는다
  local rest=$1 tok base
  while [ -n "$rest" ]; do
    rest=${rest#"$USEP"}
    tok=${rest%%"$USEP"*}
    case "$rest" in *"$USEP"*) rest=${rest#"$tok"} ;; *) rest= ;; esac
    [ -n "$tok" ] || continue
    tok=${tok#\$}          # `$'...'` 의 앞 `$`
    # 대소문자 무시 볼륨(macOS)에서는 `GIT push` 가 실제로 돈다
    base=$(printf '%s' "${tok##*/}" | tr 'A-Z' 'a-z')
    case "$base" in git|gh) LEAD=$base; RESTW=$rest; return 0 ;; esac
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

# ── 쓰기 대상 뽑기 — 게이트 훅이 못 보는 경로를 게이트에 넘긴다 ──────
# `PreToolUse` 의 matcher 는 도구 이름이라 `Write`·`Edit` 훅은 `cat > src/a.ts` 를 아예 못 본다.
# 여기서 대상 경로만 뽑아 **같은 게이트**에 물어본다 — 조건을 두 번 적으면 두 판정이 어긋난다.
#
# 파일을 쓰는 명령 목록. **늘리는 비용이 한 줄이다.**
#   `<이름> <반드시 있어야 하는 플래그 정규식(없으면 -)> <대상 위치>`
# 대상 위치 — 어느 인자가 파일인지가 명령마다 다르다. 이게 JSON 이 아니라 셸에 있는 이유고
# 머리말 `@flow-shell-rules` 의 `bash-write-command` 가 그 이유를 적어 둔다.
#   all   플래그 아닌 낱말 **전부** (여러 파일을 받는 것 — tee · sed -i)
#   last  플래그 아닌 **마지막** 낱말 (원본→대상 형태 — cp · mv · ln · install)
#   of    `of=` 값 (dd)
#
# `last` 를 쓰는 이유: `cp src/a.ts /tmp/backup.ts` 에서 원본까지 대상으로 뽑으면
# **읽기만 하는 복사가 막힌다.** 과차단은 사람이 훅을 꺼 버리게 만든다.
WRITE_CMDS='tee - all
sed (^|[[:space:]])-i([^a-zA-Z]|$) all
gsed (^|[[:space:]])-i([^a-zA-Z]|$) all
perl (^|[[:space:]])-[a-zA-Z]*i[a-zA-Z]*([[:space:]]|$) all
cp - last
mv - last
ln - last
install - last
truncate - last
rsync - last
dd - of'

seg_writer() {   # $1 = 세그먼트의 낱말 목록(SW) → 파일을 쓰는 명령이면 WREST·WMODE 를 담는다
  local rest=$1 base name flag mode hay
  while next_word "$rest"; do
    rest=$NREST
    base=$(printf '%s' "${NW##*/}" | tr 'A-Z' 'a-z')
    # 플래그 정규식은 `(^|[[:space:]])-i…` 처럼 **공백 경계**로 쓰여 있다. 낱말 목록은
    # USEP 로 이어져 있어 그대로 대면 `-i` 앞이 공백이 아니라 안 맞는다 — 실제로
    # `sed -i` 가 조용히 안 잡혔다. 그래서 경계를 공백으로 되돌려 놓고 본다.
    hay=$(printf '%s' "$rest" | tr '\037' ' ')
    while IFS=' ' read -r name flag mode; do
      [ -n "$name" ] || continue
      [ "$base" = "$name" ] || continue
      if [ "$flag" = '-' ] || printf '%s' "$hay" | grep -qE -- "$flag"; then
        WREST=$rest; WCMD=$base; WMODE=$mode; return 0
      fi
    done <<EOF
$WRITE_CMDS
EOF
  done
  return 1
}

# 대상 후보를 뽑는다. **넉넉히 뽑는다** — 게이트가 소스 아닌 것을 걸러 주므로
# 더 뽑는 것은 무해하고, 덜 뽑는 것은 구멍이다(`sed -e 's/x/y/' f` 의 표현식은 게이트가 통과시킨다).
# 단 `last` 모드는 반대다 — 거기서 넉넉히 뽑으면 읽기 전용 원본이 막힌다.
target_words() {   # <낱말 목록> <모드>
  local rest=$1 mode=$2 out= last=
  while next_word "$rest"; do
    rest=$NREST
    case "$mode" in
      of) case "$NW" in of=*) printf '%s\n' "${NW#of=}" ;; esac ;;
      last) case "$NW" in -*) ;; *) last=$NW ;; esac ;;
      *) case "$NW" in -*) ;; *) printf '%s\n' "$NW" ;; esac ;;
    esac
  done
  [ "$mode" = last ] && [ -n "$last" ] && printf '%s\n' "$last"
  return 0
}

write_targets() {   # 쓰기 대상 후보를 한 줄에 하나씩
  local i=0 t
  while [ "$i" -lt "${#SB[@]}" ]; do
    # @rule bash-write-redirect
    if [ "${SP_[$i]}" = '>' ]; then
      # 낱말 목록의 **첫 낱말**이다. SU 를 공백으로 자르면 `> "src/a b.ts"` 가 `src/a` 로 잘린다.
      if next_word "${SW[$i]}"; then
        # `2>&1` 의 `&1` 이나 `/dev/null` 은 게이트가 걸러 준다 — 여기서 판정하지 않는다
        printf '%s\n' "$NW"
      fi
    fi
    # @rule bash-write-command
    WREST= ; WCMD= ; WMODE=
    if seg_writer "${SW[$i]}"; then
      target_words "$WREST" "$WMODE"
    fi
    i=$((i+1))
  done
}

if [ -n "$DUMP_WT" ]; then
  write_targets
  exit 0
fi

# 게이트에 물어본다. 게이트가 없으면(설치가 덜 됐다) **조용히 넘긴다** —
# 여기서 막으면 가드가 게이트의 고장까지 떠안아 모든 Bash 가 멈춘다.
GATE="${FLOW_GATE:-$here/gate-source-write.sh}"
if [ -f "$GATE" ]; then
  while IFS= read -r wt; do
    [ -n "$wt" ] || continue
    grc=0
    gout=$(FLOW_TOPOLOGY="${FLOW_TOPOLOGY:-}" bash "$GATE" --path "$wt" 2>&1) || grc=$?
    case "$grc" in
      2) echo "" 1>&2
         echo "⛔ flow guard: Bash 로 소스 파일에 쓰려 했습니다 — 게이트가 막았습니다." 1>&2
         echo "   명령: $flat" 1>&2
         printf '%s\n' "$gout" 1>&2
         exit 2 ;;
      3) ask "Bash 경유 쓰기 ($wt)" "게이트 판정 근거를 확인하세요." \
            "$(printf '%s' "$gout" | tr -d '\n')" ;;
    esac
  done <<EOF
$(write_targets)
EOF
fi

words() {   # 낱말 목록 → 옵션(과 값을 먹는 것의 값)을 빼고 공백으로 이은 낱말들
  local rest=$1 out=
  while next_word "$rest"; do
    rest=$NREST
    case "$NW" in
      -c|-C|--git-dir|--work-tree|--namespace|--exec-path|-u|-g|-n|-R|--repo)
        next_word "$rest" && rest=$NREST ;;      # 값을 먹는 옵션은 값까지 버린다
      -*) ;;
      *) out="$out $NW" ;;
    esac
  done
  printf '%s' "${out# }"
}

# `on: rest` 규칙(플래그를 보는 것)의 건초더미. **낱말에서 만든다** —
# 인용이 낱말을 가르지 않으므로 `git commit --no-veri"f"y` 의 `--no-verify` 가 여기 온다.
#
# 다만 **값을 먹는 옵션의 값은 뺀다.** `git commit -m "-n 을 쓰지 마세요"` 의 `-n` 은
# 커밋 메시지고 플래그가 아니다 — 안 빼면 정상 커밋이 막힌다(v1 케이스가 그걸 못 박았다).
# `-m`·`--message` 를 여기서만 목록에 넣는 이유가 그것이다(`words` 는 손대지 않는다).
rest_hay() {   # 낱말 목록 → 플래그를 찾을 문자열
  local rest=$1 out=
  while next_word "$rest"; do
    rest=$NREST
    case "$NW" in
      -m|--message|-c|-C|--git-dir|--work-tree|--namespace|--exec-path|-u|-g|-R|--repo|-F|--file)
        out="$out $NW"
        next_word "$rest" && rest=$NREST ;;
      *) out="$out $NW" ;;
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
  if seg_cmd "${SW[$i]}"; then
    args=${SU[$i]} ; rest=$(rest_hay "$RESTW") ; w=$(words "$RESTW")
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
