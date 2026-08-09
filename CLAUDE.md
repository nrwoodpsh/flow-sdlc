# 이 리포에서 작업할 때

flow 플러그인 자체를 만드는 리포다. 사용자 프로젝트가 아니다.
구조 정본은 `doc/01.architecture.md`, v1 진단은 `doc/00.diagnosis/`.

**이 파일은 매 턴 실린다.** 여기 적을 것은 매 턴 알아야 하는 것만이다 —
목록·표는 정본을 가리키고 여기 복제하지 않는다. v1은 이 파일에 차단 목록을 산문과 표로
두 번 적어 두었고(3093자 중 54%가 가드레일 절), 그래서 목록을 늘리는 비용에 이 파일이 들어갔다.

## 정본을 손으로 두 곳 맞추지 않는다

| 무엇 | 정본 | 생성물 |
|:--|:--|:--|
| 위상·진입 조건·게이트 면제 | `plugins/flow/flow.topology.json` | 매니페스트 `description` |
| 차단 목록 (단순 규칙) | `plugins/flow/guard-rules.json` | `README.md` 차단표 · 아래 요약 |
| 차단 목록 (예외 로직) | `guard-danger.sh` 머리말의 `@flow-shell-rules` 블록 | 같음 |

생성물을 고치려면 정본을 고치고 `python3 scripts/gen_docs.py --write`를 돌린다.
**손으로 고치면 CI가 잡는다** (`scripts/lint.py`의 `generated-up-to-date`).

## 훅을 고쳤으면 되돌려서 실패하는지도 확인한다

통과 숫자만 보면 사문화된 검사와 지키는 검사가 구별되지 않는다. v1이 그렇게 낡았다.

- `guard-rules.json`에서 규칙 하나를 지우면 그 케이스가 **실패해야** 한다.
- `lint.py`에 검사를 더하면 `lint.test.py`에 **위반 픽스처**도 넣어야 한다. 안 넣으면 테스트가 실패한다.
- 검사기 고장과 문서 위반은 exit code로 갈린다 (`3` 고장 · `1` 위반).

## 재작성 금지

| 무엇 | 왜 |
|:--|:--|
| `guard-danger.sh`의 인용·here-doc 토크나이저 | `"it\'s a fix"`가 가드를 통째로 껐던 사고가 케이스로 박혀 있다 |
| `drift-hook.sh`의 `set -f` | 글로브가 디스크 파일로 확장돼 하위 파일을 놓친 사고 |
| "유닛 없으면 검사를 안 켠다" | 레거시 도입 첫날 전 커밋이 막힌다 |
| `bump-version.sh`의 이중 대조 | 두 매니페스트가 어긋나면 업데이트가 전달되지 않는다 |

## 가드 요약

<!-- flow:gen guard-summary -->
> 생성물이다. 손으로 고치지 마라. **전체 표는 `README.md`** — 여기는 매 턴 실려서 압축한다.

- **irreversible** (block) — `git push` · `git merge` · `git rebase` · `git filter-branch` · `git filter-repo` · `git reset --hard` · `git clean -f` · `git pull --rebase` · `git checkout (변경 버림)` · `git switch (변경 버림)` · `git restore` · `git reflog expire` · `git stash clear/drop` · `git update-ref -d` · `git subtree push` · `git branch -D` · `git worktree remove --force` · `git gc --prune` · `gh pr merge` · `gh release delete` · `gh repo delete` · `gh secret set` · `gh variable set`
- **defense-off** (block) — `git commit --no-verify` · `git -c core.hooksPath=…`
- **external-state** (block) — `gh release create` · `gh api 쓰기` · `gh api graphql mutation` · `gh api 쓰기(필드 플래그)` · `gh workflow run` · `gh pr create` · `gh issue create` · `gh repo create`
- **judgement** (ask) — `git commit --amend` · `git tag -d` · `git stash pop`
- **셸 정본** — `bash-write-redirect` · `bash-write-command` · `word-split-quotes`

차단 33건 · 확인 3건 · 셸 3건. 늘리려면 `guard-rules.json` 에 한 줄.
<!-- /flow:gen guard-summary -->

## 여기서 flow 커맨드를 쓰지 않는다

이 리포는 플러그인의 **소스**다. 자기 자신을 워크플로우로 돌리지 않는다 — 고치는 중인 커맨드로
고치면 무엇이 깨졌는지 가릴 수 없다. 검증은 `scripts/` 의 검사기·테스트가 한다.

## 커밋

`git commit`은 사용자가 요청할 때만 한다. `push`·`merge`는 사람이 외부 툴로 한다 — 가드가 막는다.
