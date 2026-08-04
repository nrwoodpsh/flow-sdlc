#!/usr/bin/env bash
# flow 플러그인 버전을 두 파일에서 동시에 올린다 (semver).
#   plugins/flow/.claude-plugin/plugin.json  +  .claude-plugin/marketplace.json
# 설치측 캐시 키가 버전이라, 내용을 바꾸면 반드시 버전을 올려야 update가 재복사한다.
#
# 사용: scripts/bump-version.sh          → 세 번째 자리를 1 올린다 (0.8.0 → 0.8.1)
#       scripts/bump-version.sh major    → 1.0.0 처럼 앞자리를 올릴 때만
#
# 등급을 나누지 않는다. 설치측은 **버전이 같나 다르나만** 보고 캐시를 판단하며,
# 우리 팀은 항상 최신을 받는다 — patch/minor 를 갈라도 아무도 그 값을 읽지 않는다.
#
# 두 파일을 따로 손으로 고친 이력이 있으면 값이 어긋날 수 있다.
# 어긋난 채로 올리면 **한쪽만 바뀌는데 스크립트는 성공했다고 말한다** —
# 설치측은 marketplace.json 을 보고 캐시를 판단하므로 업데이트가 전달되지 않는다.
# 그래서 올리기 전에 일치를 확인하고, 올린 뒤 결과도 다시 읽어 확인한다.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
pj="$root/plugins/flow/.claude-plugin/plugin.json"
mp="$root/.claude-plugin/marketplace.json"

# ── 두 파일에서 값을 읽는다 (JSON 파서로 — 정규식은 형식이 바뀌면 조용히 빗나간다) ──
read_pair() {   # <키>  →  "plugin값<TAB>marketplace값"
  python3 - "$pj" "$mp" "$1" <<'PY'
import json, sys
pj, mp, key = sys.argv[1], sys.argv[2], sys.argv[3]
a = json.load(open(pj))
b = next((p for p in json.load(open(mp)).get('plugins', []) if p.get('name') == 'flow'), None)
if b is None:
    sys.stderr.write("marketplace.json 에 name=flow 항목이 없습니다\n"); sys.exit(1)
print(f"{a.get(key,'')}\t{b.get(key,'')}")
PY
}

check() {
  local ok=0 v1 v2 d1 d2
  IFS=$'\t' read -r v1 v2 < <(read_pair version)
  IFS=$'\t' read -r d1 d2 < <(read_pair description)
  printf '  version      plugin=%s  marketplace=%s' "$v1" "$v2"
  if [ "$v1" = "$v2" ]; then echo "  OK"; else echo "  ❌ 어긋남"; ok=1; fi
  printf '  description  '
  if [ "$d1" = "$d2" ]; then echo "일치  OK"
  else echo "❌ 어긋남 — 둘을 같게 맞춘다"; ok=1; fi
  return $ok
}

part="${1:-patch}"
case "$part" in
  patch|major) ;;
  *) echo "usage: bump-version.sh [major]   (인자 없으면 0.8.0 → 0.8.1)" >&2; exit 1 ;;
esac

echo "올리기 전 대조"
if ! check; then
  echo "" >&2
  echo "⛔ 두 파일이 어긋나 있어 올리지 않습니다." >&2
  echo "   이 상태로 올리면 한쪽만 바뀌고, 설치측은 업데이트를 못 받습니다." >&2
  exit 1
fi

IFS=$'\t' read -r cur _ < <(read_pair version)
IFS=. read -r MA MI PA <<< "$cur"
case "$part" in
  major) MA=$((MA+1)); MI=0; PA=0 ;;
  patch) PA=$((PA+1)) ;;
esac
new="$MA.$MI.$PA"

perl -i -pe "s/(\"version\"\s*:\s*)\"\Q$cur\E\"/\${1}\"$new\"/g" "$pj" "$mp"

# ── 올린 뒤 다시 읽어 확인한다 (치환이 빗나갔는데 성공으로 보이는 것을 막는다) ──
IFS=$'\t' read -r n1 n2 < <(read_pair version)
if [ "$n1" != "$new" ] || [ "$n2" != "$new" ]; then
  echo "" >&2
  echo "⛔ 치환이 제대로 안 됐습니다 — plugin=$n1  marketplace=$n2  (목표 $new)" >&2
  echo "   두 파일을 직접 확인하세요. 커밋하지 마세요." >&2
  exit 1
fi

echo "flow  $cur → $new"
echo "  - $pj"
echo "  - $mp"
echo "→ 이 두 파일을 **내용과 같은 커밋에** 포함하세요."
echo "   따로 커밋하면 내용만 push되고 버전은 안 올라가는 일이 생깁니다."
