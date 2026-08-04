# Getting Started

> [읽기용] 설치부터 첫 기능까지. (**왜 이렇게 만들었나** → [`../README.md`](../README.md) `왜 만들었나` · doc 규약 → 프로젝트 `doc/README.md`.)

## 개념

| 층 | 무엇 | 소유 |
|:--|:--|:--|
| 공용 기계 | 커맨드·에이전트·스킬·훅 (플러그인) | 설치해서 씀 (프로젝트에 복사 안 함) |
| 프로젝트 고유층 | `CLAUDE.md`·`workflow.config.json`·`doc/` | 프로젝트 |

프로젝트마다 하는 일 = **고유층 채우기** (커맨드는 안 고친다).

### 커맨드 — 부르는 것

**상세는 커맨드 파일이 정본**이다(`plugins/flow/commands/*.md`). 여기는 목록이다.

| 커맨드 | 무엇을 | 산출물 |
|:--|:--|:--|
| `/flow:ask` | 뭘 할지 모르겠으면 — 문장으로 쓰면 알맞은 커맨드로 보낸다 | 없음 (넘김) |
| `/flow:setup` | 프로젝트 골격 + 스택 채움 + 도구 설치 (최초 1회) | `CLAUDE.md`·`config`·`doc/` |
| `/flow:theme` | 프론트 테마 적용 (FE 프로젝트만) | 스타일 코드 |
| `/flow:spike` | 되는지 모르는 것을 **버릴 코드**로 확인 | `spike/` · ADR |
| `/flow:prd` | 요구 정의 + **ID 발급** (`sys`·`domain`·`func` + `legacy`) | `*.requirement.md` |
| `/flow:design` | 분석 → 구조 확정 (**동작 변경의 단일 정문**) | `*.design.md` |
| `/flow:spec` | task 분할 + 계약 확정 | `2.task`·`3.contract` |
| `/flow:build` | 설계·계약대로 구현 (테스트 루프) | 코드 · `4.build`·`5.verify` |
| `/flow:verify` | 테스트 실행 (`unit`·`branch`·`project`) | `5.verify`·`03.integration` |
| `/flow:review` | 코드 등급 점검 · `doc`이면 문서 채점 | `6.review` |
| `/flow:sync` | 코드↔문서 동기화 (**유일 퇴장구**) | 문서 갱신 · `7.summary` |
| `/flow:commit` | 커밋 (main이면 새 브랜치 · **push는 사람**) | git 커밋 |
| `/flow:run` | 위를 자동 연결 (`full`·`fix`·`design`·`build`) | 각 국면 산출물 |
| `/flow:publish` | 결과를 Notion 등으로 발행 | 외부 페이지 |

### 에이전트·스킬 — 대신 일하는 것

**직접 부르지 않는다.** 커맨드가 위임하거나, Claude가 필요를 알아보고 쓴다.

| 에이전트 | 무엇 | 왜 나눴나 |
|:--|:--|:--|
| `explorer` | 넓게 읽어 **결론만** 반환 | 파일 원문이 메인 컨텍스트를 먹지 않게 |
| `builder` | 코드 구현·수정 — **쓰기 권한은 이것뿐** | 쓰는 곳을 하나로 |
| `verifier` | 테스트 실행 · 리뷰 발견 **재확인** | 자기 일을 자기가 검증하지 않게 |
| `reviewer` | 룰·그래프 기반 코드리뷰 | 무거운 실행을 격리 |
| `gatekeeper` | 단계 전환 게이트 — 산출물↔스펙 대조 | **작업자와 분리** |

스킬은 **여러 곳이 함께 보는 규약**이다. 정본이 한 곳이라 어긋나지 않는다.

| 갈래 | 스킬 |
|:--|:--|
| 추적·표현 | `traceability`(ID·레벨·태그) · `usecase`(유스케이스 형식) · `plain-writing`(쉬운 말) · `doc-template`(절 등급·다이어그램 표기) |
| 검증 | `contract-gate`(계약 컴파일) · `tdd-verify`(Exit code 판정) · `test-spec`(테스트 명세) · `doc-verify`(문서 채점) · `code-audit`(코드 체크리스트) |
| 분석 | `code-graph`(관계 질의) · `impact-analysis`(회귀 표면) · `code-review`(리뷰 층·등급) |
| 그 밖 | `drift-check`(코드↔문서) · `default-reference`(무엇을 읽나) · `theme-apply`(테마 반영) · `ops-doc`(회고·절차·설명 노트) |

## 설치

### 새 프로젝트 설치

