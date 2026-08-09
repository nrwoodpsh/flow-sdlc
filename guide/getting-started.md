# Getting Started

> 설치부터 첫 기능까지. **왜 이렇게 만들었나**는 [`../README.md`](../README.md), 구조 정본은 [`../doc/01.architecture.md`](../doc/01.architecture.md) 다.

## 무엇이 어디 있나

| 층 | 무엇 | 소유 |
|:--|:--|:--|
| 공용 기계 | 커맨드·에이전트·스킬·절차 조각·훅 (플러그인) | 설치해서 쓴다 — 프로젝트에 복사하지 않는다 |
| 프로젝트 고유층 | `CLAUDE.md` · `workflow.config.json` · `doc/` | 프로젝트 |

프로젝트마다 하는 일은 **고유층 채우기**다. 커맨드는 고치지 않는다.

**정본은 데이터다.** 파이프라인 위상·게이트 조건(진입·퇴장)·게이트 면제는 `plugins/flow/flow.topology.json` 이,
차단 목록은 `plugins/flow/guard-rules.json` 과 가드 셸의 머리말이 갖는다.
문서에 보이는 표는 대부분 **그것의 생성물**이라 손으로 고치면 검사기가 잡는다.

### 커맨드 — 부르는 것

**상세는 커맨드 파일이 정본**이다(`plugins/flow/commands/*.md`). 여기는 이름표다.

| 커맨드 | 무엇을 | 산출물 |
|:--|:--|:--|
| `/flow:next` | 지금 뭘 할 차례인지 **파일에서 계산**해 답하고, 원하면 이어서 돌린다 | 없음 (넘김) |
| `/flow:setup` | 프로젝트 골격 + 스택 채움 + 도구 설치 + 훅 심기 (최초 1회) | `CLAUDE.md` · `workflow.config.json` · `doc/` |
| `/flow:prd` | 요구 정의 + **ID 발급** (`sys` · `domain` · `func` + `legacy`) | 요구 문서 |
| `/flow:design` | 분석 → 구조 확정, 기능이면 **task·계약까지** (동작 변경의 단일 정문) | 설계 문서 · `2.task` · `3.contract` |
| `/flow:build` | 설계·계약대로 구현 + **단위 검증까지** | 코드 · `4.build` · `5.verify` |
| `/flow:verify` | 테스트 실행 · 요구 커버리지 감사 | `5.verify` · 통합 리포트 |
| `/flow:review` | 코드 등급 점검 · `doc` 이면 문서 채점 | `6.review` |
| `/flow:sync` | 코드↔문서 수렴 (유일 퇴장구) | 문서 갱신 · `7.summary` |
| `/flow:commit` | 커밋 (main 이면 새 브랜치 · **push 는 사람**) | git 커밋 |
| `/flow:spike` | 되는지 모르는 것을 **버릴 코드**로 확인 | `spike/` · ADR |
| `/flow:publish` | 결과를 외부로 발행 | 외부 페이지 |

- **v1 에서 바뀐 것**: `ask` 와 `run` 이 `/flow:next` 로, `spec` 이 `/flow:design` 으로 합쳐졌고, `/flow:theme` 은 `theme-apply` 스킬이 됐다.
- **어느 커맨드 다음에 무엇이 오나는 `flow.topology.json` 이 정본이다.** 헤매면 `/flow:next` 가 그것을 읽어 답한다.

### 에이전트 — 대신 일하는 것

**직접 부르지 않는다.** 커맨드가 위임한다. 나눈 이유는 역할극이 아니라 **컨텍스트 비용과 권한 경계**다.

