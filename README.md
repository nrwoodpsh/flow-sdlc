# flow — AI 개발 워크플로우 플러그인 (v2)

요구에서 커밋까지를 잇고, **어긋나는 것을 기계가 잡는다.**
v1(0.8.0) 진단은 `doc/00.diagnosis/`에 있고, 이 판의 구조는 `doc/01.architecture.md`가 정본이다.

## 왜 v2인가

v1은 세 층이 각각 다른 증상을 냈는데 원인이 하나였다 — **정본이 산문이라 기계가 못 읽는다.**
그래서 복제가 생기고, 복제를 맞추는 비용이 변경을 막고, 안 고쳐진 채 낡았다.

| 층 | v1 증상 | 근거 |
|:--|:--|:--|
| 커맨드 | 게이트를 4곳이 약속하고 실제로 거는 곳은 하나 | `diag-A` 4절 |
| 스킬 | `/flow:design` 한 번에 1,107줄이 실리고 실사용은 100여 줄 | `diag-B` 4절 |
| 인프라 | 차단 목록 하나 늘리는 비용이 9곳 → 미탐 9건이 남았다 | `diag-C` 4절 |

## 강제력 — 층 수를 세지 않고 경로를 적는다

v1 README는 "드리프트 4겹"이라 적었지만 **사람 경로만 4겹이고 AI 경로는 옵트인 CI 1겹**이었다.
그래서 이 표는 층을 세지 않고 **각 층이 어느 경로에서 기계인지** 적는다.

| 무엇 | Write·Edit | Bash | MCP 파일 도구 | 사람 편집기 |
|:--|:--|:--|:--|:--|
| 소스 쓰기 게이트 (task 문서·요구 태그) | **기계** | 가드가 경로를 뽑아 같은 게이트에 넘긴다 | **밖** | 밖 |
| 되돌릴 수 없는 명령 차단 | — | **기계** | 밖 | 밖 |
| 코드↔문서 드리프트 (커밋) | — | `--no-verify`를 가드가 막는다 | — | git 훅 (사람은 `--no-verify` 가능) |

- **"보장"이라 적지 않는다.** 기계인 것은 `Write`·`Edit` 경로이고, `Bash`는 가드가 닿는 범위까지, MCP는 밖이다.
- 내용 판정(설계가 요구를 실제로 덮나)은 `gatekeeper` 에이전트가 하고, **부르는 것 자체는 약속이다.**
- 약속을 약속이라고 적는 것이 `plugins/flow/flow.topology.json`의 일이다.

## 무엇이 정본인가

```
plugins/flow/flow.topology.json   위상 · 진입 조건(등급별) · 게이트 면제
  └─ gate-source-write.sh          (읽는다)
plugins/flow/guard-rules.json     차단 목록 중 단순 규칙
  ├─ guard-danger.sh               (읽는다)
  └─ scripts/tests/hooks.test.sh   (읽는다 — 케이스를 여기서 만든다)
guard-danger.sh 머리말            예외 로직이 붙은 셸 규칙 (고정 형식 주석 블록)
  └─ scripts/gen_docs.py           (긁어서 아래 표를 만든다)
```

**생성물은 커밋한다** — 플러그인 설치자에게 빌드를 요구할 수 없다. 대신 손으로 고치면 CI가 잡는다.

## 차단 목록

<!-- flow:gen guard-table -->
> **이 표는 생성물이다.** 손으로 고치지 마라 — `scripts/lint.py` 가 잡는다.
> 정본은 두 곳이고 아래에 절로 나눠 적는다.

### JSON 정본 — `plugins/flow/guard-rules.json`

명령 이름을 열거하면 되는 규칙이다. **늘리는 비용이 한 줄이다.**

**irreversible** — 되돌릴 수 없다 — 실행하면 복구 경로가 없거나 사람 손이 필요하다