* **설치** — 새 프로젝트 폴더에서:

  ```
  /plugin marketplace add nrwoodpsh/flow-sdlc       # 이 repo를 플러그인 카탈로그로 등록(로컬 clone)
  /plugin install flow@flow-sdlc --scope user       # 스코프는 ②
  ```

  설치하면 `/flow:*` 커맨드가 뜬다. `project-template`·`presets`도 함께 들어와 `/flow:setup`이 `${CLAUDE_PLUGIN_ROOT}`로 읽는다 (별도 clone·복사 불필요).

* **스코프** — 파일은 어느 스코프든 중앙 캐시, "누가 쓰냐"만 정한다:

  | 스코프 | 활성화 기록 | 쓰는 사람 | git | 언제 |
  |:--|:--|:--|:--:|:--|
  | **user** | `~/.claude/settings.json` | 나 · 내 모든 프로젝트 | ✗ | 개인 · 여러 프로젝트 병행 |
  | **project** | `<프로젝트>/.claude/settings.json` | 이 repo 누구나 | ✓ | 팀 프로젝트 (팀원 공유) |
  | **local** | `<프로젝트>/.claude/settings.local.json` | 나만 · 이 repo | ✗ | 개인 override |

  > 여러 프로젝트를 병행하면 **`user`를 기본**으로(한 번 켜면 전부 뜸), **팀 repo엔 `project`도** 추가해 커밋. 둘은 겹쳐 써도 된다.

* **팀원 합류** — `project` 스코프로 커밋된 `settings.json` 덕에 팀원은 clone + 신뢰 승인만으로 flow가 붙는다 (install 불필요).

### 업데이트

오너가 플러그인을 고쳐 push한 뒤, 각 사용자가:

```
/plugin marketplace update flow-sdlc    # 새 버전 가져오기
/reload-plugins                          # 반영
```

## 프로젝트 초기 세팅 — `/flow:setup`

```
/flow:setup list          # 원형 카탈로그만 보기 (아무것도 안 만듦)
/flow:setup               # 대화형 (빈 프로젝트=원형 메뉴 / 진행중=목록만)
/flow:setup egov-msa-cc   # 원형 키 바로 지정 (또는 repo URL = 커스텀 원형)
```

`/flow:setup`이 수동 복사 없이 다 만든다:

| 하는 일 | 내용 |
|:--|:--|
| **만들기** | `doc/` 골격·`CLAUDE.md`·`workflow.config.json` (`${CLAUDE_PLUGIN_ROOT}/project-template/`에서 복사) |
| **채우기** | 스택·네이밍·도메인 후보를 스캔해 추론 |
| **묻기** | 감지 못 한 것만 — 스택·테스트 명령·도메인 후보 |
| **설치** | 도구를 추천하고 고른 것을 설치까지 |

생성 구조·규약은 프로젝트 `doc/README.md`가 정본. `doc/00.ref/03.templates/`엔 산출물 템플릿이 함께 복사되고, 계약 템플릿(`03.api-contract`)만 스택에 맞게 조정한다.

**도구는 대부분 선택이다** — 없으면 대체 경로로 돈다. 목록·설치법은 `presets/tools/README.md`.

**종류가 설치 방법을 정한다** — `MCP`·`CLI`는 Claude가 깔고, `플러그인`·`확장`은 명령만 안내받아 직접 깐다.

| 도구 | 종류 | 어디 쓰나 | 없으면 |
|:--|:--|:--|:--|
| **Playwright** 또는 **Claude in Chrome** | MCP · 확장 | 화면 테스트 (`/flow:verify`·`/flow:theme`) | **둘 중 하나는 필수** — 없으면 멈춘다 |
| **Joern** (CPG) | CLI | **영향 범위·데이터 흐름** 그래프 질의 (`code-graph`) | 축소 모드 — 1~2홉만, **흐름 추적은 못 한다** |
| **open-code-review** | CLI | 리뷰 룰 검출 — NPE·XSS·SQLi | LLM 판단만 (오탐 증가) |
| **ponytail** | 플러그인 | **코드를 덜 만들게** — 쓰기 전 "안 만들어도 되나" 판단 주입 · 과설계 삭제 목록 | 우리 `최소 코드`·`범위 준수` 규칙만 (문장 지침이라 약함) |
| **claude-security** | 플러그인 | 취약점 스캔 — **발견을 반박한 뒤 보고** (`/flow:review`) | `code-audit` 체크리스트 + LLM 판단만 (오탐 증가) |
| LSP (언어별) | 플러그인 | 타입·참조로 코드 이해 | grep으로 대체 (정확도 하락) |
| DB — `db-dev`(전권) · `db-prod`(읽기 전용) | MCP | 실제 컬럼 확인 · 개발에서 **마이그레이션을 돌려 검증** | `02.db-schema/` 파일만. 마이그레이션은 사람이 |
| Context7 | MCP | 라이브러리 최신 문서 | 학습 시점 기억에 의존 |
| GitHub | MCP | PR·이슈 논의로 "왜 이렇게 됐나" 확인 | 로컬 `git log`만 |
| Figma | MCP | 디자인에서 테마 토큰 추출 | `.md` 스펙을 사람이 준다 |
| codex | 플러그인 | **다른 모델이 설계를 의심** (`review deep`) · ⚠ 유료·외부 전송 | 그 층을 빼고 리포트에 적는다 |
| Notion | MCP | `/flow:publish` 발행 | `docx`·마크다운으로 |
| session-report | 플러그인 | 토큰·캐시 실측 (도구 효과 확인용) | 감으로 판단 |

