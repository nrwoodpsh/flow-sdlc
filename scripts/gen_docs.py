#!/usr/bin/env python3
"""생성물 만들기 — 정본에서 문서·매니페스트를 채운다.

**차단 목록의 정본이 둘로 갈렸다.** 단순 규칙은 `guard-rules.json`, 예외 로직이 붙은 규칙은
셸에 남았다(설계 근거: 예외 로직을 데이터로 내리면 매칭 엔진 재작성이 된다).
갈라진 대가는 문서 표가 한쪽만 싣게 되는 것이다 — diag-C 4절이 짚은 '산문 사본' 관계가
셸 몫에 남는다. 그래서 **셸 규칙의 머리말을 고정 형식 주석 블록으로 두고 여기서 긁는다.**

무엇을 생성하나

  README.md         `guard-table`    차단표 전체 — `JSON 정본` 절 + `셸 정본` 절 + 한계
  CLAUDE.md         `guard-summary`  압축판. **이 파일은 매 턴 실린다** — 표를 다 싣지 않는다
                                     (v1 은 project-template/CLAUDE.md 3093자 중 54%가
                                      가드레일 절이었고 차단 목록이 산문·표로 두 번 나왔다)
  plugin.json       description      `flow.topology.json` 의 manifest 절에서
  marketplace.json  description      같은 값 — 두 파일이 어긋나면 업데이트가 전달되지 않는다

생성 자리는 마커로 감싼다. 마커 밖은 사람이 쓰는 글이라 건드리지 않는다.

    <!-- flow:gen guard-table -->
    …생성물…
    <!-- /flow:gen guard-table -->

돌리는 법
  python3 scripts/gen_docs.py --check   어긋나면 exit 1 (CI·lint 가 쓴다)
  python3 scripts/gen_docs.py --write   생성물을 다시 쓴다
  python3 scripts/gen_docs.py --print <블록>   생성 결과만 본다

**손으로 고치면 `--check` 가 잡는다.** 그 대조를 `lint.py` 의 `generated-up-to-date` 검사가
CI 에서 돌린다 — 생성기를 사람이 기억해서 돌리는 관계로 두지 않는다.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GUARD_RULES = 'plugins/flow/guard-rules.json'
TOPOLOGY = 'plugins/flow/flow.topology.json'
GUARD_SH = 'plugins/flow/hooks/scripts/guard-danger.sh'
PLUGIN_JSON = 'plugins/flow/.claude-plugin/plugin.json'
MARKET_JSON = '.claude-plugin/marketplace.json'

# 셸 머리말 고정 형식 — `lint.py` 의 `shell-guard-header` 검사도 같은 것을 읽는다.
SH_BEGIN = re.compile(r'^#\s*@flow-shell-rules(?:\s+v(\d+))?\s*$')
SH_END = re.compile(r'^#\s*@flow-shell-rules-end\s*$')
SH_RULE = re.compile(r'^#\s*rule:\s*(.+)$')
SH_LIMIT = re.compile(r'^#\s*limit:\s*(.+)$')
SH_MARK = re.compile(r'#\s*@rule\s+(\S+)')

BLOCK = '<!-- flow:gen {} -->'
BLOCK_END = '<!-- /flow:gen {} -->'


def read(root, rel):
    with open(os.path.join(root, rel), encoding='utf-8') as fh:
        return fh.read()


def load_json(root, rel):
    return json.loads(read(root, rel))


def cell(s):
    r"""표 칸에 넣을 수 있게 — 안 감싼 `|` 가 행을 깨뜨린다(`lint.py` 의 table-columns)."""
    return re.sub(r'(?<!\\)\|', r'\\|', str(s)).replace('\n', ' ').strip()


# ── 셸 머리말 긁기 ──

def shell_rules(root):
    """(v, [{'id','level','what','why'}], [{'what','why'}], [본문 @rule 표시...])

    형식이 깨지면 예외를 낸다 — 조용히 빈 목록을 돌려주면 표에서 셸 규칙이 사라지는데
    그게 정확히 이 블록을 둔 이유(셸 쪽이 낡는 것)를 못 막는 상태다.
    """
    text = read(root, GUARD_SH)
    lines = text.split('\n')
    v, rules, limits = None, [], []
    inside, seen_end = False, False
    for l in lines:
        if not inside:
            m = SH_BEGIN.match(l.strip())
            if m:
                inside, v = True, m.group(1) or '0'
            continue
        if SH_END.match(l.strip()):
            inside, seen_end = False, True
            continue
        m = SH_RULE.match(l.strip())
        if m:
            f = [x.strip() for x in m.group(1).split('|')]
            if len(f) != 4:
                raise ValueError(
                    f"@flow-shell-rules 의 rule 줄은 필드 4개다 (id | 등급 | 무엇 | 왜) — "
                    f"{len(f)}개다: {m.group(1)[:60]}")
            rules.append({'id': f[0], 'level': f[1], 'what': f[2], 'why': f[3]})
            continue
        m = SH_LIMIT.match(l.strip())
        if m:
            f = [x.strip() for x in m.group(1).split('|')]
            if len(f) != 2:
                raise ValueError(
                    f"@flow-shell-rules 의 limit 줄은 필드 2개다 (못 막는 것 | 왜) — "
                    f"{len(f)}개다: {m.group(1)[:60]}")
            limits.append({'what': f[0], 'why': f[1]})
    if v is None:
        raise ValueError(f"{GUARD_SH} 에 `# @flow-shell-rules` 블록이 없다 — "
                         f"셸에 남은 규칙을 문서 표에 실을 방법이 없어진다")
    if not seen_end:
        raise ValueError("`# @flow-shell-rules-end` 가 없다 — 블록이 어디서 끝나는지 모른다")
    marks = SH_MARK.findall(text)
    return v, rules, limits, marks


# ── 렌더 ──

def limit_rows(gr):
    """`guard-rules.json` 의 `limits` — **한계의 유일한 정본**.

    `{what, why}` 가 정상 형태다. 옛 문자열 형태도 받아 준다(왜는 `—`) — 형태 하나 때문에
    한계가 표에서 사라지면 문서가 실제 방어보다 넓게 읽힌다. 그게 v1 의 병이다.
    """
    out = []
    for x in gr.get('limits') or []:
        if isinstance(x, dict):
            out.append({'what': x.get('what', ''), 'why': x.get('why') or '—'})
        else:
            out.append({'what': str(x), 'why': '—'})
    return out


def _rule_rows(rules, classes, cid):
    out = []
    for r in rules:
        if r.get('class') != cid or r.get('tool') == 'write':
            continue
        name = r.get('label') or f"{r.get('tool')} {r.get('words')}"
        out.append(f"| `{cell(name)}` | {cell(r.get('level'))} | {cell(r.get('why'))} |")
    return out


def render_guard_table(root):
    gr = load_json(root, GUARD_RULES)
    classes = gr.get('classes') or {}
    rules = gr.get('rules') or []
    _, sh_rules, sh_limits, _ = shell_rules(root)

    L = []
    L.append('> **이 표는 생성물이다.** 손으로 고치지 마라 — `scripts/lint.py` 가 잡는다.')
    L.append('> 정본은 두 곳이고 아래에 절로 나눠 적는다.')
    L.append('')
    L.append('### JSON 정본 — `plugins/flow/guard-rules.json`')
    L.append('')
    L.append('명령 이름을 열거하면 되는 규칙이다. **늘리는 비용이 한 줄이다.**')
    L.append('')
    for cid, meta in classes.items():
        rows = _rule_rows(rules, classes, cid)
        if not rows:
            continue
        L.append(f"**{cid}** — {cell(meta.get('뜻'))}")
        L.append('')
        L.append('| 명령 | 등급 | 왜 막나 |')
        L.append('|:--|:--|:--|')
        L += rows
        L.append('')

    L.append('### 셸 정본 — `plugins/flow/hooks/scripts/guard-danger.sh`')
    L.append('')
    L.append('예외 로직이나 인자 해석이 필요해 목록으로 표현할 수 없는 규칙이다.')
    L.append('머리말의 고정 형식 블록이 정본이고 이 표는 거기서 생성한다.')
    L.append('')
    L.append('| 규칙 | 등급 | 무엇을 막나 | 왜 셸에 있나 |')
    L.append('|:--|:--|:--|:--|')
    for r in sh_rules:
        L.append(f"| `{cell(r['id'])}` | {cell(r['level'])} | {cell(r['what'])} | {cell(r['why'])} |")
    L.append('')

    L.append('### 못 막는 것')
    L.append('')
    L.append('**층 수를 세지 않는다.** 아래가 이 가드의 바깥이다.')
    L.append('')
    L.append('| 무엇 | 왜 |')
    L.append('|:--|:--|')
    # **한 정본에서만 렌더한다.** 예전에는 셸 머리말의 `limit:` 과 JSON 의 `limits` 를 둘 다
    # 실어서 겹치는 6개가 표에 두 번 나왔고, JSON 쪽 한 줄은 낡은 채(`rsync … 통과한다`)
    # 남아 있었다. 정본을 JSON 하나로 모았으니 여기서도 하나만 읽는다.
    for x in limit_rows(gr):
        L.append(f"| {cell(x['what'])} | {cell(x['why'])} |")
    L.append('')
    L.append('생성: `python3 scripts/gen_docs.py --write`')
    return '\n'.join(L)


def render_guard_summary(root):
    """CLAUDE.md 용 압축판 — **매 턴 실리는 파일이라 표를 안 싣는다.**"""
    gr = load_json(root, GUARD_RULES)
    classes = gr.get('classes') or {}
    rules = gr.get('rules') or []
    _, sh_rules, _, _ = shell_rules(root)

    L = []
    L.append('> 생성물이다. 손으로 고치지 마라. **전체 표는 `README.md`** — 여기는 매 턴 실려서 압축한다.')
    L.append('')
    for cid, meta in classes.items():
        names = [(r.get('label') or f"{r.get('tool')} {r.get('words')}")
                 for r in rules if r.get('class') == cid and r.get('tool') != 'write']
        if not names:
            continue
        lvl = meta.get('level', '')
        L.append(f"- **{cid}** ({lvl}) — " + ' · '.join(f'`{n}`' for n in names))
    L.append(f"- **셸 정본** — " + ' · '.join(f"`{r['id']}`" for r in sh_rules))
    L.append('')
    L.append(f"차단 {sum(1 for r in rules if r.get('level') == 'block')}건 · "
             f"확인 {sum(1 for r in rules if r.get('level') == 'ask')}건 · "
             f"셸 {len(sh_rules)}건. 늘리려면 `guard-rules.json` 에 한 줄.")
    return '\n'.join(L)


def render_description(root):
    topo = load_json(root, TOPOLOGY)
    m = topo.get('manifest') or {}
    cmds = topo.get('commands') or {}
    chain = m.get('descriptionChain') or []
    missing = [c for c in chain if c not in cmds]
    if missing:
        raise ValueError(f"manifest.descriptionChain 이 없는 커맨드를 가리킨다: {', '.join(missing)}")
    parts = ' → '.join(f"{cmds[c].get('phase') or c}({c})" for c in chain)
    return f"{m.get('descriptionHead', '')}{parts}. {m.get('descriptionTail', '')}".strip()


BLOCKS = {
    'guard-table': ('README.md', render_guard_table),
    'guard-summary': ('CLAUDE.md', render_guard_summary),
}


# ── 마커 블록 갈아 끼우기 ──

def splice(text, name, body):
    """마커 사이를 갈아 끼운 새 본문. 마커가 없으면 None."""
    a, b = BLOCK.format(name), BLOCK_END.format(name)
    i, j = text.find(a), text.find(b)
    if i < 0 or j < 0 or j < i:
        return None
    return text[:i + len(a)] + '\n' + body + '\n' + text[j:]


def current(text, name):
    a, b = BLOCK.format(name), BLOCK_END.format(name)
    i, j = text.find(a), text.find(b)
    if i < 0 or j < 0 or j < i:
        return None
    return text[i + len(a):j].strip('\n')


def check(root):
    """어긋난 것들의 설명 목록. 빈 목록이면 생성물이 정본과 맞다."""
    bad = []
    for name, (rel, fn) in BLOCKS.items():
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            bad.append(f"{rel} 이 없다 — `{name}` 블록을 담을 파일이다 "
                       f"(`python3 scripts/gen_docs.py --write` 로 만들 수 없다. 파일을 먼저 둔다)")
            continue
        text = read(root, rel)
        cur = current(text, name)
        if cur is None:
            bad.append(f"{rel} 에 `{BLOCK.format(name)}` … `{BLOCK_END.format(name)}` 마커가 없다")
            continue
        want = fn(root)
        if cur.strip() != want.strip():
            bad.append(f"{rel} 의 `{name}` 블록이 정본과 다르다 — 손으로 고쳤나 "
                       f"(`python3 scripts/gen_docs.py --write` 로 되돌린다)")
    want_desc = render_description(root)
    for rel, getter in ((PLUGIN_JSON, lambda d: d.get('description')),
                        (MARKET_JSON, lambda d: next(
                            (p.get('description') for p in d.get('plugins', [])
                             if p.get('name') == 'flow'), None))):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            bad.append(f"{rel} 이 없다")
            continue
        got = getter(load_json(root, rel))
        if got != want_desc:
            bad.append(f"{rel} 의 description 이 flow.topology.json 의 manifest 절과 다르다")
    return bad


def write(root):
    """생성물을 다시 쓴다. 바뀐 파일 목록을 돌려준다."""
    done = []
    for name, (rel, fn) in BLOCKS.items():
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            print(f"  ⚠ {rel} 이 없어 건너뜀 — 파일을 먼저 두고 마커를 넣어라", file=sys.stderr)
            continue
        text = read(root, rel)
        new = splice(text, name, fn(root))
        if new is None:
            print(f"  ⚠ {rel} 에 `{name}` 마커가 없어 건너뜀", file=sys.stderr)
            continue
        if new != text:
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(new)
            done.append(f"{rel} [{name}]")

    desc = render_description(root)
    pj = os.path.join(root, PLUGIN_JSON)
    if os.path.exists(pj):
        d = load_json(root, PLUGIN_JSON)
        if d.get('description') != desc:
            d['description'] = desc
            with open(pj, 'w', encoding='utf-8') as fh:
                json.dump(d, fh, ensure_ascii=False, indent=2)
                fh.write('\n')
            done.append(f"{PLUGIN_JSON} [description]")
    mp = os.path.join(root, MARKET_JSON)
    if os.path.exists(mp):
        d = load_json(root, MARKET_JSON)
        hit = next((p for p in d.get('plugins', []) if p.get('name') == 'flow'), None)
        if hit is not None and hit.get('description') != desc:
            hit['description'] = desc
            with open(mp, 'w', encoding='utf-8') as fh:
                json.dump(d, fh, ensure_ascii=False, indent=2)
                fh.write('\n')
            done.append(f"{MARKET_JSON} [description]")
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description='정본에서 생성물 만들기 (flow v2)')
    ap.add_argument('--root', default=REPO)
    ap.add_argument('--check', action='store_true', help='어긋나면 exit 1')
    ap.add_argument('--write', action='store_true', help='생성물을 다시 쓴다')
    ap.add_argument('--print', dest='show', help='블록 하나를 출력만 (guard-table·guard-summary·description)')
    a = ap.parse_args(argv)

    try:
        if a.show:
            if a.show == 'description':
                print(render_description(a.root))
            elif a.show in BLOCKS:
                print(BLOCKS[a.show][1](a.root))
            else:
                print(f"모르는 블록: {a.show} (있는 것: "
                      f"{', '.join(list(BLOCKS) + ['description'])})", file=sys.stderr)
                return 2
            return 0
        if a.write:
            done = write(a.root)
            if done:
                print('생성:')
                for x in done:
                    print(f"  - {x}")
            else:
                print('생성물이 이미 정본과 같다 — 바꾼 것 없음')
            return 0
        bad = check(a.root)
        if bad:
            print('생성물이 정본과 어긋난다:')
            for x in bad:
                print(f"  ❌ {x}")
            return 1
        print(f"생성물 {len(BLOCKS) + 2}곳이 정본과 같다")
        return 0
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        # 정본을 못 읽는 것은 "생성물이 맞다"도 "틀리다"도 아니다 — 별 코드로 가른다
        print(f"⛔ 정본을 읽을 수 없다: {type(e).__name__}: {e}", file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
