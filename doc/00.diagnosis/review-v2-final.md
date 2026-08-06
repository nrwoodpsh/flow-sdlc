# v2 최종 검증 — 진단이 짚은 결함이 닫혔나 (커밋 d1a6e51)

읽고 판정 + 실제로 검사·훅을 돌려 확인. 기준선 재확인: `lint.py` 17검사 통과·`lint.test.py` 17·`hooks.test.sh` 367/0·`gen_docs --check` 4곳 일치·`bump --check` 일치.
이전 리포트에서 지적하고 **고쳐진** 것(guard 구멍 C1 경로조작·H1 인용삽입·H2 쓰기명령)은 재검증만 했다 — 변형(플래그 안 인용·다른 정규화·symlink)까지 전부 차단, 재보고 안 함.

## 1~3. 판정 표

| 대상 | 판정 | 근거 |
|:--|:--|:--|
| **커맨드** — 위상 4벌 복제·게이트 1곳 | **부분** | topology 단일 정본化 + `command-loads-parity`(실재 스킬 양방향, 대상 139)로 복제·부정확은 닫힘. **그러나 게이트 강제는 build·commit 둘만 실제 기계고 나머지는 약속** → H1 |
| **스킬** — 규약=로드 단위 | **닫힘** | `references/` 조각 + `topology.loads` 정본, parity 강제. 조각 참조 31개 전부 디스크 실재(직접 확인) |
| **인프라** — 차단목록 셸+산문 5곳 | **닫힘** | `guard-rules.json` 단일 정본, `gen_docs` 가 README·CLAUDE 표 생성, `generated-up-to-date`+CI 가 대조. **JSON↔생성물 관계지만 손 동기화 아님** — 변조(행 삭제·공백·마커 제거) 셋 다 CI 가 잡음(이전 확인) |
| **남길 것 11항목** | **전부 남음** | 회귀 0. 이식 사고 주석 보존 확인(`guard-danger.sh:229` 인용스캐너·`drift-hook.sh:76` `set -f`·`bump-version.sh:18` 이중대조·표 렌더 4종·추적축·도구권한·자기검증금지·critical 룰기반·레거시면제·paths frontmatter) |
| **버릴 것** | **전부 빠짐** | 규모게이트 3벌·gatekeeper 표복제·ask 라우팅표·doc-template 등급표·default-reference setup행·검사4 화이트리스트22·README 트리·CLAUDE 산문목록·architectures 2행 전부 제거. `## 연결`만 "유지+기계검사"로 남음(회귀 아님) |

**"형태만 바뀜" 의심 판정**: 인프라의 `JSON↔생성물`은 형태만 바뀐 복제가 **아니다** — 생성·대조가 CI 기계라 사람이 두 곳을 맞추지 않는다. 반면 커맨드층의 **게이트 강제는 형태만 바뀌었다**(아래 H1).

## High

### H1 (최우선). 진입 게이트 5/7 이 "기계"라 적혔지만 강제하는 기계가 없다
설계는 강제력을 3등급(기계=PreToolUse 훅 / 분리판정=gatekeeper / 약속=커맨드 본문)으로 갈랐다(`01.architecture.md:23-27`). topology `commands.*.entry.machine` 로 등급을 데이터에 박고, 커맨드 `## 진입 조건` 표가 그걸 렌더한다. **그런데 PreToolUse 훅은 `guard-danger.sh`(위험 Bash)·`gate-source-write.sh`(소스 쓰기→task 문서) 둘뿐이고**(hooks.json 확인), gate 는 topology 의 `gate` 절만 읽지 `commands.*.entry` 는 **아무 것도 읽지 않는다**(grep 으로 확인 — `commands[].entry` 를 읽는 스크립트 0건).
```
machine 라벨의 실제 강제자:
  build  unit-task-doc/unit-req-tag → gate-source-write.sh   ✅ 진짜 기계 (재현 확인)
  commit no-drift → drift-hook.sh(pre-commit)                 △ setup 이 core.hooksPath 를 걸어야만 (M3)
  design requirement-doc-exists / "훅 — 경로 존재"            ❌ 어느 훅도 안 봄
  prd    has-config / "파일 존재"                             ❌   design 은 .md 를 쓰는데 gate 는 .md 를 면제한다
  verify unit-task-doc / "경로 존재"                          ❌
  next   has-config / "파일 존재"                             ❌
  sync   source-changed / "git diff"                          ❌ 커맨드가 자기 diff 를 보는 것 = 약속
```
`commands/design.md` 진입 조건 표는 사용자에게 *"기계 | 요구 문서가 있다 | 훅 — 경로 존재"* 라 적는다 — **훅이 검사한다는 거짓 표시**다. 이것은 v1 README 가 "드리프트 4겹"이라 적고 AI 경로는 1겹이던 병(`diag-C` 3절)과 **같은 종류**이고, 설계 자신이 *"약속인데 기계라고 적지 마라"* 며 고치겠다던 바로 그 자리다. `lint.py` 에 `entry.machine` 항목이 실제 훅에 배선됐는지 대조하는 검사는 **없다**(`topology-pending` 은 세 키의 존재만, `gatekeeper-delegation` 은 content 등급의 호출 지시만 본다). 순증은 있다 — v1 은 강한 게이트 1곳, v2 는 실제 기계 게이트가 build(+commit) 로 늘었다. 그러나 **표가 5곳을 기계로 과장한다.**

