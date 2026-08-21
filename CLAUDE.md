# 이 리포에서 작업할 때

flow 플러그인 자체를 만드는 리포다. 사용자 프로젝트가 아니다.
구조 정본은 `doc/01.architecture.md`, 스킬 조각 지도는 `doc/02.skills-map.md`.

**이 파일은 매 턴 실린다.** 여기 적을 것은 매 턴 알아야 하는 것만이다 —
목록·표는 정본을 가리키고 여기 복제하지 않는다. 차단 목록을 산문과 표로 두 번 적으면
목록을 하나 늘리는 비용에 이 파일이 들어간다.

## 정본을 손으로 두 곳 맞추지 않는다

| 무엇 | 정본 | 생성물 |
|:--|:--|:--|
| 위상·게이트 조건(진입·퇴장)·게이트 면제 | `plugins/flow/flow.topology.json` | 매니페스트 `description` |
| 차단 목록 (단순 규칙) | `plugins/flow/guard-rules.json` | `README.md` 차단표 · 아래 요약 |
| 차단 목록 (예외 로직) | `guard-danger.sh` 머리말의 `@flow-shell-rules` 블록 | 같음 |

생성물을 고치려면 정본을 고치고 `python3 scripts/gen_docs.py --write`를 돌린다.
**손으로 고치면 CI가 잡는다** (`scripts/lint.py`의 `generated-up-to-date`).

훅·검사기 작업 규율(되돌려서 실패 확인 · 재작성 금지)은 `.claude/rules/guard-work.md`에 있다 —
그 경로를 만질 때만 실린다.

## 가드 요약

<!-- flow:gen guard-summary -->
> 생성물이다. 손으로 고치지 마라. **전체 표는 `README.md`** — 여기는 매 턴 실려서 압축한다.

- **irreversible** (block) — 되돌릴 수 없다. `git push` · `git merge` · `git rebase` 등 23건
- **defense-off** (block) — 다른 방어 층을 끈다. `git commit --no-verify` · `git -c core.hooksPath=…`
- **external-state** (block) — 우리 저장소 밖에 상태를 만든다. `gh release create` · `gh api 쓰기` · `gh api graphql mutation` 등 8건
- **judgement** (ask) — 판단이 갈린다. `git commit --amend` · `git tag -d` · `git stash pop`
- **셸 정본** — `bash-write-redirect` · `bash-write-command` · `word-split-quotes`

차단 33건 · 확인 3건 · 셸 3건. 늘리려면 `guard-rules.json` 에 한 줄.
<!-- /flow:gen guard-summary -->

## 여기서 flow 커맨드를 쓰지 않는다

이 리포는 플러그인의 **소스**다. 자기 자신을 워크플로우로 돌리지 않는다 — 고치는 중인 커맨드로
고치면 무엇이 깨졌는지 가릴 수 없다. 검증은 `scripts/` 의 검사기·테스트가 한다.

## 커밋

`git commit`은 사용자가 요청할 때만 한다. `push`·`merge`는 사람이 외부 툴로 한다 — 가드가 막는다.