**스택·원형에 맞는 공식 스킬은 `/flow:setup`이 그때 찾아 안내**한다 — 원형 `mcp-server`면 `mcp-server-dev`, Convex 프로젝트면 `convex` 같은 것. 마켓이 계속 늘어나니 목록을 들고 있지 않는다.

**기본으로 고르는 것**: Playwright/Chrome(택1) · Joern · open-code-review · **ponytail** · claude-security · LSP. 나머지는 필요할 때 고른다.

> **ponytail은 설치만으로 끝나지 않는다.** 코드는 `builder`라는 별도 창에서 쓰므로 거기까지 지침이 들어가야 효과가 있다 — `PONYTAIL_SUBAGENT_MATCHER=builder`. 강도도 `/ponytail full`로 한 번 정한다. 둘 다 사용자만 할 수 있다.

## 개발 흐름

**전체 순서**

1. `/flow:setup` (+원형 · 도구 설치)
2. `/flow:theme` — 프론트 테마 적용 (프론트 프로젝트만 · 원형 코드가 생긴 뒤)
3. `/flow:spike` — 알파 검증 (핵심 불확실할 때만)
4. `/flow:prd` — 요구 정의 (요구마다 ID)
5. `/flow:design` — 분석 → 설계도
6. `/flow:spec` — task 분할 + 계약
7. `/flow:build` ⇄ `/flow:verify` → `/flow:review` → `/flow:sync` → `/flow:commit`
8. `/flow:publish` — 노션 발행 (선택)

**레벨** — 요구·설계는 3레벨. 위 두 레벨은 구현 없이 `00.ref/`에 정본으로 남는다.

| 레벨 | 인자 | 어디까지 | 착지 |
|:--|:--|:--|:--|
| 시스템 (횡단·기술 구조) | `/flow:prd sys` | `design`에서 정지 | `00.ref/00.architecture/` |
| 도메인 (한 도메인) | `/flow:prd domain user` | `design`에서 정지 | `00.ref/01.domain/` |
| 기능 (work-unit) | `/flow:prd func user/00.login` | 끝까지 | `01.work/user/00.login/` |

**진입 지점** — 상황별 시작 커맨드. 순서는 권장일 뿐 강제가 아니다.

### 규모에 따라 쓰는 만큼만

**flow는 다 채우라고 강요하지 않는다.** 작으면 절 절반이 비는 게 정상이다.

| | 작은 도구 (도메인 1개·혼자) | 보통 (도메인 3~5개) | 큰 제품 (MSA·여럿) |
|:--|:--|:--|:--|
| `SYS-*` 시스템 요구 | **없어도 된다** — 횡단 제약이 없으면 | 있다 | 많다 |
| `13.architecture` | 구성 요소 한 줄 · **의존 방향·크로스 도메인 흐름 없음** | 절반 | 전부 |
| `09.domain` **경계** | **비운다** — 도메인이 하나면 뜻이 없다 | 채운다 | 채운다 |
| `09.domain` 용어·업무 규칙 | 있으면 채운다 (규모와 무관) | 같음 | 같음 |
| 화면 지도 | FE 없으면 **절 자체가 없다** | FE 있으면 | 있다 |
| `verify branch` | **건너뛴다** — 혼자면 `project`와 시점이 같다. 이때 **`project`가 `DR번호` 규칙까지 닫는다** | 쓴다 | 쓴다 |
| `/flow:run` | **`full {유닛}`** 으로 3층만 | `full project` | `full project` |

