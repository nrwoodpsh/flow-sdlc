# 재설계 W1 — 커맨드·에이전트·위상 층

범위: `commands/*.md`(11) · `agents/*.md`(5) · `procedures/**`(13) · `flow.topology.json` · `project-template/CLAUDE.md`.
읽기만 했다. `python3 scripts/lint.py`(검사 26 통과) · `bash scripts/tests/hooks.test.sh`(371 통과) 를 전후로 돌렸고 그대로다.

렌즈: **주 사용 상황은 신규 생성이 아니라 이미 있는 시스템을 분석해 변형하기다.**

## 1. 능력 인벤토리

`강제자` 는 실제로 판정하는 것만 적는다. `—` 는 아무 기계도 없다는 뜻이다.

| 커맨드 | 입력 | 산출 | 국면 | 진입 조건 등급 · 실제 강제자 |
|:--|:--|:--|:--|:--|
| `setup` | `list`·원형키·git URL·(비움) | `CLAUDE.md`·`workflow.config.json`·`doc/` 골격·`03.templates/` 전체·`pre-commit` 훅·도구 | 도입 | 약속 1(멱등) · **—** |
| `next` | 자유 문장·`{도메인}/{NN.유닛}`·`이어서` | 산출물 없음(라우팅 판정·이어 돌리기) | 라우팅 | 약속 2(`has-config`·`ops-safety`) · **—** (`has-config` 는 `wasGrade: machine` 에서 내려옴) |
| `prd` | `sys`·`domain X`·`func X/NN`·`legacy`·`@참조` | 레벨별 요구 문서 + 요구 ID + `확인 필요`·외부 쿼터 대조 | 요구 | 내용 1(`level-decision`) → `gatekeeper` · 약속 2 · **—** |
| `design` | `sys`·`domain X`·`X/NN`·자유 문장(버그) | `1.design.md`·`2.task/*`·`3.contract/`·(도메인)유닛 계획·화면 지도 | 설계 | 내용 1(`requirement-covered`) → `gatekeeper` · 약속 1 · **—** |
| `build` | `도메인/유닛`·task 경로·(비움=파일 계산) | 소스 코드 · `4.build/NN.md` · `5.verify/NN.md` · task `History` | 구현 | **기계 2** — `hooks/scripts/gate-source-write.sh` (PreToolUse `Write\|Edit\|MultiEdit\|NotebookEdit`) · 내용 1 → `gatekeeper` · 약속 1 |
| `verify` | `unit`·`branch {이름}`·`project`·`coverage` | `5.verify/NN.md` · `03.integration/00.branch/…`·`01.project/` · 커버리지 분류표 | 검증 | 내용 1(`coverage-gap`) → `gatekeeper` · 약속 2 · **—** |
| `review` | (비움=diff)·경로·`deep`·`doc [경로]` | `6.review/NN.…md`(유닛일 때만) · 그 밖은 리포트만 | 리뷰 | 내용 1(`finding-severity`) → **`reviewer`** · 약속 1 · **—** |
| `sync` | (비움=diff 자동 분류)·`도메인` | 갱신된 설계·계약 · `7.summary/NN.…md` · 색인 · PR 초안 텍스트 | 수렴 | 약속 1(`source-changed`) · **—** |
| `commit` | (비움)·메시지 힌트 | git 커밋 1개 · (필요 시)`CLAUDE.md` Git 규약 | 커밋 | **기계 1** — `git-hooks/drift-hook.sh`(pre-commit). **`setup` 이 `core.hooksPath` 를 건 프로젝트에서만** |
| `spike` | 가설(필수)·검증 기준(필수)·`@참조` | `spike/00.{주제}/`(버림) · ADR · `00.ref/` 제약 | 검증(버릴 코드) | 약속 1(`throwaway`) · **—** (`spike/**` 는 쓰기 게이트 *면제* 대상) |
| `publish` | (비움=project)·`{도메인}/{NN.유닛}`·`→ 발행처` | 외부 페이지 · 발행 URL 한 줄(`7.summary/` 또는 `doc/README.md`) | 발행 | 약속 1(`external-confirm`) · **—** |