| 에이전트 | 무엇 | 왜 나눴나 |
|:--|:--|:--|
| `explorer` | 넓게 읽어 **결론만** 반환 | 파일 원문이 메인 컨텍스트를 먹지 않게 |
| `builder` | 코드 구현·수정 — **쓰기 권한은 이것뿐** | 코드가 바뀌는 자리를 하나로 |
| `verifier` | 테스트를 **돌려** Exit code 로 판정 | 만든 쪽이 자기 결과를 확인하지 않게 |
| `reviewer` | 정적분석·그래프 도구를 돌려 **발견 목록**을 만든다 | 무거운 실행을 격리 |
| `gatekeeper` | 산출물·주장을 **대조·반증**해 통과/차단 | **작업자와 판정자를 분리** |

- `verifier` 와 `reviewer` 는 둘 다 셸을 쓰지만 산출이 다르다 — 하나는 통과/실패, 하나는 severity 붙은 발견이다.
- **`gatekeeper` 에는 셸이 없다.** 도구를 돌리는 쪽과 그 결과를 의심하는 쪽을 가르려는 것이다.

### 스킬 — 여러 곳이 함께 보는 규약

**얇은 `SKILL.md`(판정과 인덱스) + `references/` 조각**이다. 커맨드는 필요한 조각만 읽는다.
어느 커맨드가 어느 조각을 싣는지는 [`../doc/02.skills-map.md`](../doc/02.skills-map.md) 와 `flow.topology.json` 이 정본이다.

| 갈래 | 스킬 |
|:--|:--|
| 추적·표현 | `traceability` · `usecase` · `doc-template` · `plain-writing` |
| 검증 | `testing` · `contract-gate` · `doc-verify` · `code-review` |
| 분석 | `code-graph` · `impact-analysis` · `drift-check` |
| 그 밖 | `default-reference` · `theme-apply` · `ops-doc` |

## 설치

새 프로젝트 폴더에서:

```
/plugin marketplace add nrwoodpsh/flow-sdlc       # 이 repo 를 플러그인 카탈로그로 등록
/plugin install flow@flow-sdlc --scope user       # 스코프는 아래 표
```

설치하면 `/flow:*` 커맨드가 뜬다. `project-template`·`presets` 도 함께 들어와 `/flow:setup` 이 `${CLAUDE_PLUGIN_ROOT}` 로 읽는다 — 따로 clone·복사할 것이 없다.

| 스코프 | 활성화 기록 | 쓰는 사람 | git | 언제 |
|:--|:--|:--|:--:|:--|
| **user** | `~/.claude/settings.json` | 나 · 내 모든 프로젝트 | ✗ | 개인 · 여러 프로젝트 병행 |
| **project** | `<프로젝트>/.claude/settings.json` | 이 repo 누구나 | ✓ | 팀 프로젝트 |
| **local** | `<프로젝트>/.claude/settings.local.json` | 나만 · 이 repo | ✗ | 개인 override |

- 여러 프로젝트를 병행하면 **`user` 를 기본**으로, 팀 repo 엔 **`project` 도** 추가해 커밋한다. 겹쳐 써도 된다.
- **팀원 합류**는 clone + 신뢰 승인만으로 끝난다 — `project` 스코프 설정이 커밋돼 있으면 install 이 필요 없다.
- **업데이트**는 `/plugin marketplace update flow-sdlc` 후 `/reload-plugins`.

## 프로젝트 세팅 — `/flow:setup`

```
/flow:setup list          # 원형 목록만 보기 (아무것도 안 만든다)
/flow:setup               # 대화형
/flow:setup {원형키}       # 원형 바로 지정 (또는 repo URL = 커스텀 원형)
```

| 하는 일 | 내용 |
|:--|:--|
| 만들기 | `doc/` 골격 · `CLAUDE.md` · `workflow.config.json` — **`project-template/` 에서 복사한다** |
| 채우기 | 스택·네이밍·도메인 후보를 스캔해 추론 |
| 묻기 | 감지 못 한 것만 — 스택·테스트 명령·도메인 후보 |
| 심기 | 드리프트 훅 설치 · CI 씨앗 파일 복사 · 도구 설치 |