- **빈 절을 억지로 채우지 않는다.** 지어낸 내용이 낡은 문서보다 나쁘다.
- **`doc-verify`가 조건부 절을 안다** — 도메인 1개면 `경계`를, 횡단 제약이 없으면 `SYS-*` 요구를 FAIL로 세지 않는다.
- **자라면 그때 채운다.** 도메인이 둘이 되는 순간 `경계`가 필요해지고, 그때 쓰면 된다.

### 어디서 시작하나

| 상황 | 시작 |
|:--|:--|
| 새 기능 | `/flow:prd func …` → `/flow:design` |
| 버그·장애 | `/flow:design` (분석·요구 자동 발급) |
| 레거시 프로젝트 | `/flow:prd sys legacy` (코드에서 요구 역추출) |
| 미검증 알고리즘 | `/flow:spike` |
| 프론트 테마 적용 | `/flow:theme` (`setup` 이후 권장 — 원형 코드가 생긴 뒤) |
| 품질·보안 점검 | `/flow:review` (아무 때나) |
| 자동 진행 (유닛 하나) | `/flow:run full` |
| **버그를 고치는 것부터 동기화까지** | **`/flow:run fix {도메인}/{유닛}`** — `prd`를 안 지난다 |
| 제품 전체를 만든다 | `/flow:run full project` — 층마다 승인 |
| 전체 + **막히면 스스로 고쳐가며** | `/flow:run full project auto` — 설계까지만 고친다, 요구는 안 고친다 |
| **뭘 써야 할지 모르겠다** | `/flow:ask` — 그냥 문장으로 쓰면 알맞은 커맨드로 안내한다 |

**입력 예시**

- 요구:
  ```
  /flow:prd func user/00.login
  [목적] 회원이 이메일로 로그인
  [완료 기준] 성공 시 JWT 발급(30분) · 3회 실패 시 잠금
  ```
  → `0.requirement.md`에 `USER-LOGIN-1,2…` ID 발급.
- 설계:
  ```
  /flow:design user/00.login
  [REFERENCE] @doc/00.ref/02.db-schema/user.sql
  ```
  → `1.design.md`(분석 + 데이터·기능·화면 구조 + 설계 요소 `D-N`). 이어서 `/flow:spec`이 `2.task`·`3.contract` 생성(계약은 `contract-gate` 검증).
- 버그:
  ```
  /flow:design
  [버그] 로그인 후 401 간헐 발생
  [REFERENCE] @logs/error.log @src/auth/TokenFilter.java
  ```
  → 근본원인 확정 + **요구 자동 발급**(`USER-LOGIN-4`) → `/flow:spec`부터 재개.

**규칙**

- 동작·로직 변경은 `/flow:design` 필수. 오타·문구만 flow 밖 직접 편집.
- 요구 ID는 **불변**. 삭제는 `deprecated`, 분할은 하위 ID. 설계·task는 **직접 충족한 ID만** 태그한다.
- 개발이 끝나면 `/flow:verify project`(전체 통합테스트)가 요구 커버리지도 함께 리포트한다 — 미반영을 요구 삭제로 닫지 않는다.
- **장기 자율 작업은 모델을 올린다** — `/flow:run full`·`/flow:prd sys legacy`·`/flow:verify project`는 실행 전 세션 모델을 확인하고 Fable 5를 권고한다. 바꾸려면 `/model` 후 재실행(비용 2배·턴 수 분·30일 데이터 보존 필요). 그 외는 Opus 5로 충분.
- spike 코드는 승격 금지 — 지식(ADR·ref)만 남기고 `/flow:design`으로 재설계. (왜 → [`../README.md`](../README.md) `왜 만들었나`)
- `/flow:commit`은 요청 시에만. main이면 새 브랜치. **push·merge는 외부 툴로 직접.**
- drift는 **커밋 전에 차단**된다 (`자동화`). 범위는 `workflow.config.json`의 `drift.sourceGlobs`·`drift.ignore`.

## 팀 협업 (2인 이상)

혼자면 넘어가도 된다. 2인 이상이면 **설계 문서 충돌**을 막는 규칙이 필요하다 — `doc/00.ref/01.domain/`가 도메인 중복은 막지만, 같은 도메인을 동시에 건드릴 때의 소유권까지는 정하지 않는다.