- **기계는 훅 2개가 전부다** — 쓰기 게이트(우회 불가) + 드리프트 pre-commit(옵트인·`--no-verify` 가능). 11개 중 9개는 기계 0. 데이터·본문·`lint.py`(`machine-gate-wired`·`entry-grade-parity`)가 이걸 일관되게 적고 있다 — v1 의 "4겹이라 적고 1겹" 병은 이 층에서 재발하지 않았다.
- `연결` 절 ↔ topology 배선 139건이 양방향 대조를 통과한다(v1 최다 결함 자리). **단 에이전트 행은 대조 밖이다** — 3절 (다).

## 2. 에이전트 5개

| 에이전트 | 왜 분리 | 도구(frontmatter) | 실제로 누가 부르나 | 안 부르면 |
|:--|:--|:--|:--|:--|
| `explorer` | 컨텍스트 격리 — 원문을 메인에 안 올린다 | `Read, Grep, Glob` | `prd`(prose:20) `design`(22) `setup`(18) `build` `verify` `review` `sync` `publish` | 컨텍스트 폭발뿐. 판정은 안 무너진다 |
| `builder` | 구현 격리 + **유일한 쓰기 주체** | `Read, Grep, Glob, Edit, Write, Bash` | `build` `spike` · (`theme-apply` 스킬도, builder.md:36) | 메인 세션이 직접 쓴다. 쓰기 게이트는 도구 단위라 **여전히 돈다** |
| `verifier` | 실행 판정 — Exit code | `Read, Grep, Glob, Bash` | `build`(루프) `verify` `spike` | 자기검증 편향. 막는 기계 없음(`no-self-verify` 는 약속) |
| `reviewer` | 도구를 직접 돌려 **룰 기반** 근거를 만든다 | `Read, Grep, Glob, Bash` | `review` 만 | critical 이 LLM 추측뿐이 되어 **아무것도 차단하지 못한다**(그 규칙상) |
| `gatekeeper` | 대조·반증. **`Bash` 없음이 의도** | `Read, Grep, Glob` | `prd` `design` `build` `verify` `review`(반증) `next`(전환) | 내용 등급이 전부 무효 — `lint.py:932` 은 본문에 호출 *문구*가 있나까지만 본다 |

- 분리 근거가 문서에 명시적이다: `verifier`(통과/실패) vs `reviewer`(severity 목록) vs `gatekeeper`(남의 주장 반증). 3자 구분은 v1 보다 선명하다.
- **`builder.md:16-17` 의 "쓰기 권한은 이 하나" 는 에이전트 사이에서만 참이다.** 메인 세션은 `Write`/`Edit` 를 갖고 커맨드는 그것을 쓴다 — "코드가 바뀌는 자리가 하나로 모인다" 는 **약속**이고 기계가 아니다. 지금 문장은 기계처럼 읽힌다.

## 3. 사슬의 구멍

**(가) `entry` 라 적힌 내용 조건이 실제로는 전부 퇴장 조건이다.**
`topology` 의 5개 `entry.content` 를 커맨드는 전부 *착지 전에* 판정시킨다 — `prd.md:32` `design.md:37` `verify.md:38` `review.md:37` `build.md:35-38`.
그런데 `next.md:30,94` 는 **전환할 때 다음 커맨드의 `entry.content` 를 `gatekeeper` 에게 준다**고 적는다. `build` 의 `contract-followed`("구현이 계약을 따르나", topology:410-416)는 구현 전에 판정할 대상이 없고, `verify` 의 `coverage-gap`(:473-479)은 감사 결과 자체다. **이어 돌리기의 전환 게이트는 5개 중 3개가 원리상 판정 불가다.** 결과: 진입 시점에는 아무 판정도 없다.

