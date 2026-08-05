#!/usr/bin/env python3
"""lint.py 자기 테스트 — 검사마다 통과 픽스처 1 + 위반 픽스처 1.

v1 은 `lint-docs.py` 가 전부 통과하는 상태에서 검사 하나가 **사문화**돼 있었다.
어떤 입력에도 실패하지 않는데 통과 숫자로는 구별되지 않았다(`diag-C` 2절·4절).
이 파일이 그 길을 막는다.

세 가지를 확인한다.

  1. 등록된 모든 검사에 픽스처가 있나 — `lint.py --list` 를 읽어 대조한다.
     검사를 더하고 테스트를 안 붙이면 여기서 실패한다.
  2. 위반 픽스처가 **실패하나** — 통과하면 그 검사는 사문화다.
     검사를 항상 `pass` 로 바꿔도 통과 픽스처는 통과한다. 위반 픽스처만 그걸 잡는다.
  3. 통과 픽스처에서 **대상이 0건이 아닌가** — 검사가 파일을 아예 못 찾으면
     걸릴 게 없어서 조용히 통과한다. 그것도 사문화다.

**크래시는 판정이 아니다.** 검사가 예외를 내거나 결과를 안 내면 스택 트레이스로 죽지 않고
그 검사 id 를 지목한 실패를 낸다. 이 테스트의 목적은 사문화된 검사를 **이름으로 부르는 것**인데
스택 트레이스는 그 일을 못 한다 — 사람이 원인을 못 읽는다.

픽스처는 임시 디렉터리에 쓰고 지운다. repo 문서는 건드리지 않는다.

돌리는 법:  python3 scripts/lint.test.py       (하나라도 걸리면 exit 1)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LINT = os.path.join(HERE, 'lint.py')

TPL = 'plugins/flow/project-template/doc/00.ref/03.templates'
F = '`' * 3          # 픽스처 안에 코드펜스를 쓰려면 이렇게 이어 붙인다


# ─────────────────────────────────────────────────────────────────────
# 픽스처 — 검사 id → (통과 케이스, 위반 케이스). 값은 {상대경로: 내용}.
# ─────────────────────────────────────────────────────────────────────

def _review_template():
    """왕복 검사용 템플릿 — 필수 절 둘."""
    return {f'{TPL}/06.review/review.md': (
        "# 리뷰\n"
        "\n"
        "## 판정 **[진행 필수]**\n"
        "\n"
        "## 발견 **[문서 필수]**\n"
    )}


def _skill(name, body, fm=''):
    return {f'plugins/flow/skills/{name}/SKILL.md':
            f"---\nname: {name}\n{fm}---\n\n# {name}\n\n{body}"}


def _review_skill(sections, fm='output-template: 06.review\n'):
    inner = '\n\n'.join(f'## {s}' for s in sections)
    body = ("리뷰 결과를 낸다.\n"
            "\n"
            "## 출력 형식\n"
            "\n"
            f"{F}markdown\n{inner}\n{F}\n"
            "\n"
            "## 경계\n"
            "\n"
            "코드를 고치지 않는다.\n")
    return _skill('code-review', body, fm)


CASES = {
    # ── 표 렌더 4종 ──
    'table-columns': (
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n| b | 둘 |\n"},
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하 | 나 |\n"},
    ),
    'table-orphan-row': (
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n\n표 뒤 문단이다.\n"},
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n\n"
                        "문단이 끼었다.\n| b | 둘 |\n"},
    ),
    'table-blank-line': (
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n\n- 불릿이다\n"},
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n- 불릿이 흡수된다\n"},
    ),
    'table-split': (
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n| b | 둘 |\n"},
        {'doc/case.md': "# 표\n\n| 이름 | 뜻 |\n|:--|:--|\n| a | 하나 |\n\n| b | 둘 |\n"},
    ),

    # ── frontmatter ──
    'argument-hint-quoted': (
        {'plugins/flow/commands/build.md':
            "---\nname: build\nargument-hint: '[유닛 ID]'\n---\n\n# build\n\n구현한다.\n"},
        {'plugins/flow/commands/build.md':
            "---\nname: build\nargument-hint: [유닛 ID]\n---\n\n# build\n\n구현한다.\n"},
    ),

    # ── 출력 형식 ↔ 템플릿 왕복 ──
    'output-sections-exist': (
        {**_review_template(), **_review_skill(['판정', '발견'])},
        # 템플릿에 없는 이름을 지어냈다
        {**_review_template(), **_review_skill(['판정', '안 본 층'])},
    ),
    'output-required-sections': (
        {**_review_template(), **_review_skill(['판정', '발견'])},
        # `발견`(문서 필수)이 빠졌다 — 그대로 만들면 채점에서 FAIL
        {**_review_template(), **_review_skill(['판정'])},
    ),

    # ── 스킬 간 중복 ──
    'skill-duplication': (
        {**_skill('traceability',
                  "요구 ID 를 발급하고 추적한다.\n\n"
                  "## 판정\n\n"
                  "- 요구 ID 는 발급한 순서대로 붙이고 지운 번호는 다시 쓰지 않는다\n\n"
                  "## 경계\n\n코드를 고치지 않는다.\n"),
         **_skill('testing',
                  "테스트를 돌려 판정한다.\n\n"
                  "## 판정\n\n"
                  "- 테스트는 실제로 실행해 exit code 로 통과를 확인한다 추론은 검증이 아니다\n\n"
                  "## 경계\n\n구현을 고치지 않는다.\n")},
        {**_skill('traceability',
                  "요구 ID 를 발급하고 추적한다.\n\n"
                  "## 판정\n\n"
                  "- 요구 ID 는 발급한 순서대로 붙이고 지운 번호는 다시 쓰지 않는다\n\n"
                  "## 경계\n\n코드를 고치지 않는다.\n"),
         **_skill('testing',
                  "테스트를 돌려 판정한다.\n\n"
                  "## 판정\n\n"
                  "- 요구 ID 는 발급한 순서대로 붙이고 지운 번호는 다시 쓰지 않는다\n\n"
                  "## 경계\n\n구현을 고치지 않는다.\n")},
    ),

    # ── 절 이름 번호·라벨 금지 ──
    'section-label': (
        {'plugins/flow/commands/design.md':
            "---\nname: design\n---\n\n# design\n\n## 판정\n\n## 연결\n\n## 경계\n"},
        {'plugins/flow/commands/design.md':
            "---\nname: design\n---\n\n# design\n\n## 1. 판정\n\n## 연결\n\n## 경계\n"},
    ),
}


# ─────────────────────────────────────────────────────────────────────

def _lint(argv):
    return subprocess.run([sys.executable, LINT] + argv,
                          capture_output=True, text=True)


def _tail(text, n=3):
    """스택 트레이스에서 사람이 읽을 마지막 줄들만."""
    lines = [l for l in (text or '').strip().split('\n') if l.strip()]
    return ' / '.join(l.strip() for l in lines[-n:])


def registered():
    """등록된 검사 id. `--list` 가 깨지면 그것도 판정으로 돌려준다 — 여기서 죽으면 안 된다."""
    cp = _lint(['--list'])
    if cp.returncode != 0:
        return None, (f"lint.py --list 가 실패했다 (exit {cp.returncode}) — "
                      f"{_tail(cp.stderr) or '출력 없음'}")
    try:
        return [c['id'] for c in json.loads(cp.stdout)], None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, (f"lint.py --list 출력을 읽을 수 없다 ({type(e).__name__}) — "
                      f"{_tail(cp.stdout) or '출력 없음'}")


def run_on(files, only):
    """픽스처를 임시 루트에 쓰고 그 검사 하나만 돌린다.

    **예외를 내지 않는다.** 검사기가 크래시하거나 결과를 안 내면 `_broken` 에 이유를 담아
    돌려준다 — 스택 트레이스로 죽으면 어느 검사가 사문화됐는지 이름으로 지목할 수 없다.
    """
    root = tempfile.mkdtemp(prefix='lint-fixture-')
    try:
        for rel, body in files.items():
            p = os.path.join(root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(body)
        cp = _lint(['--root', root, '--only', only, '--json'])
        if cp.returncode == 2:
            return {'_broken': f"lint.py 가 `{only}` 를 모른다 (exit 2) — "
                               f"{_tail(cp.stderr) or '출력 없음'}"}
        try:
            got = json.loads(cp.stdout)
        except json.JSONDecodeError:
            return {'_broken': f"lint.py 가 결과를 내지 않았다 (exit {cp.returncode}) — "
                               f"{_tail(cp.stderr) or _tail(cp.stdout) or '출력 없음'}"}
        checks = got.get('checks') or []
        if len(checks) != 1:
            return {'_broken': f"`--only {only}` 가 검사 {len(checks)}개를 돌렸다"}
        got = checks[0]
        if got.get('error'):
            return {'_broken': got['error']}
        return got
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    fails = []          # (검사 id, 이유) — 항상 이름으로 지목한다

    ids, err = registered()
    if err:
        print(f"  ❌ lint.py — {err}")
        print("\n자기 테스트 — 검사 목록을 못 읽어 아무것도 검증하지 못했다")
        return 1

    # ── 1. 픽스처 없는 검사 ──
    for cid in ids:
        if cid not in CASES:
            fails.append((cid, "픽스처가 없다 — `lint.test.py` 의 `CASES` 에 "
                               "통과 케이스 1 + 위반 케이스 1 을 추가한다"))
    for cid in CASES:
        if cid not in ids:
            fails.append((cid, "검사가 없는데 픽스처가 있다 — `lint.py` 에서 사라진 검사다 "
                               "(이름이 바뀌었나, 함수째 지웠나)"))

    # ── 2·3. 검사마다 통과·위반 ──
    for cid in ids:
        if cid not in CASES:
            continue
        ok_fx, bad_fx = CASES[cid]

        good = run_on(ok_fx, cid)
        if '_broken' in good:
            # 크래시를 판정으로 바꾼다 — 어느 검사가 고장났는지 이름이 남아야 한다
            fails.append((cid, f"검사가 결과를 내지 않았다 (사문화 의심) — {good['_broken']}"))
            continue
        if good['targets'] == 0:
            fails.append((cid, "통과 픽스처에서 대상 0건 — 검사가 파일을 못 찾았다 "
                               "(걸릴 게 없어 조용히 통과한다)"))
        if good['findings']:
            fails.append((cid, "통과 픽스처가 걸렸다 (오탐) — "
                               + ' / '.join(good['findings'][:2])))

        bad = run_on(bad_fx, cid)
        if '_broken' in bad:
            fails.append((cid, f"검사가 결과를 내지 않았다 (사문화 의심) — {bad['_broken']}"))
            continue
        if not bad['findings']:
            fails.append((cid, "**위반 픽스처가 통과했다 — 이 검사는 사문화다.** "
                               f"어기는 입력을 넣어도 실패하지 않는다 "
                               f"(대상 {bad['targets']} {bad['unit']})"))
        elif not good['findings'] and good['targets']:
            print(f"  ✅ {cid} — 통과 케이스 대상 {good['targets']} {good['unit']} · "
                  f"위반 케이스 실패 {len(bad['findings'])}")

    # ── 4. repo 전체에 대고 돌려도 검사기가 고장나지 않나 ──
    cp = _lint(['--json'])
    if cp.returncode == 3:
        seen = {cid for cid, _ in fails}
        try:
            for c in json.loads(cp.stdout)['checks']:
                if c.get('error') and c['id'] not in seen:
                    fails.append((c['id'], f"repo 전체 실행에서 검사기 고장 — {c['error']}"))
        except (json.JSONDecodeError, KeyError, TypeError):
            fails.append(('lint.py', f"repo 전체 실행에서 검사기 고장 (exit 3) — "
                                     f"{_tail(cp.stderr) or _tail(cp.stdout)}"))
    elif cp.returncode not in (0, 1):
        fails.append(('lint.py', f"repo 전체 실행이 비정상 종료 {cp.returncode} — "
                                 f"{_tail(cp.stderr) or _tail(cp.stdout) or '출력 없음'}"))

    print()
    if fails:
        for cid, why in fails:
            print(f"  ❌ {cid} — {why}")
        print(f"\n자기 테스트 — 검사 {len(ids)} · 실패 {len(fails)}")
        return 1
    print(f"자기 테스트 — 검사 {len(ids)} 전부 통과·위반 픽스처를 갖췄다")
    return 0


if __name__ == '__main__':
    sys.exit(main())