## Medium

### M2. 규약 미적재 방어의 절반이 구현되지 않았다 (새 실패 모드)
설계는 지연 로드의 뒷면(조각 미적재)에 방어 둘을 두겠다고 했다(`01.architecture.md:153-156`): ① SKILL.md 판정표 ② **산출물에 읽은 조각을 적고 검사기가 "이 상황인데 안 읽었다"를 대조.** ②가 구현에 **없다** — `lint.py`·SKILL.md 어디에도 "읽은 조각 기록" 대조가 없다(grep 0건). 조각을 안 읽고 지나가는 것은 여전히 무방비이고, 이건 v1 엔 없던(스킬이 늘 통째로 실려 규약이 항상 있었다) 새 실패 모드다.

### M3. `command-loads-parity` 는 실재 스킬만 본다 — 환각·오타 배선은 통과
`## 연결` 표에 topology `loads` 에 없는 이름을 넣어도, 그 이름이 **실재 스킬일 때만** `연결 초과`로 잡힌다(`lint.py:882` `named & ours`). 가짜 이름 `zzz-fake` 주입 → 통과(직접 확인). 실재 스킬 `code-review` 주입 → 잡힘, `traceability` 제거 → 잡힘. 즉 검사는 실효가 있으나, **오타나 환각한 스킬 이름은 조용히 통과**한다 — `01.architecture.md:175` 의 *"매 턴 실리는 거짓말이 구조적으로 불가능"* 은 그만큼 과장이다. (범위는 v1 보다 훨씬 좁다.)

### M4. commit 의 no-drift 는 프로젝트가 setup 을 마쳐야만 기계
`entry.machine no-drift` 는 `drift-hook.sh` 를 pre-commit 으로 건 프로젝트에서만 돈다. `setup.md:117-126` 이 `core.hooksPath` 배선을 사람에게 시키고 "확인 없이 완료 보고하면 거짓말"이라 정직히 적지만, **미설치 프로젝트·플러그인 자체 리포에는 그 층이 없다.** H1 의 commit 행에 △ 로 표시한 이유.

## 확인했으나 문제 아님 / 잔여 경미
- guard 3구멍 재검증: 플래그 안 인용(`git reset --har"d"`)·경로 정규화(`src/./`·`sub/../`)·symlink 면제 전부 **차단**. `rsync a src/x`(쓰기 목록 밖) 하나 통과 — H2 클래스의 미세 잔여, `WRITE_CMDS` 에 한 줄이면 닫힌다(언급만).
- fail 모드: gate 는 topology 부재·손상 시 ask(근거 주석), guard 는 rules 부재 시 경고+통과(근거 주석) — 이전 리포트에서 다뤘고 변화 없음.
- `## 연결` 표 **밖의** 산문은 parity 가 안 본다(표만 파싱) — 배선 정본이 아니므로 실해는 낮음(추측).

## 원복 확인
모든 실험은 `scratchpad/` 와 대상 파일 복사본에만 했고 매번 되돌렸다. `git status`: v2 **clean**, v1(`/Users/soulers/WKSPCES/flow-sdlc`) **clean**. 원복 후 `lint.py`·`gen_docs --check` 재통과 확인.