**(나) `review` 의 내용 조건 판정자가 `reviewer` 다** — `topology:542-548` 의 `who: reviewer`. `grades.content`(:40-44)는 *"gatekeeper — 진행하는 쪽이 아니다"* 라고 정의한다. 발견을 만든 쪽이 자기 진입 조건을 판정하는 구조이고, `lint.py:932-951` 은 `who` 를 안 보고 `gatekeeper` 호출 문구만 찾으므로 무관한 반증 문장(`review.md:37`)으로 통과한다.

**(다) 에이전트 배선에 정본이 없다.** `topology.agents` 는 조각만 갖고 **어느 커맨드가 어느 에이전트를 부르나가 없다.** `lint.py:895` 는 에이전트 이름을 "없는 이름" 오탐 방지용으로만 쓴다. 실측 결과: `next.md:16-19` 의 `연결` 절에 에이전트 행이 아예 없는데 본문(`next.md:94,97`)은 `gatekeeper` 를 부른다. v1 최다 결함(`연결`↔본문 어긋남)이 **에이전트 축에만 그대로 남아 있다.**

**(라) `next` 가 부를 수 없는 커맨드가 3개다.** `topology:200-209` 의 `next.next` 는 `prd·design·build·verify·review·sync·commit` 뿐이고 **`setup`·`spike`·`publish` 가 없다.** 그런데 `next.md:68` 은 설정이 없으면 `/flow:setup` 을 안내하라 하고, `next.md:141` 은 *"위상 정본에 있는 것만 부른다"* 고 못박는다. `next.md:76` 의 유형 칸에는 `불확실`(→ `spike` 여야 한다)이 있다. **불확실·발행은 라우터에서 도달 불가고, setup 안내는 자기 가드레일 위반이다.**

**(마) `design` 의 다음 국면이 레벨을 모른다.** `topology:377-381` 은 `design.next = [build, spike]` 인데 `design.md:81`·`procedures/design/system.md:76` 은 시스템·도메인은 **여기서 정지**라고 한다. `next` 는 `after`/`next` 를 그대로 읽어 제시하므로(`next.md:66`), 도메인 설계 직후 task 가 없는 상태에서 `build` 를 권한다.

**(바) 산출했는데 아무도 안 쓰는 자리 — `4.build/NN.md`.** `build.md:92` 가 쓰지만 `task-template.md:54` 는 *이탈의 정본은 task `History`, `4.build` 엔 한 줄만* 이라 하고, `sync`·`review`·`publish/collect.md:7-21` 은 `History`·`7.summary` 를 읽는다. 실제 소비는 `traceability/unit-state`(존재 여부로 상태 계산)뿐이다.

**(사) 소비자는 있는데 생산 커맨드가 없는 문서 3종.** `doc/04.ops/`(회고·SOP) — 소비: `procedures/review/doc.md:26-31`, `next` 의 `ops-doc/safety`. `doc/00.ref/05.explainer/` — `review/doc.md:35` 이 *"아무 커맨드도 이걸 만들지 않아, 요청이 없으면 영원히 안 생긴다"* 고 자백한다. `15.theme` 스펙 — `topology.direct_fragments` 가 사용자 직접 호출로 처리. 셋 다 `ops-doc`/`theme-apply` 스킬(등급 `자율`)이 유일한 생산자다. **파이프라인 안에서는 영구 빈 폴더다.**

**(아) 유닛 폴더를 만드는 주체가 선언돼 있지 않다.** 모든 것이 `01.work/{도메인}/{NN.유닛}/` 에 걸리는데 "이 폴더를 누가 만든다"는 문장이 없다. `prd func`·`design` 기능이 착지 경로로 *암묵적으로* 만들고(`level.md:9`), `sync/index.md:10` 은 *"유닛이 생기면"* 이라고 수동태다. `prd.md:106` 은 `func legacy` 에서 **유닛 생성을 명시적으로 거부**한다 — 즉 레거시에서는 암묵 생산자마저 없다.

