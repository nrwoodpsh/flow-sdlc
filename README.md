# flow — AI 개발 워크플로우 플러그인

요구에서 커밋까지를 잇고, **어긋나는 것을 기계가 잡는다.**
구조 정본은 `doc/01.architecture.md`, 스킬 조각 지도는 `doc/02.skills-map.md` 다.

## 원칙 — 정본은 데이터고 산문은 생성물이다

**정본이 산문이면 기계가 못 읽는다.** 그러면 복제가 생기고, 복제를 맞추는 비용이 변경을 막고,
안 고쳐진 채 낡는다. 그래서 세 가지를 데이터에 둔다.

| 무엇 | 정본 | 기계가 지키는 것 |
|:--|:--|:--|
| 위상·게이트 조건·커맨드↔조각 연결 | `flow.topology.json` | 훅이 읽어 게이트를 건다 · 검사기가 문서와 대조한다 |
| 차단 목록 | `guard-rules.json` | 가드가 읽는다 · 훅 테스트가 케이스를 여기서 생성한다 |
| 검사 자체 | `scripts/lint.py` + `lint.test.py` | 위반 픽스처가 통과하면 그 검사는 실패로 표시된다 |

**게이트를 약속하는 곳과 실제로 거는 곳이 다르면 그건 게이트가 아니다.** 그래서 강제력 등급을
데이터에 적고, 배선 없이 `machine` 을 달면 CI 가 실패한다.

## 강제력 — 층 수를 세지 않고 경로를 적는다

"드리프트 4겹"처럼 층을 세면 **사람 경로만 4겹이고 AI 경로는 옵트인 CI 1겹**인 상태가 숨는다.
그래서 이 표는 층을 세지 않고 **각 층이 어느 경로에서 기계인지** 적는다.

| 무엇 | Write·Edit | Bash | MCP 파일 도구 | 사람 편집기 |
|:--|:--|:--|:--|:--|
| 소스 쓰기 게이트 (task 문서·요구 태그) | **기계** | 가드가 경로를 뽑아 같은 게이트에 넘긴다 | **밖** | 밖 |
| 되돌릴 수 없는 명령 차단 | — | **기계** | 밖 | 밖 |
| 코드↔문서 드리프트 (커밋) | — | `--no-verify`를 가드가 막는다 | — | git 훅 (사람은 `--no-verify` 가능) |

- **"보장"이라 적지 않는다.** 기계인 것은 `Write`·`Edit` 경로이고, `Bash`는 가드가 닿는 범위까지, MCP는 밖이다.
- 내용 판정(설계가 요구를 실제로 덮나)은 `gatekeeper` 에이전트가 **그 커맨드가 끝낼 때** 한다 — 산출물이 나와야 판정할 대상이 있다(진입 시점에는 없다). **부르는 것 자체는 약속이다.**
- 약속을 약속이라고 적는 것이 `plugins/flow/flow.topology.json`의 일이다.

## 무엇이 정본인가

```
plugins/flow/flow.topology.json   위상 · 게이트 조건(진입·퇴장, 등급별) · 게이트 면제
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
| `bash-write-redirect` | block | 리다이렉션으로 소스 파일에 쓰는 것 — `>` · `>>` · noclobber 무시 형태 | 리다이렉션 대상은 토크나이저가 세그먼트 경계로 써서 버린다 — 명령 이름 목록으로 표현할 수 없다 |
| `bash-write-command` | block | 파일을 만드는 명령으로 소스를 쓰는 것 — tee · sed -i · gsed -i · perl -i · cp · mv · ln · install · truncate · rsync · dd(of=) | 어느 인자가 파일인지가 명령마다 달라(전부/마지막/of=) 인자 해석이 필요하다 |
| `word-split-quotes` | block | 낱말 안에 인용을 끼워 명령을 쪼개는 것 — `git p"u"sh` · `gh "pr" merge` | 셸의 단어 분리 규칙(인용은 단어 경계가 아니다)을 구현해야 판정된다. 목록으로 표현할 수 없다 |

### 못 막는 것

**층 수를 세지 않는다.** 아래가 이 가드의 바깥이다.

| 무엇 | 왜 |
|:--|:--|
| 셸 우회 — `eval "git pu" "sh"` · `P=push; git $P` · 스크립트 파일에 써서 실행 · 별칭(`git ci`) | 셸을 해석해야 알 수 있다. 훅이 할 일이 아니다 |
| ANSI-C 인용 — `git $'p\x75sh'` | 낱말은 제대로 나누지만 `\x75` 같은 이스케이프를 값으로 풀지 않는다. 풀려면 셸의 인용 해석기를 다 구현해야 한다 |
| 다른 실행 경로 — python subprocess · MCP 도구 | matcher 가 도구 이름이라 훅이 아예 안 돈다 |
| 사람 터미널 — Sourcetree · IDE · 직접 셸 · 편집기로 고치는 것 | 훅은 Claude Code 세션에만 걸린다 |
| deny-list 라 목록에 없는 명령은 통과한다 | 늘리는 비용을 없앴으니 늘려서 대응한다 — `guard-rules.json` 에 한 줄이다 |
| 과차단 쪽으로 기운 것 — `echo git push` 는 막힌다. `echo "git push"`(**한 낱말**로 인용)는 통과하지만 `echo "git" "push"`(낱말별 인용)는 막힌다 | 낱말이 `git`·`push` 로 갈리면 실행과 구별할 수 없다 |
| here-doc 구분자를 못 닫으면 본문을 명령으로 스캔한다 | 안전 측으로 기울였다 — 못 닫힌 본문을 데이터로 보면 그 안의 명령이 통째로 사라진다 |
| **쓰기** — 코드 안에 경로가 있는 것: `python3 -c "open('src/a.ts','w')"` · `node -e` · awk 의 `print > f` | 경로가 코드 안에 있어 셸이 알 수 없다 |
| **쓰기** — 목록에 없는 파일 생성 명령: `curl -o` · `wget -O` · `patch` · `xargs` 로 감싼 것 | 셸을 해석하지 않고 이름으로 판정하므로 목록 밖은 통과한다. `guard-danger.sh` 의 `WRITE_CMDS` 에 한 줄 더하면 잡힌다 |
| **쓰기** — 대상이 디렉터리인 복사: `cp a b dir/` | 그 안에 만들 파일 이름을 알 수 없다 |
| **쓰기** — 심볼릭 링크 우회 | 게이트는 경로 문자열만 정규화하고 realpath 는 안 쓴다 — 링크가 정상인 자리가 있어서다(테스트 환경의 `/tmp`↔`/private/tmp`) |

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
| 공식 검증기 | `claude plugin validate ./plugins/flow` · `claude plugin validate .` | **Claude Code 가 이 파일을 읽을 수 있나** — 벤더 스키마의 일이라 우리 검사기가 대신 판정할 수 없다 |

전부 `.github/workflows/ci.yml`에서 돈다. **`.example`가 아니다** — 드리프트 CI를 옵트인 예시로
두면 AI 경로가 1겹이 된다.

**사용자 프로젝트에 주는 CI는 여전히 옵트인이다**(`.example`). 켜는 것은 그 프로젝트의 선택이고,
안 켠 프로젝트에는 그 층이 없다 — **옵트인을 기계라고 적지 않는다.**