- **도구 목록과 설치법을 여기 적지 않는다** — 정본은 `${CLAUDE_PLUGIN_ROOT}/presets/tools/README.md` 이고 `/flow:setup` 이 스택에 맞춰 골라 제시한다. 대부분 선택이라 없으면 대체 경로로 돈다.
- **`/flow:setup` 이 끝에 "무엇이 기계이고 무엇이 옵트인인지" 를 표로 알린다.** 안 켠 층은 없는 층이다 — 그걸 켜졌다고 적지 않는 것이 이 플러그인의 규칙이다.
- 생성된 구조·규약은 프로젝트의 `doc/README.md` 가 정본이 된다.

## 개발 흐름

1. `/flow:setup` — 최초 1회 (+원형 · 도구 · 훅)
2. `/flow:spike` — 되는지 모를 때만
3. `/flow:prd` → `/flow:design` → `/flow:build` → `/flow:verify` → `/flow:review` → `/flow:sync` → `/flow:commit`
4. `/flow:publish` — 선택

**요구와 설계는 3레벨이다.** 시스템·도메인은 구현 없이 참조 정본으로 남고, 기능(work-unit)만 끝까지 간다.
레벨 판별 질문과 착지 위치는 `traceability` 스킬이 정본이다 — 애매하면 `/flow:next` 에 문장으로 물어도 된다.

**어디서 시작하나** — 안내일 뿐 강제가 아니다.

| 상황 | 시작 |
|:--|:--|
| 새 기능 | `/flow:prd func …` → `/flow:design` |
| 버그·변경 요청 | `/flow:design` — 요구를 자동 발급한다 |
| 레거시 프로젝트 | `/flow:prd sys legacy` — 코드에서 요구를 역추출 |
| 미검증 알고리즘 | `/flow:spike` |
| **뭘 할 차례인지 모르겠다** | **`/flow:next`** — 파일을 세어 계산하고, 원하면 이어서 돌린다 |

**규칙**

- 동작·로직 변경은 `/flow:design` 을 지난다. 오타·문구만 flow 밖에서 직접 고친다.
- 요구 ID 는 **불변**이다. 삭제는 폐기 표기, 분할은 하위 ID. 설계·task 는 **직접 충족한 ID 만** 태그한다.
- 커버리지 gap 을 **요구 삭제로 닫지 않는다** — 리포트가 결론이다.
- `/flow:commit` 은 요청할 때만 돈다. **push·merge 는 사람이 외부 도구로** 한다.
- 드리프트는 **커밋 전에 막힌다**(아래 `자동화`).

### 규모에 따라 쓰는 만큼만

**flow 는 다 채우라고 강요하지 않는다.** 작으면 절 절반이 비는 것이 정상이다.

| | 작은 도구 (도메인 1개·혼자) | 큰 제품 (도메인 여럿·팀) |
|:--|:--|:--|
| 시스템 요구 | **없어도 된다** — 횡단 제약이 없으면 | 있다 |
| 도메인 경계 | **비운다** — 도메인이 하나면 뜻이 없다 | 채운다 |
| 화면 지도 | 화면이 없으면 절 자체가 없다 | 있다 |
| 브랜치 통합 검증 | **건너뛴다** — 혼자면 프로젝트 검증과 시점이 같다 | 머지 전에 돈다 |

- **빈 절을 억지로 채우지 않는다.** 지어낸 내용이 낡은 문서보다 나쁘다.
- **자라면 그때 채운다.** 도메인이 둘이 되는 순간 경계가 필요해진다.

## 팀 협업

혼자면 넘어가도 된다. 2인 이상이면 **문서 소유권**을 정해야 한다.

| 규칙 | 내용 |
|:--|:--|
| 1 브랜치 = 1 work-unit 소유권 | 기능 브랜치를 연 사람이 그 유닛 폴더의 소유자다. 남의 유닛을 고치지 않는다 |
| 같은 도메인 동시 작업 | 유닛을 나눠 폴더 자체를 분리한다 — 물리 충돌이 없어진다 |
| 계약 충돌 | **선행 PR 의 계약을 정본**으로 채택하고 후행이 맞춘다 |
| PR 내용 | 코드와 유닛 문서(task·계약·요약)를 **함께** 올린다 |