| 명령 | 등급 | 왜 막나 |
|:--|:--|:--|
| `git push` | block | 원격 이력이 바뀐다 — 되돌리려면 남이 이미 받아 간 것을 고쳐야 한다. |
| `git merge` | block | 충돌 판단과 이력 결정이 사람 몫이다. |
| `git rebase` | block | 커밋 해시가 전부 바뀐다 — 이미 공유된 이력이면 되돌릴 수 없다. |
| `git filter-branch` | block | 이력 전체를 다시 쓴다. |
| `git filter-repo` | block | 이력 전체를 다시 쓴다. |
| `git reset --hard` | block | 커밋되지 않은 변경은 어디에도 남지 않는다. |
| `git clean -f` | block | 추적되지 않는 파일은 git 이 사본을 갖고 있지 않다. |
| `git pull --rebase` | block | rebase 와 같은 일을 한다 — 이력을 다시 쓴다. |
| `git checkout (변경 버림)` | block | `checkout -- .` 는 reset --hard 와 같은 손실이다. |
| `git switch (변경 버림)` | block | `switch -f` 는 커밋 안 된 변경을 버리고 옮긴다. |
| `git restore` | block | 작업 트리를 되돌린다 — `--staged` 만 인덱스라 안전하다. |
| `git reflog expire` | block | reflog 는 사고 뒤 되돌리는 마지막 안전망이다. |
| `git stash clear/drop` | block | 스태시는 커밋이 아니라 지우면 찾을 곳이 없다. |
| `git update-ref -d` | block | 참조가 사라지면 그 아래 커밋이 도달 불가가 된다. |
| `git subtree push` | block | 원격을 바꾼다 — push 와 같다. |
| `git branch -D` | block | 머지되지 않은 커밋이 도달 불가가 된다 — `-d` 는 그때 거부하니 통과시킨다. |
| `git worktree remove --force` | block | 미커밋 변경째로 워크트리를 지운다 — `--force` 없이는 git 이 거부하니 그건 통과시킨다. |
| `git gc --prune` | block | 도달 불가 객체를 즉시 지운다 — reflog 로도 못 찾는다. |
| `gh pr merge` | block | 머지는 사람의 판단이다. |
| `gh release delete` | block | 릴리스·태그가 원격에서 사라진다. |
| `gh repo delete` | block | 저장소가 사라진다. |
| `gh secret set` | block | 이전 값을 읽을 수 없어 되돌릴 수 없다. |
| `gh variable set` | block | CI 가 읽는 값을 바꾼다. |

**defense-off** — 다른 방어 층을 끈다 — AI 가 스스로 감시를 벗는 길이다

| 명령 | 등급 | 왜 막나 |
|:--|:--|:--|
| `git commit --no-verify` | block | drift 훅을 끈다 — 문서가 낡은 채 커밋되고 다음 세션이 그걸 진실로 믿는다. |
| `git -c core.hooksPath=…` | block | 훅 폴더를 바꿔 drift 훅 자체를 없는 것으로 만든다 — --no-verify 보다 조용하다. |

**external-state** — 우리 저장소 밖에 상태를 만든다 — 남이 보고 반응한다

| 명령 | 등급 | 왜 막나 |
|:--|:--|:--|
| `gh release create` | block | 태그와 릴리스가 원격에 남고 사람이 알림을 받는다. |
| `gh api 쓰기` | block | 임의의 GitHub 상태를 바꾼다 — 무엇이 바뀔지 훅이 알 수 없다. |
| `gh api graphql mutation` | block | GraphQL 읽기도 POST 라 메서드로는 못 가른다 — mutation 이라는 낱말로 가른다. |
| `gh api 쓰기(필드 플래그)` | block | 필드만 줘도 gh 가 POST 로 보낸다 — 메서드를 안 적어도 쓰기가 된다. |
| `gh workflow run` | block | **배포가 돈다.** 훅이 막는 것 중 유일하게 저장소 밖 시스템을 건드린다. |
| `gh pr create` | block | 리뷰어에게 알림이 가고 GitHub 에 상태가 남는다. |
| `gh issue create` | block | GitHub 에 외부 상태가 남고 사람이 알림을 받는다. |
| `gh repo create` | block | 조직에 저장소가 생긴다 — 지우는 것도 사람 일이다. |

**judgement** — 판단이 갈린다 — 정상 작업일 때가 있어서 무조건 막으면 사람이 훅을 끈다

