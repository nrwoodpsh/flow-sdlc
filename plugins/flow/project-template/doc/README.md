# doc — 요구·설계·기록 (기능별 IA)

한 작업의 전 과정(요구→설계→명세→구현→검증→리뷰→요약)을 한 폴더(work-unit)에 모은다.
**이 파일이 doc 구조의 단일 정본**이다 — 전체 트리·규칙이 여기 하나에 있다.

## 처음 왔으면 이 순서로 읽는다

**구조를 아는 것과 프로젝트를 아는 것은 다르다.** 아래는 **추상 → 구체** 순이다. 각 단계에서 멈춰도 그만큼은 안다.

| 순 | 무엇 | 알게 되는 것 |
|:--|:--|:--|
| 1 | 루트 [`README.md`](../README.md) | 이 프로젝트가 무엇인가 · 스택 |
| 2 | [`CLAUDE.md`](../CLAUDE.md) `정체성`·`가드레일` | 도메인 목록 · **하지 말 것** |
| 3 | [`00.ref/01.domain/00.common.md`](00.ref/01.domain/00.common.md) | **용어** — 이걸 모르면 나머지가 안 읽힌다 |
| 4 | `00.ref/00.architecture/01.design.md` *(있으면)* | 배포 단위·도메인 매핑 · 의존 방향 · 화면 지도 |
| 5 | `00.ref/05.explainer/` *(있으면)* | **왜 이렇게 돼 있나** — 설명 노트 |
| 6 | [`02.decisions/README.md`](02.decisions/README.md) | 결정 목록 — 제목만 훑고 관련된 것만 열어본다 |
| 7 | 담당 도메인 `00.ref/01.domain/{도메인}.md` | 경계·업무 규칙(`DR`)·유닛 계획 |
| 8 | 담당 유닛 `01.work/{도메인}/{유닛}/README.md` | 그 유닛의 요구→검증 사슬 |

- **1~3은 반드시 읽는다.** 나머지는 있는 것만·맡은 일에 따라.
- **없는 것도 정보다.**

| 없으면 | 뜻 |
|:--|:--|
| 4 `01.design.md` | 시스템 설계를 아직 안 했다 — 단일 도메인 소규모면 정상이다 |
| 5 `05.explainer/` | 설명 노트가 없다. **결정이 쌓였는데 비어 있으면 만들 시점**이다(`ops-doc`) |
| 7 유닛 계획 | 그 도메인은 아직 역추출·요구만 있다 |

- **`03.templates/`는 읽지 않는다** — 문서를 쓸 때 참조하는 골격이고, 읽어서 프로젝트를 알게 되는 것이 아니다.
- 전체 트리·규칙은 이 파일 아래에 있다.

## 폴더 역할

| 폴더 | 역할 | 소유 |
|:--|:--|:--|
| `00.ref/` | 전역 기반 지식(요구·아키텍처·도메인·DB·패턴) | 사람 (확정) |
| `01.work/` | 기능 산출물 — `{도메인}/{유닛}/` 사슬 | 커맨드 (출력) |
| `02.decisions/` | 전역 ADR (유일 결정 로그) | 커맨드 |
| `03.integration/` | 통합테스트 (브랜치·프로젝트 조합) | 커맨드 |
| `04.ops/` | 운영 문서 — 장애 회고·운영 절차 | 사람 (AI가 초안) |

## repo가 여럿일 때 — `doc/`는 한 곳에 모은다

**코드는 repo가 갈려도 `doc/`는 하나다.** 흩어지면 추적이 끊긴다 — 요구 ID로 grep해 역인덱스를 만드는 방식(`traceability`)이 repo 경계를 못 넘는다.

| 구성 | 코드 | `doc/` |
|:--|:--|:--|
| **모노repo** (기본) | repo 하나에 서비스 여럿 | 그 repo 루트 |
| **repo per service** | 서비스마다 repo | **주 repo 하나** 또는 **별도 doc repo** — 어디든 **한 곳** |
| 하이브리드 | 일부만 분리 | 같음 |

- **`01.work/{도메인}/`은 도메인 단위다** — repo가 서비스 단위여도 도메인으로 묶는다. 한 도메인이 두 repo에 걸치면 그건 도메인 경계를 다시 볼 신호다.
- **계약(`3.contract/`)도 `doc/`에 있다.** 다른 repo의 서비스가 그걸 보려면 **`doc/`를 서브모듈로 붙이거나 사본을 받는다** — 어느 쪽이든 정본은 `doc/` 하나다.
- **`03.integration/`은 서비스를 넘는 테스트를 담는다** — 그래서 `doc/`가 서비스마다 갈리면 둘 곳이 없어진다.
- **repo 경로는 `File Map`에 적는다** — `[Mod] order-svc:src/OrderService.java`처럼 repo를 앞에 붙인다. 배포 단위와 repo의 매핑은 `13.architecture` 구성 요소 표에 있다.

**repo가 갈리면 이것들이 안 된다** — 정직하게 적어둔다.