**번호는 파일이 안 겹쳐도 겹친다.** 화면 번호·시스템 요구 번호·유닛 번호는 전역이라 두 사람이 같은 번호를 뽑는다.
막는 방법(구간 나눠 쓰기·먼저 발급·한 사람에게 모으기)과 머지 전 중복 판정의 정본은 **`traceability` 의 `conflict` 조각**이다.

## 자동화 — 무엇이 기계인가

**층 수를 세지 않는다.** 어느 경로에서 기계인지는 [`../README.md`](../README.md) 의 `강제력` 표가 정본이다.

### 위험 명령 차단 — 켜는 것이 아니라 항상 돈다

flow 를 설치하면 가드 훅이 함께 붙어 **되돌릴 수 없는 명령을 실행 전에 막는다.** 약속이 아니라 기계다.

```
⛔ flow guard: 되돌릴 수 없는 명령이라 차단했습니다 — git push
   push·merge 는 사람이 외부 도구로 합니다. 커밋까지는 /flow:commit 이 합니다.
```

- **무엇을 막고 무엇을 통과시키나는 [`../README.md`](../README.md) 의 `차단 목록` 이 정본이다** — 그 표는 `guard-rules.json` 과 가드 셸 머리말에서 생성되므로 여기 옮겨 적지 않는다.
- **끄는 스위치가 없다.** 환경변수로 열어 두면 AI 가 그 변수를 설정해 통과한다.
- **사람이 push 할 때는 안 걸린다** — Claude Code 세션 안의 명령만 본다.
- **뚫리는 길이 있다**(셸 우회·MCP 파일 도구). README 의 `못 막는 것` 절에 적어 뒀다 — **무심코 치는 것을 막는 장치**로 읽는다.

### 소스 쓰기 게이트 — 설계 없이 구현이 앞서가는 것을 막는다

소스 파일에 `Write`·`Edit` 가 들어오면 훅이 **그 파일을 담은 task 문서와 요구 태그**를 확인한다. 없으면 차단이다.

- 판정 근거는 `flow.topology.json` 의 `gate` 절이고, 셸 경유 쓰기는 가드가 경로를 뽑아 같은 게이트에 넘긴다.
- **면제가 있다** — `spike/` 아래 · 소스가 아닌 것 · 레거시 면제 유닛 · **유닛이 하나도 없는 도입 첫날.** 과차단은 사람이 훅을 꺼 버리게 만들기 때문이다.
- 막히면 훅을 끄지 말고 `/flow:design` 으로 task 문서를 먼저 만든다.

### 드리프트 훅 — Claude 밖에서 커밋해도 잡는다

`/flow:setup` 이 `pre-commit` 으로 심는다. `.githooks/` 에 두고 `core.hooksPath` 를 가리키므로 파일이 커밋되어 clone 마다 다시 깔 필요가 없다. 어디서 커밋하든 도는 셸 스크립트다.

- **코드가 바뀌었는데 작업 문서가 같이 안 바뀌었으면** 커밋이 막힌다. `/flow:sync` 를 먼저 돌린다.
- 무엇을 소스로 치나는 `workflow.config.json` 의 `drift.sourceGlobs`·`drift.ignore` 가 정하고, 판정 규칙의 정본은 `drift-check` 스킬이다.
- **유닛이 하나도 없으면 통과**한다 — 아직 체인을 안 쓰는 프로젝트다.
- `git commit --no-verify` 로 사람은 건너뛸 수 있다. **AI 는 못 한다** — 가드가 그 플래그를 막는다.
- **clone 한 사람은 `git config core.hooksPath .githooks` 한 줄이 필요하다.** 세션을 열면 훅이 그것을 알린다.

### CI 게이트 — 직접 켠다