| 규칙 | 내용 |
|:--|:--|
| **1 브랜치 = 1 work-unit 소유권** | 기능 브랜치(`feature/user-login`)를 연 사람이 그 work-unit(`doc/01.work/user/00.login/`)의 소유자. 남의 work-unit을 고치지 않는다. |
| **같은 도메인 동시 작업** | work-unit을 분리한다 — `user/00.login-auth/`와 `user/00.login-history/`처럼 폴더 자체를 나눠 물리 충돌을 없앤다. |
| **계약 충돌 시** | 두 브랜치의 계약(`3.contract`)이 겹치면 **선행 PR의 계약을 정본**으로 채택하고, 후행 PR 작성자가 자기 설계를 그 정본에 맞춘다. |
| **브랜치 = 색인 태그** | 한 브랜치가 work-unit 여러 개를 낳으면 `/flow:sync`가 git diff로 `01.work/README`(상단)에 브랜치별로 묶는다(사람 태깅 0). |

- work-unit은 폴더가 번호로 분리돼 물리 충돌이 거의 없다. 겹치면 일반 Git merge로 해결.
- **PR에 코드 + work-unit 문서(2.task·3.contract·7.summary)를 함께** 올린다. 리뷰어가 충돌·중복을 교차 확인한 뒤 승인. (push·merge는 사람이 외부 툴로 — `개발 흐름`과 같다.)
- **머지 전에 `/flow:verify branch`를 돌린다** — 유닛별로는 통과했어도 합쳐서 돌아가는지는 다른 문제다. **체인(`/flow:run`)엔 없다** — 머지 시점을 커맨드가 모르니 사람이 부른다. `/flow:commit`이 유닛 둘 이상이면 알려준다.
- 서버측 드리프트 강제가 필요하면 아래 **`자동화`**의 CI 게이트를 켠다.

### ID 동시 발급 — 파일이 안 겹쳐도 번호는 겹친다

폴더를 나눠도 **번호는 전역**이라 두 사람이 같은 번호를 뽑는다. merge가 조용히 통과하고, 나중에 `SCR-3`이 둘이 된다.

| 무엇이 겹치나 | 왜 |
|:--|:--|
| **`SCR-N`** (화면) | 프로젝트 전역 번호다. 브랜치마다 "다음 번호"를 따로 센다 |
| **`DR번호`** (도메인 업무 규칙) | 같은 도메인을 둘이 건드리면 겹친다 |
| **`SYS-N`** (시스템 요구) | 횡단이라 항상 전역이다 |
| **유닛 번호** (`00.login`의 `00`) | 같은 도메인 아래 새 유닛을 각자 만들면 겹친다 |

**막는 방법** — 셋 중 하나면 된다.

| 방법 | 어떻게 |
|:--|:--|
| **구간 나눠 쓰기** *(권장)* | 사람마다 대역을 미리 준다 — A는 `SCR-100~199`, B는 `SCR-200~299`. 조율 없이 끝난다 |
| **먼저 발급하기** | 작업 시작 전에 정본 파일(`00.ref/`)에 번호만 올려 커밋·push. 남이 그 번호를 못 뽑는다 |
| **한 사람에게 모으기** | 전역 ID(`SCR`·`SYS`) 발급을 한 사람이 맡는다. 팀이 작을 때만 |

- **`{도메인}-{유닛}-N`은 안 겹친다** — 유닛 안에서만 세니 소유자가 하나다.
- **`D-N`도 안 겹친다** — 문서 안에서만 쓰는 번호다.
- **`/flow:sync`가 머지 전에 중복을 본다** — 찾으면 **리포트하고 멈춘다**. **나중에 머지하는 쪽이 재발급**하고, 그 번호를 가리키는 태그를 전부 함께 고친다(`traceability`).

## 자동화

### 위험 명령 차단 — 켜는 것이 아니라 항상 돈다

flow를 설치하면 `guard-danger.sh`가 함께 붙는다. **되돌릴 수 없는 명령을 실행 전에 막는다** — 약속이 아니라 기계 장치다. 막히면 이렇게 보인다:

```
⛔ flow guard: 되돌릴 수 없는 명령이라 차단했습니다 — git push
   명령: git push

   push·merge는 사람이 외부 툴로 합니다(Sourcetree 등). 커밋까지는 /flow:commit 이 합니다.
   (CLAUDE.md 가드레일 · 이 훅은 Claude Code 세션에만 걸립니다)
```

| 막는 것 | 왜 |
|:--|:--|
| `git push` (force 포함) | 원격을 바꾼다. **사람이 외부 툴로** 한다 |
| `git merge` · `git rebase` · **`filter-branch`·`filter-repo`** | 이력을 다시 쓴다 |
| `git reset --hard` | 안 커밋한 작업이 사라진다 |
| `git clean -f` | 추적 안 되는 파일이 사라진다 |
| **`gh pr merge`·`release create`·`repo delete`** | GitHub 상태를 바꾼다 |
| **`gh api` 쓰기** — `-X`·`--method` · **필드 플래그**(`-f`·`-F`·`--field`·`--raw-field`·`--input`) · `graphql mutation` | 같음. **필드만 줘도 gh 가 POST 로 보낸다** |