| 명령 | 등급 | 왜 막나 |
|:--|:--|:--|
| `git commit --amend` | ask | 직전 커밋을 다시 쓴다 — 아직 push 안 했으면 정상 작업이고, 했으면 이력 사고다. |
| `git tag -d` | ask | 로컬 태그만이면 다시 붙이면 되고, 원격에도 있으면 릴리스 참조가 끊긴다. |
| `git stash pop` | ask | 충돌하면 스태시는 남지만 작업 트리가 반쯤 섞인다 — `apply` 가 더 안전하다. |

### 셸 정본 — `plugins/flow/hooks/scripts/guard-danger.sh`

예외 로직이나 인자 해석이 필요해 목록으로 표현할 수 없는 규칙이다.
머리말의 고정 형식 블록이 정본이고 이 표는 거기서 생성한다.

| 규칙 | 등급 | 무엇을 막나 | 왜 셸에 있나 |
|:--|:--|:--|:--|
| `bash-write-redirect` | block | `>` · `>>` 로 소스 파일에 쓰는 것 | 리다이렉션 대상은 토크나이저가 세그먼트 경계로 써서 버린다 — 명령 이름 목록으로 표현할 수 없다 |
| `bash-write-command` | block | `tee` · `sed -i` 계열로 소스 파일을 고치는 것 | 어느 인자가 파일인지가 명령마다 달라 인자 해석이 필요하다 |

### 못 막는 것

**층 수를 세지 않는다.** 아래가 이 가드의 바깥이다.

| 무엇 | 왜 |
|:--|:--|
| `python -c "open('src/a.ts','w')"` | 경로가 코드 안에 있어 셸이 알 수 없다 |
| `eval` · 변수로 쪼갠 경로 · 스크립트 파일에 써서 실행 | 셸을 해석해야 한다. 훅이 할 일이 아니다 |
| MCP 파일 도구 | matcher 가 도구 이름이라 훅이 아예 안 돈다 |
| 사람이 편집기로 고치는 것 | 훅은 Claude Code 세션에만 걸린다 |
| 셸 우회 — eval "git pu""sh" · P=push; git $P · 스크립트 파일에 써서 실행 | — |
| 다른 실행 경로 — python subprocess · MCP 도구 (matcher 가 Bash 라서 훅이 아예 안 돈다) | — |
| 사람 터미널 — 이 훅은 Claude Code 세션에만 걸린다. Sourcetree·IDE·직접 셸에는 안 걸린다 | — |
| deny-list 라 목록에 없는 명령은 통과한다. 늘리는 비용을 없앴으니 늘려서 대응한다 | — |
| 과차단 방향으로 기운 것 — `echo git push`(인용 없이)는 막힌다. 인용하면 통과한다 | — |
| here-doc 구분자를 못 닫으면 본문을 명령으로 스캔한다(과차단) | — |

생성: `python3 scripts/gen_docs.py --write`
<!-- /flow:gen guard-table -->

## 검사기와 테스트

| 무엇 | 돌리는 법 | 무엇을 지키나 |
|:--|:--|:--|
| 훅 테스트 | `bash scripts/tests/hooks.test.sh` | 케이스를 `guard-rules.json`에서 만든다 — 목록과 테스트가 어긋날 수 없다 |
| 문서 정합 | `python3 scripts/lint.py` | 검사마다 픽스처가 있어야 등록된다 |
| 검사기 자기 테스트 | `python3 scripts/lint.test.py` | **위반 픽스처가 통과하면 그 검사는 사문화** |
| 생성물 대조 | `python3 scripts/gen_docs.py --check` | 생성물을 손으로 고치는 것 |
| 매니페스트 | `bash scripts/bump-version.sh --check` | 두 파일이 어긋난 채 버전이 올라가는 것 |

넷 다 `.github/workflows/ci.yml`에서 돈다. **`.example`가 아니다** — v1은 드리프트 CI를 옵트인
예시로 뒀고 그게 AI 경로가 1겹이던 이유다.

**사용자 프로젝트에 주는 CI는 여전히 옵트인이다**(`.example`). 켜는 것은 그 프로젝트의 선택이고,
안 켠 프로젝트에는 그 층이 없다 — **옵트인을 기계라고 적지 않는다.**