로컬 훅은 사람이 건너뛸 수 있다. PR 에서 한 번 더 막으려면 `/flow:setup` 이 복사해 둔 워크플로 파일의 확장자를 벗긴다.

**이건 옵트인이다.** 켜지 않은 프로젝트에는 그 층이 없다 — 켰다고 적지 않는다.

## 자주 막히는 곳

| 증상 | 원인·해결 |
|:--|:--|
| 커맨드가 안 뜬다 | 설치 스코프를 확인하고 `/reload-plugins` |
| 소스를 쓰려는데 막힌다 | task 문서나 요구 태그가 없다 → `/flow:design` 으로 task 를 먼저 만든다 |
| 계약 검사가 안 돈다 | `contract.gate` 가 비었거나, 고친 파일이 `contract.pathGlob` **경로 패턴**과 안 맞는다 |
| `/flow:commit` 이 드리프트 경고 | 코드만 바뀌고 문서가 안 따라왔다 → `/flow:sync` 먼저 |
| `/flow:build` 가 엉뚱한 걸 잡는다 | 대상을 직접 지정한다 — `/flow:build {도메인}/{유닛}` |
| `/flow:next` 가 중간에 멈춘다 | 게이트가 막았거나 재시도가 소진됐다 → 리포트의 `어디 문제인가` 를 보고 그 국면을 손으로 고친 뒤 다시 부른다 |

## 각 파일 조정

`/flow:setup` 이 채운 것을 검수·수정할 때.

### `workflow.config.json` — 스택 주입

```jsonc
{
  "contract": { "pathGlob": "*/3.contract/*.ts",   // 파일명이 아니라 경로로 판정한다
                "gate": "…" },                      // 계약 검증 명령 ({file} 치환)
  "build":   { "command": "…" },
  "test":    { "command": "…", "browser": "playwright", "headless": false },
  "drift":   { "sourceGlobs": [], "ignore": ["**/*.md", "spike/**"] },   // 비어 있으면 넓게 본다
  "review":  { "severity": "critical" },
  "language": "korean"
}
```

- **키의 뜻과 안 맞을 때 무엇이 조용히 안 도는지는 `/flow:setup` 의 `실행 키는 돌려 보고 적는다` 절이 정본**이고, 계약 판정 규칙은 `contract-gate` 스킬이 갖는다. 여기 옮겨 적지 않는다.
- **`drift.sourceGlobs` 는 비어서 나간다.** 값이 있으면 **그 안만** 소스로 치는 화이트리스트라, 코드가 `lib/`·`backend/` 에 있는데 `src/**` 가 남아 있으면 쓰기 게이트와 드리프트 훅이 **함께, 아무 말 없이** 꺼진다. 비어 있으면 `doc/`·`spike/`·`.claude/`·`.github/` 밖이고 `.md` 가 아닌 것이 전부 소스다 — **넓어서 막히는 것은 보이고, 좁아서 안 막히는 것은 안 보인다.**
- 넓어서 걸리면 `drift.ignore`·`gate.legacyExempt` 로 좁힌다. **`sourceGlobs` 를 좁혀서 풀지 않는다** — 그건 게이트를 통째로 끄는 쪽이다.

### `CLAUDE.md` — 프로젝트 정체성·가드레일

- 자리표시자를 실제 값으로 채운다.
- **작게 유지한다** — 매 턴 컨텍스트에 실리는 유일한 파일이다. 스택·네이밍·금지사항 같은 **프로젝트 고유만** 둔다.
- 범용 워크플로우·일반 코딩 룰은 넣지 않는다. 플러그인이 이미 갖고 있다.

### `doc/00.ref/` — 참조 정본

폴더마다 고치는 주체가 정해져 있고, 그 소유표의 정본은 프로젝트의 `doc/README.md` 다.

- **요구·설계·화면 지도를 손으로 고치지 않는다** — 그 번호를 가리키는 태그가 여러 문서에 흩어져 있어 같이 안 바뀐다. 커맨드를 지나면 `/flow:sync` 가 대조한다.