| 통과하는 것 | 왜 |
|:--|:--|
| `git commit` · `add` · `status` · `diff` · `log` · `branch` · `checkout -b` | 되돌릴 수 있다 |
| `git reset HEAD~1` (`--hard` 없음) | 파일은 남는다 |
| `git clean -n` | 미리 보기만 한다 |

- **`git   push`·`git -C /repo push`·`npm test && git push`·여러 줄·`sudo git push`·`sh -c "git push"`도 막힌다** — 인용을 아는 스캐너로 세그먼트를 쪼개 본다.
- **안전 측으로 기울였다** — 세그먼트 안 어느 자리의 `git`·`gh`도 명령으로 본다. `echo git push`(인용 없이)도 막힌다. 인용하면 통과한다.
- **끄는 스위치는 없다.** 환경변수로 열어두면 AI가 그 변수를 설정해 통과한다.
- **사람이 push할 때는 안 걸린다** — Claude Code 세션 안의 명령만 본다. Sourcetree·터미널은 그대로 된다.
- **뚫리는 길이 있다** — `eval "git pu""sh"`·`P=push; git $P`·스크립트 파일에 써서 실행. 막으려면 셸을 해석해야 하는데 훅이 할 일이 아니다. **무심코 치는 것을 막는 장치**로 읽는다.
- **운영 MCP 쓰기는 기계로 막지 않는다** — 훅으로 만들어 봤지만 SQL 내용 판정이 양방향으로 계속 틀려 걷어냈다. **읽기 전용 계정으로 붙이는 것이 유일한 방어다** — `CLAUDE.md`의 `가드레일`에 있는 이름 규약과 함께.

### 드리프트 훅 — Claude 밖에서 커밋해도 잡는다

`/flow:setup`이 `drift-hook.sh`를 **`pre-commit`** 으로 넣는다. `.githooks/`에 두고 `core.hooksPath`를 가리키므로 **파일이 커밋되어 clone마다 다시 깔 필요가 없다.** Sourcetree·IDE·터미널 어디서 커밋하든 도는 **셸 스크립트**다 — AI를 부르지 않으니 느려지지 않는다.

**무엇을 보나**: 코드가 바뀌었는데 작업 문서(`doc/01.work/`)가 같이 안 바뀌었으면 어긋난 것으로 본다.

**무엇을 "코드"로 치나는 config가 정한다** — 순서대로 본다(정본은 `drift-check`).

| 순 | 규칙 | 기본값 |
|:--|:--|:--|
| ① | `drift.ignore`에 맞으면 **소스가 아니다** | `**/*.md` · `**/*.test.*` · `spike/**` |
| ② | **`drift.sourceGlobs`가 있으면 그 안만 소스** | `src/**` · `app/**` ← **배포 기본값이 채워져 나간다** |
| ③ | `sourceGlobs`가 **비어 있을 때만** — `doc/`·`spike/`·`.claude/`·`.github/` 밖이고 `.md`가 아닌 것 | — |

- **②가 기본으로 켜져 있다는 점을 놓치기 쉽다.** 배포되는 `workflow.config.json`엔 `sourceGlobs`가 채워져 있어 **`lib/`·`server/`는 안 잡힌다.** 프로젝트 구조가 다르면 `각 파일 조정`에서 그 글로브를 먼저 고친다.
- **`spike/`는 소스가 아니다** — 버릴 실험 코드라 드리프트 대상이 아니다.

**설정 키가 없다.** 깔면 켜지고 빼면 꺼진다.

| 상황 | 무엇이 일어나나 |
|:--|:--|
| 소스만 스테이징 | **커밋이 막힌다.** `/flow:sync` 후 다시 |
| 소스 + `doc/01.work/` | 통과 |
| **`doc/01.work/`에 유닛이 하나도 없다** | **통과** — 아직 체인을 안 쓰는 프로젝트다. 첫 유닛이 생기면 켜진다 |
| 작업 중이라 지금은 넘기고 싶다 | `git commit --no-verify` |

범위는 `drift.sourceGlobs`(볼 것)·`drift.ignore`(뺄 것)로 좁힌다. 레거시를 조금씩 들여올 때 쓴다.