**(자) 모드로 갈린 커맨드에 게이트가 하나다.** `verify` 는 4모드·`review` 는 2모드인데 `entry` 는 커맨드 단위다. `verify unit` 에는 `coverage-gap` 이 무의미하고 `review doc` 에는 `finding-severity` 가 무의미하다 — 그 모드로 들어가면 내용 게이트가 사실상 없다.

## 4. 레거시 변형 렌즈로 본 판정

**되는 것** (실측 근거 있음): `prd {레벨} legacy` 역추출(`prd.md:87-107`, 신규용 게이트 면제·전량 `확인 필요`) · 쓰기 게이트의 `any-unit-has-task` 바닥 판정(`topology:86-95`) · `design/system.md:72` 의 레거시 유닛 분할("이번에 손댈 범위") · `build.md:69` `[Mod]` 일 때만 회귀 표면 · `verify/run.md:40` 레거시 커버리지 분리. **국면 층에서 레거시를 의식한 문장은 v1 에서 이식된 것들이고 값이 있다.**

**신규 생성을 전제한 자리** —

1. **`drift.sourceGlobs` 기본값이 JS 신규 프로젝트 모양이다.** `project-template/workflow.config.json:22-25` = `src/**`,`app/**`. `gate-source-write.sh:218-220` 은 *globs 가 있고 안 맞으면 → 소스가 아니다 → allow* 다. 즉 코드가 `backend/`·`services/`·`modules/`·`cmd/`·`packages/` 에 있는 레거시 리포에서는 **쓰기 게이트가 전 파일을 통과시키고**, `drift-hook.sh:53,72` 가 같은 키를 읽으므로 **드리프트 훅도 함께 꺼진다.** 기계 2개가 동시에, 조용히 없어진다. `setup.md` 는 `drift.` 를 한 번도 언급하지 않는다(실행 키 표 `setup.md:91-97` 에 없다) — 돌려 확인하는 5개 키에 이것이 빠져 있다. **이 층에서 가장 큰 구멍이다.**
2. **`gate.legacyExempt` 를 채우는 커맨드가 없다.** 리포 전체에서 이 키는 `gate-source-write.sh:197`·`workflow.config.json:34`(빈 배열) 두 곳에만 나온다. `build.md:43` 은 "레거시 면제 유닛"을 작동하는 면제로 읽히게 적는다. 실제로는 사람이 설정을 손으로 고쳐야 켜지고, 아무 커맨드도 그 사실을 말하지 않는다 — **레거시 도입 첫날 과차단을 막으려고 만든 면제가 도달 불가다.**
3. **기존 시스템을 읽어 보고만 하는 진입점이 없다.** 11개 중 코드를 읽고 산출 없이 결론만 내는 것은 `review`(코드/문서 리뷰)뿐이고, 레거시 파악의 정문은 `prd legacy` 즉 **요구 문서를 쓰는 커맨드**다. `explorer` 는 있는데 그것을 감싼 커맨드가 없다. (v1 설치판에 있던 분석 진입점이 v2 커맨드 표(`01.architecture.md:139-153`)에서 언급 없이 사라졌다 — 그 표의 "빠진 것"은 `spec`·`theme`·`ask`·`run` 만 적는다.)
4. **`next` 에 레거시 경로가 없다.** v1 `ask.md:43` 에는 *"남의 코드를 파악해야 한다 → 레거시 → `/flow:prd sys legacy`"* 행이 있었다. v2 는 라우팅을 `traceability/level` 에 위임했는데 `level.md` 에 레거시 행이 없다. `next.md:76` 은 유형 칸에 `레거시` 를 출력하라 하면서 **그 유형을 어디로 보내는지 아무 데도 안 적혀 있다.**
5. **작은 레거시 수정의 빠른 경로가 끊긴다.** `level.md:22` 는 버그·작은 변경은 `design` 부터(요구 자동 발급)라 한다. 그 착지처는 유닛 안의 `0.requirement.md` 인데, 레거시엔 유닛이 없고 `prd.md:106` 은 유닛 생성을 거부한다. 결과 최소 경로가 `prd domain legacy → design domain(유닛 계획) → design 기능 → build` 4단이 되고, 그 사실을 알려 주는 커맨드가 없다.
6. *(추측)* `build` 의 대상 계산은 `2.task/NN` 있고 `4.build/NN` 없음(`build.md:49`)에 의존한다. 레거시에서 옮겨 온 유닛은 이미 코드가 있으니 이 계산이 "미착수"로 읽힐 소지가 있다 — 실제 동작은 확인하지 않았다.