| 못 하는 것 | 왜 | 대신 |
|:--|:--|:--|
| **드리프트가 repo를 넘는 변경을 잡기** | `git diff`가 한 repo만 본다 | 계약에 `서비스 간`·`외부 제공` 표기 → 커밋 때 알린다 (`drift-check`). **막지는 못한다** — 상대 repo를 우리가 모른다 |
| **`code-graph`가 서비스 간 호출을 추적하기** | HTTP는 코드가 아니다 | 계약을 축으로 역인덱스 (`code-graph`) |

## 레벨 — 어디에 쓰이나

요구·설계는 **레벨에 따라 착지처가 다르다**. 규약 정본은 `traceability` 스킬.

| 레벨 | 요구 (`/flow:prd`) | 설계 (`/flow:design`) | 이후 |
|:--|:--|:--|:--|
| **시스템** (횡단·기술 구조) | `00.ref/00.architecture/00.requirement.md` | `…/01.design.md` | **정지** |
| **도메인** (한 도메인) | `00.ref/01.domain/{도메인}.md` §요구 | 같은 파일 §경계·용어 | **정지** |
| **기능** (work-unit) | `01.work/{도메인}/{NN.유닛}/0.requirement.md` | `…/1.design.md` + `2.task`·`3.contract` | `/flow:build`→`/flow:verify`→… |

- 시스템·도메인은 **구현 없이 ref 정본으로 착지**한다.
- 요구는 `requirement`, 설계는 `design` — 레벨이 달라도 이름은 같다.

## 단위 정의

- **domain** = 주(主) 컨트롤러명. 폴더, **번호 없음** (코드 매핑 안정).
- **work-unit** = 한 요구가 낳는 인과 사슬(요구→설계→task→계약→build→verify→review→summary). 폴더, `NN.`. 사람·AI가 함께 읽는 원자 단위.
- **branch**(업무 지시) = 색인 태그. `01.work` 안에선 폴더 아님 — `01.work/README`가 git 분석으로 브랜치별로 유닛을 묶어 링크. (폴더로 쓰는 곳은 통합테스트 `03.integration/00.branch/`뿐.)
- **다중 컨트롤러** = 한 브랜치가 여러 도메인 유닛을 낳으면 상단 인덱스가 그 브랜치 아래 함께 묶어 교차 도메인도 한눈에 드러난다.

## 전체 구조 (최하단까지)

```
doc/
├── README.md                    ← 이 파일 (구조 정본)
│
├── 00.ref/                      전역 기반 지식 · 사람 소유
│   ├── README.md                ← ref 색인 (하위 폴더엔 README 없음)
│   ├── 00.architecture/         00.requirement.md(SYS-*) · 01.design.md(기술 구조·크로스 도메인 업무 흐름)
│   ├── 01.domain/               00.common.md(용어집) · {도메인}.md(§요구 · §경계·용어)
│   ├── 02.db-schema/            저장소 스키마 · 관계형 {table}.sql · 그래프 graph.cypher · 여럿이면 {저장소}/ 폴더
│   ├── 03.templates/            유닛 사슬 00.requirement~07.summary + 08.adr·09.domain·10.explainer·11.postmortem·12.sop-runbook·13.architecture·14.integration·15.theme
│   ├── 04.theme/                테마 스펙 정본 (theme-apply 스킬 입력 · 없으면 빈 폴더)
│   └── 05.explainer/            신규 인력용 설명 노트 · NN.{주제}.md      (빈 폴더)
│
├── 01.work/                     기능 산출물
│   ├── README.md                ← 상단 인덱스 (브랜치→유닛, /flow:sync가 git 분석해 자동생성)
│   └── {도메인}/{NN.유닛}/       예: user/00.login/
│       ├── README.md            ← 유닛 인덱스 (이 폴더 전체 목차, /flow:sync 자동)
│       ├── 0.requirement.md     요구 · ID+완료 기준 (/flow:prd)
│       ├── 1.design.md          설계도 · 분석+구조+D-N (/flow:design)
│       ├── 2.task/              task (스파인) · NN.name.md — frontmatter에 requirement·design 태그
│       ├── 3.contract/          계약 {도메인}.ts (유닛마다 · self-contained) · LLM이면 {도메인}.prompt.md
│       ├── 4.build/             구현 기록 · NN.name.md (task와 번호·이름 1:1)
│       ├── 5.verify/            단위테스트 · NN.name.md (task와 1:1)
│       ├── 6.review/            리뷰 · NN.내용.YYYYMMDD.md (유닛 회차)
│       └── 7.summary/           요약 · NN.내용.YYYYMMDD.md (유닛 회차)
│
├── 02.decisions/                전역 ADR
│   ├── README.md                ← ADR 인덱스 (/flow:sync 자동)
│   └── NN.내용.YYYYMMDD.md
│
├── 03.integration/              통합테스트
│   ├── README.md                ← 통합 인덱스 (/flow:sync 자동)
│   ├── 00.branch/{브랜치}/       브랜치 통합 (머지 전) · NN.내용.YYYYMMDD.md
│   │                            브랜치 이름의 `/`는 `-`로 (feature/login → feature-login)
│   └── 01.project/              프로젝트 E2E + 요구 gap 리포트 · NN.내용.YYYYMMDD.md
│
└── 04.ops/                      운영
    ├── README.md                ← 운영 인덱스 (/flow:sync 자동)
    └── NN.내용.YYYYMMDD.md       장애 회고(11.postmortem) · 운영 절차(12.sop-runbook)

(코드는 doc 아님: 실제 코드 src/ · 테스트 tests/scenarios/ · 버릴 검증 코드 spike/ — 주제별 하위 폴더는 `/flow:spike`가 만든다)
```