**husky·lefthook을 쓰는 프로젝트는 자리가 다르다.** `core.hooksPath`가 이미 `.husky` 같은 폴더를 가리키면 `/flow:setup`이 **그 폴더에** 넣는다. 같은 이름 훅이 있으면 **덮지 않고** 호출 한 줄을 더할지 묻는다 — 덮으면 그 프로젝트의 lint·테스트 훅이 죽는다.

> **clone한 사람은 한 줄이 필요하다** — 훅 파일은 `.githooks/`에 있어 따라오지만 **`git config`는 clone마다 따로다.** 안 하면 파일이 있어도 훅이 안 돈다. 세션을 열면 `check-drift-hook.sh`가 알린다.
> ```bash
> git config core.hooksPath .githooks
> ```

### CI 게이트 — 건너뛸 수 없는 마지막 방어 (직접 켠다)

로컬 훅은 `git commit --no-verify`로 건너뛸 수 있다. PR에서 한 번 더 막으려면 GitHub Actions를 쓴다.

- `/flow:setup`이 씨앗 파일을 프로젝트에 복사해 둔다. **확장자만 벗기면 켜진다:**
  ```bash
  mv .github/workflows/drift-gate.yml.example .github/workflows/drift-gate.yml
  ```
- 코드가 바뀌었는데 **`doc/01.work/` 아래가 아무것도 안 바뀌었으면** PR이 실패한다(`2.task`·`3.contract`·`7.summary` 어느 것이든 인정). 막지 않고 알리기만 하려면 파일 안의 `process.exit(1)`을 `process.exit(0)`으로 바꾼다.
- **판정 규칙은 로컬 훅과 같다** — 정본은 `drift-check` 스킬이다. `workflow.config.json`의 `drift.sourceGlobs`·`drift.ignore`를 CI도 읽는다.
- (선택) PR에 리뷰 코멘트를 달려면 Actions에서 `claude -p "/flow:review 이 diff"`. **사람 없이 커밋하는 것은 금지** — 리포트·PR까지만.

## 자주 막히는 곳

| 증상 | 원인·해결 |
|:---|:---|
| 커맨드가 안 뜸 | 설치 스코프를 확인하고 `/reload-plugins` |
| 계약 검사가 안 돎 | ① `contract.gate`가 비었다 ② 고친 파일이 `contract.pathGlob` 경로 패턴과 안 맞는다 ③ (드물게) `node`·`python3`·`perl`이 모두 없다 — 이 셋 중 하나면 **조용히 통과**한다 |
| `/flow:commit`이 드리프트 경고 | 코드만 바뀌고 문서가 안 따라왔다 → `/flow:sync` 먼저. 문서가 필요 없는 변경이면 그대로 진행 |
| `/flow:build`가 엉뚱한 걸 잡음 | 대상을 직접 지정한다 — `/flow:build user/00.login` |
| `/flow:spec`이 거부한다 | 시스템·도메인 레벨엔 task·계약이 없다(`/flow:design`에서 끝난다). 기능을 만들려면 `/flow:prd func …`부터 |
| `/flow:run`이 중간에 멈춘다 | 게이트가 3번 막았거나 국면이 실패했다 → 리포트를 보고 그 단계를 손으로 고친 뒤 다시 실행 |

## 각 파일 조정

`/flow:setup`이 채운 것을 검수·수정할 때.

### `workflow.config.json` — 스택 주입

```jsonc
{
  "contract": {
    "pathGlob": "*/3.contract/*.ts",                             // 경로로 판정 — 파일명 아님
    "gate": "npx -y -p typescript tsc --noEmit --strict {file}"  // 스택에 맞게
  },
  "build":   { "command": "npm run build" },
  "test":    { "command": "npm test",                 // mvn test / pytest 등
               "browser": "playwright",               // playwright | chrome — 화면이 있으면 필수
               "headless": false },                   // 창을 띄운다 (사람이 보게)
  "drift":   {
               "sourceGlobs": ["src/**", "app/**"], "ignore": ["**/*.md", "**/*.test.*", "spike/**"] },
  "review":  { "severity": "critical" },
  "publish": { "target": "notion", "notionParent": "" },
  "theme":   { "source": "", "stack": "", "targetPath": "" },   // 비우면 doc/00.ref/04.theme/ 자동 인식
  "language": "korean"
}
```

**키 레퍼런스**:

| 키 | 의미 | 예 |
|:---|:---|:---|
| **`contract.pathGlob`** | 계약 파일 판정 — **경로 전체**로 본다 | `*/3.contract/*.ts` · `*/3.contract/*.java` |
| `contract.gate` | 계약 검증 명령 (`{file}` 치환) | `tsc --noEmit --strict {file}` |
| `test.command` | 테스트 명령 | `npm test` / `./gradlew test` / `pytest` |
| **`test.browser`** | 화면 테스트 모드 — **화면이 있으면 둘 중 하나 필수** | `playwright`(기본) · `chrome` |
| `test.headless` | 창을 띄우지 않을지 | `false`(기본 — 띄운다) |
| `build.command` | 빌드 명령 | `npm run build` |
| **`drift.sourceGlobs`** | **무엇을 소스로 치나** — 채워져 있으면 **그 안만** 본다 (`자동화` ②) | `src/**`·`app/**` → 구조가 다르면 **먼저 고친다** |
| `drift.ignore` | 소스에서 뺄 것 | `**/*.md`·`**/*.test.*`·`spike/**` |
| `review.severity` | 리뷰 하드 차단 임계 | `critical`(기본) |
| `publish.target` | 발행처 | `notion`·`docx`·`markdown` |
| `theme.*` | 테마 입력 — `source`를 비우면 `00.ref/04.theme/`를 쓴다 | 스펙 파일·프론트 스택·적용 경로 |
| `language` | 산출물 언어 | `korean`(기본) |

> JSON 파싱은 프로젝트 런타임(`node`·`python3`·`perl` 중 하나)이 한다 — 별도 설치 불필요.

**주의**:

- **`contract.pathGlob`을 파일명 패턴으로 두지 않는다.** 계약 이름은 `{도메인}.ts`라 도메인마다 다르다 — `api-contract.ts`처럼 고정 파일명을 쓰면 **훅이 못 잡고 조용히 통과**한다(`contract-gate`).
- **`gate`에 `npx`를 쓰면 네트워크에 매인다.** 사내망·오프라인이면 로컬 설치로 바꾼다 — `./node_modules/.bin/tsc --noEmit --strict {file}`.
- `tsc` 7 + `tsconfig.json`이 있으면 `{file}` 인자가 `TS5112` → `contract.gate`에 `--ignoreConfig` 추가.
- `node --test`는 디렉터리 대신 glob 필요 → `node --test 'tests/*.test.ts'`.

### `CLAUDE.md` — 프로젝트 정체성·가드레일

- `{{placeholder}}`를 실제 값으로 채운다.
- **작게 유지** — 매 턴 컨텍스트에 실리는 유일한 파일. 스택·네이밍·금지사항·MCP 정책 등 **프로젝트 고유만**.
- 범용 워크플로우·일반 코딩 룰은 넣지 않는다 (플러그인이 이미 가짐).
- 새 규칙 전 기존 규칙을 압축·삭제부터. 유지보수 안내도 본문에 두지 않는다 (매 턴 토큰).

### `doc/00.ref/` — 참조 정본

**정본이라 아무 커맨드나 못 고친다.** 폴더마다 고치는 주체가 정해져 있다.

| 폴더 | 무엇 | 누가 고치나 |
|:--|:--|:--|
| `00.architecture/` | **시스템 요구**(`SYS-*`) + 기술 구조·크로스커팅 제약 + **화면 지도**(`SCR-N` 발급) | `/flow:prd sys`(요구) · `/flow:design sys`(그 외) |
| `01.domain/` | **도메인 요구** + 경계·용어집(`00.common.md`) | `/flow:prd domain`(요구) · `/flow:design domain`(경계·용어·흐름) |
| `02.db-schema/` | 지금 상태의 DDL (BE 프로젝트) | 마이그레이션과 **같은 커밋**에 사람이 |
| `03.templates/` | 단계별 산출물 템플릿 | 사람 — 프로젝트 규약을 바꿀 때 |
| `04.theme/` | 테마 스펙 정본 (`/flow:theme` 입력) | 스펙은 **사람이 승인** · 매핑 기록은 `/flow:theme` |
| `05.explainer/` | 신규 인력용 설명 노트 — **왜 이렇게 돼 있나** | 요청할 때 `ops-doc`(`/flow:review`가 비어 있으면 권한다) |

- **요구·설계·화면 지도는 손으로 고치지 않는다** — `SYS-*`·`D-N`·`SCR-N`을 가리키는 태그가 여러 문서에 흩어져 있어 같이 안 바뀐다. 커맨드를 지나면 `sync`가 대조한다.
- 유닛 산출물(`01.work/`)은 여기 없다 — 그건 각 유닛 폴더가 갖는다.