**종합 판정**: 이 층은 레거시 *요구 역추출* 은 진지하게 다루지만, **레거시에서 기계 게이트를 실제로 켜는 배선(1·2)과 진입·라우팅(3·4·5)이 비어 있다.** 신규 프로젝트 가정이 남은 곳은 산문이 아니라 **기본 설정값과 라우팅 데이터**다.

## 5. 재설계 후보

**없어야 하는 것**

- `entry` 라는 이름 — 내용 조건은 전부 퇴장 조건이다. `exit.content` 로 바꾸고, 진입에서 볼 수 있는 것만 `entry` 에 남긴다. 근거: 3절 (가).
- `4.build/NN.md` — 이탈 정본이 task `History` 로 옮겨진 뒤 존재 여부 계산에만 쓰인다. 근거: 3절 (바).
- `topology` 의 커맨드 단위 `entry` — 모드로 갈린 커맨드에서 절반이 무의미하다. 근거: 3절 (자).

**나눌 것**

- `verify` → 실행(`unit·branch·project`)과 커버리지 감사. 이미 인자·조각·에이전트·게이트가 전부 갈려 있어 한 커맨드로 묶은 이득이 인자 하나뿐이다. 근거: `verify.md:8-15`, 3절 (자).
- `entry.content` 를 모드별로. 근거: 같음.

**합칠 것**

- `review doc` → `sync` 의 문서 점검과 겹친다(`sync.md:64` 가 이미 `doc-verify` 로 손댄 문서를 대조한다). 전수 채점만 남기고 커맨드 하나로 줄일 후보. *(추측 — 스킬 층은 W2 범위라 `doc-verify` 소비자 전수는 안 봤다.)*

**새로 필요한 것**

- **레거시 진입 커맨드**(가칭 `survey`) — 코드를 읽어 도메인 후보·경계·위험만 리포트하고 문서를 안 쓴다. `explorer` 를 감싸는 유일한 자리. 근거: 4절 3·4.
- **`setup` 의 소스 경로 확정 단계** — `drift.sourceGlobs` 를 실제 트리에서 감지해 적고, 못 맞추면 **키를 비워** 관대한 기본 판정으로 떨어뜨린다. 지금은 틀린 값이 남아 기계 2개를 조용히 끈다. 근거: 4절 1.
- **`gate.legacyExempt` 를 채우는 절차** — `setup`(기존 코드 감지 시) 또는 `design domain legacy`(손대지 않을 범위)에 붙인다. 근거: 4절 2.
- **에이전트 배선 정본** — `topology.commands[].agents` + `lint` 양방향 대조. 근거: 3절 (다).
- **`topology` 에 되돌아가는 간선** — 지금은 `next` 만 있고 역방향(`verify coverage` gap → `prd`, gatekeeper BLOCK → 직전 국면)이 산문에만 있다. 근거: `verify/coverage.md:40`, `next.md:98`.
- **레벨을 아는 `next`** — `design.next` 를 레벨 조건부로. 근거: 3절 (마).
- `next.next` 에 `setup`·`spike`·`publish` 추가, 또는 `next.md:68,141` 수정. 근거: 3절 (라).

**고칠 문장 2개** — `builder.md:16-17`(쓰기 단일 주체는 에이전트 간 약속이지 기계가 아니다) · `build.md:43`(도달 불가한 레거시 면제를 작동하는 것처럼 적는다).