## 핵심 규칙

- **전면 0-기반 넘버링**: 모든 `NN.`은 `00.`부터. 단계 번호는 1자리(`0.requirement`~`7.summary`), 목록 안 파일은 2자리(`00.`).
- **구분자**: `.` = 번호↔이름(및 날짜 앞), `-` = 이름 안 단어 (`00.error-handling`).
- **이름은 짧게** — 도메인·유닛 이름이 곧 요구 ID가 된다(`shorts/00.script-gen` → `SHORTS-SCRIPT-GEN-1`). 한 단어 권장, 두 단어까지. 서술형 금지.
- **번호 예외**: `README.md`(무번호·하단) · 계약 `{도메인}.ts`(도메인명) · 도메인 요구 `01.domain/{도메인}.md`(도메인명 — `01.work/{도메인}/`과 표기를 맞춘다) · db-schema(저장소가 정하는 이름 — 테이블·라벨·컬렉션. `00.ref/README`가 인덱스).
- **task 스파인 1:1**: `2.task/NN.name`→`4.build/NN.name`→`5.verify/NN.name` (번호·이름 물려받음). 계약은 공유 → task 문서 "사용 계약" 표로 추적.
- **추적 태그**: 요구 ID(전역)·설계 요소 `D-N`(문서 내 로컬)만 발급한다. task 이하는 **파일 경로가 곧 ID** — 별도 번호를 만들지 않는다. 태그는 `2.task/` frontmatter(`requirement:`·`design:`)에.
- **계약 소비**: 코드는 `3.contract/`의 계약을 **직접 import**한다(경로 길면 path alias 권장). **유닛 폴더명은 바꾸지 않는다** — 폴더명이 ID의 일부라 태그·스파인·import가 전부 걸린다(`traceability`).
- **날짜 파일명 `NN.내용.YYYYMMDD.md`**: `6.review`·`7.summary`·`02.decisions`·`03.integration`·`04.ops`(회차·시간성). 요구·설계·task는 날짜 없음(번호가 순서).
- **`0.requirement`·`1.design`만 파일**(유닛당 1). 나머지 단계는 폴더.
- **폴더는 셋업 때 일괄 생성** (빈 폴더 유지). **산출물 파일**은 작업하며 채움. 재실행은 in-place(변경은 문서 안 History), 새 산출물은 새 번호.

## README 체계 (이 doc 안 README는 이게 전부)

- **셋업 생성**: `doc/README`(이 파일)·`00.ref/README`(ref 색인) + 영역 인덱스 — `01.work`·`02.decisions`·`03.integration`·`04.ops`의 `README`(처음엔 플레이스홀더).
- **`/flow:sync`가 채움·갱신**: 영역 인덱스를 git 분석으로 채우고(브랜치→유닛·목록), 유닛별 `README`(폴더 목차)를 생성. 도메인 요구 파일(`00.ref/01.domain/*`)엔 하위 기능 색인을 갱신해 **단일 뷰**를 만든다.
- **라벨 README 없음**: "이 폴더는 X"는 이 파일이 대신한다.
- **정렬**: README는 무번호라 번호 형제 아래(하단). 형제도 무번호인 `01.work`에선 상단 무방(전체 지도).
- 충돌 안전: 유닛 README는 그 유닛 담당자 1명만, 상단은 git에서 자동 재생성.
- **색인이 머지 충돌하면 손으로 풀지 않는다** — 한쪽을 취하고 `/flow:sync`를 다시 돌린다(계산된 것이라 다시 맞는다). 사람이 쓴 문서(요구·설계·task·ADR)는 정상적으로 머지한다.

**색인이 커지면 최근 것만 남긴다.** 색인은 읽히려고 있는 것이라, 다 담으면 읽히지 않는다.

| 색인 | 자라는 축 | 커졌을 때 |
|:--|:--|:--|
| `01.work/README` | **브랜치→유닛** | **머지된 브랜치는 접는다** — 최근 것만 펼치고 나머지는 `이전 이력` 한 줄로. 브랜치 축은 시간이 지나면 뜻이 없어진다 |
| `02.decisions/README` | ADR 목록 | **주제별로 절을 나눈다** — 목록이 길면 제목만 훑어도 안 읽힌다 |
| 도메인 `하위 기능` | 그 도메인 유닛 | 도메인 단위라 자연히 나뉘어 있다 — 그대로 |

- **도메인→유닛은 도메인 파일이 갖는다** — `01.work/README`와 축이 다르다(브랜치 vs 도메인). 둘을 합치지 않는다.
- **접는 판정은 `/flow:sync`가 한다** — 손으로 정하지 않는다.
