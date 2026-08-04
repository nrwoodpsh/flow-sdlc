# flow-sdlc

**요구 사항부터 커밋 전까지를 하나의 흐름으로 잇는다.** 개발 라이프사이클 오케스트레이터를 Claude Code 플러그인 `flow`로 제공한다.

[![flow](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnrwoodpsh%2Fflow-sdlc%2Fmain%2F.claude-plugin%2Fmarketplace.json&query=%24.plugins%5B0%5D.version&style=flat-square&color=111111&label=flow)](.claude-plugin/marketplace.json)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-111111?style=flat-square)](https://code.claude.com)
[![License](https://img.shields.io/badge/license-MIT-111111?style=flat-square)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-%ED%95%9C%EA%B5%AD%EC%96%B4-111111?style=flat-square)](guide/getting-started.md)

```
(spike) → prd → design → spec → build ⇄ verify → review → sync → commit
```

| | |
|:--|:--|
| **쓰는 법** | [`guide/getting-started.md`](guide/getting-started.md) — 설치·사용법·커맨드·설정 |
| **고치는 법** | [`CLAUDE.md`](CLAUDE.md) — 정체성·워크플로우·가드레일. 플러그인 파일 규약은 `.claude/rules/plugin-authoring.md` |
| **커맨드 상세** | [`plugins/flow/commands/`](plugins/flow/commands/) — **파일이 정본이다** |

## 왜 만들었나

AI에게 코딩을 맡기면 세 가지가 걸린다. 이 셋을 틀로 통제하는 것이 flow다.

| 제약 | 무엇이 문제인가 | 어떻게 통제하나 |
|:--|:--|:--|
| **컨텍스트 한계** | 큰 코드베이스를 다 못 읽는다 | 참조 통제(무엇을 읽을지 미리 정함) + 무거운 탐색은 별도 창(`explorer`)에 격리 |
| **환각** | 그럴듯한데 틀린 것을 만든다 | **이중 게이트** — 자연어는 사람이, 계약(타입)은 기계가 검증 |
| **자기 검증 편향** | 자기가 놓친 것은 검증에서도 놓친다 | 검증을 **작업자와 분리**(`gatekeeper`·`verifier`) |

### 진입은 유연, 퇴장은 하나

변경의 대부분은 작다. 전부 `/flow:prd`부터 강요하면 **사람이 flow를 우회하고**, 우회하면 문서가 코드와 어긋난다.

| | 언제 | 경로 |
|:--|:--|:--|
| 전체 | 신제품·큰 기능 | `prd → design → spec → build → …` |
| **붕괴** | 작은 변경·버그 | **`design`부터** — 요구를 자동 발급하고 질문을 줄인다 |
| 면제 | **오타·문구만** | flow 밖에서 그냥 고친다. **유일한 면제다** |

코드 변경은 어느 경로로 왔든 `/flow:sync` 하나로 모인다.

### 요구 ID가 축이다

테스트가 다 통과해도 *"요구를 다 덮었나"* 는 알 수 없다. 통과 목록에는 **애초에 테스트가 없는 요구가 나타나지 않기** 때문이다.

```
요구(ID 발급) → 설계 요소(D-N) → task → 구현 → 검증
                      ↑ 태그로 잇고, /flow:verify project 가 대조해 gap 을 낸다
```

- **레벨이 깊이를 정한다** — 시스템·도메인 요구는 `design`에서 멈춰 `00.ref/` 정본이 되고, 기능 요구만 구현까지 간다.
- 태그는 **직접 충족한 것만**. 부모는 전이로 따라간다 — 중복 기입이 드리프트를 만든다.

### 문서 드리프트를 4겹으로 막는다

코드만 바꾸고 문서를 안 맞추면 **AI가 낡은 문서를 진실로 믿는다.**

| 층 | 언제 | 무엇 |
|:--|:--|:--|
| `/flow:sync` | 코드를 고친 뒤 | 유일 퇴장구 — 변경을 문서에 반영 |
| `/flow:commit` | 커밋 전 | 불일치를 **사람에게 알린다.** 판단은 사람이 |
| **git 훅** | **커밋 전** | **Claude 밖 커밋(Sourcetree·IDE)을 막는다** — 위 둘이 안 도는 그 경우다 |
| **CI 게이트** | PR | **머지를 막는다** — 켜면 `--no-verify` 우회가 안 통한다 |

**가운데 둘은 같은 시점을 다른 경로로 지킨다.** Claude로 커밋하면 `/flow:commit`이 묻고, 밖에서 커밋하면 git 훅이 막는다. CI만 옵트인이다.

### 되돌릴 수 없는 것은 약속으로 두지 않는다

**AI가 어기면 아무것도 안 막는 규칙은 규칙이 아니다.**

| | 어떤 것이 | 왜 이쪽인가 |
|:--|:--|:--|
| **기계 장치** | 되돌릴 수 없는 git 명령 · 드리프트 | 판정이 **결정론**이라 훅으로 쓸 수 있다 |
| **약속** | 자동 커밋 · 테스트 약화 · 계약 검증 · **운영 MCP 쓰기** | 판정이 맥락에 달렸거나 **커맨드 절차 안에 있어** 훅이 설 자리가 없다 |

- **우회 수단을 두지 않는다.** 환경변수로 열어두면 **AI가 그 변수를 설정해 통과한다.**
- **막는 범위를 부풀리지 않는다.** flow 훅(`guard-danger`)은 Bash 도구만 본다 — `eval`이나 다른 도구로는 뚫린다. **무심코 치는 것을 막는 장치**지 마음먹은 우회를 막지 못한다.
- **약속으로 남은 것은 구조로 줄인다** — 운영 MCP는 **읽기 전용 계정**으로 붙인다. 훅으로 막아 보려 했지만 **SQL 내용 판정이 양방향으로 계속 틀려** 걷어냈다.

### 통과 ≠ 정확

`tsc` 통과는 **컴파일만** 증명한다. 계약이 맞는지는 증명하지 않는다. 그래서 게이트가 통과해도 **자동 커밋을 하지 않고, 실패 시 자율 수정도 하지 않는다.**

무엇이 실제로 막히고 무엇이 약속인지는 **프로젝트 `CLAUDE.md`의 표**가 정본이다 — `/flow:setup`이 그 프로젝트에 깔아 준다.

## 저장소 구조

**폴더마다 성격이 다르다** — 어디를 고치면 무엇이 딸려 오는지가 여기서 갈린다.

```
flow-sdlc/
├── README.md                             이 문서 — 무엇·왜 + 구조
├── CLAUDE.md                             고치는 사람용 — 매 턴 실린다
├── guide/getting-started.md              쓰는 사람용 — 설치·사용법·커맨드·설정
│
├── .claude-plugin/marketplace.json       마켓 등록. 설치측이 **이 파일의 버전으로 캐시를 판단**한다
│
├── plugins/flow/                     ══ ① 플러그인 (설치되면 컨텍스트에 실린다) ══
│   ├── .claude-plugin/plugin.json        신분증 (name: flow → /flow: 접두). 버전은 위 파일과 **같아야** 한다
│   ├── commands/                         커맨드 — **부를 때만** 본문이 실린다
│   ├── agents/                           에이전트 — 본문은 **그 서브에이전트 창에서만**
│   ├── skills/                           스킬 — description 은 상시, 본문은 쓸 때만
│   ├── hooks/                        ── 셸 훅 (컨텍스트에 안 실린다 · 출력만)
│   │   ├── hooks.json                    이벤트 → 스크립트 매핑
│   │   └── scripts/
│   │       ├── guard-danger.sh           되돌릴 수 없는 git·gh 차단 (PreToolUse · exit 2)
│   │       └── check-drift-hook.sh       세션 시작 시 drift 훅이 도는지 확인
│   ├── git-hooks/drift-hook.sh           pre-commit — 소스만 커밋하면 막는다
│   ├── presets/                      ── setup 이 읽는 참조 (**매 턴 안 실린다**)
│   │   ├── architectures/                프로젝트 원형 — 복제해 시작
│   │   ├── tools/                        도구 추천 — 종류·설치·없을 때
│   │   └── template-sync.md              템플릿 동기화 절차 — **업데이트 모드에서만 읽는다**
│   └── project-template/             ── 새 프로젝트 씨앗 (**읽지 않고 복사**한다)
│       ├── CLAUDE.md                     **매 턴 실린다** — 작게 유지하는 것이 규칙. 절에 번호를 안 붙인다(밖에서 이름으로 가리킨다)
│       ├── workflow.config.json          스택 주입 (계약 게이트·테스트·빌드·drift)
│       ├── .claude/settings.json         팀원이 clone 하면 flow 자동 활성화
│       ├── .claude/rules/code-style.md   네이밍·폴더·테스트 — **소스 파일을 읽을 때만 실린다**(매 턴 아님)
│       ├── .github/workflows/            drift-gate.yml.example — PR 머지 차단 (기본 꺼짐)
│       ├── spike/                        버릴 검증 코드 (내용물 gitignore)
│       └── doc/                          아래 구조는 doc/README.md 가 정본
│           ├── 00.ref/                   **정본** — 폴더마다 고치는 커맨드가 정해져 있다
│           │   ├── 00.architecture/      시스템 요구(SYS-*)·구조·화면 지도  ← prd sys · design sys
│           │   ├── 01.domain/            도메인 요구·경계·용어·유닛 계획    ← prd domain · design domain
│           │   │   └── 00.common.md      공통 용어집 — design 전 필수 확인
│           │   ├── 02.db-schema/         지금 상태의 DDL — 마이그레이션과 **같은 커밋에** 갱신
│           │   ├── 03.templates/         산출물 골격 — **doc-verify 의 채점 기준**
│           │   │   └── VERSION           복사 시점의 flow 버전 — setup 이 동기화 판정에 쓴다
│           │   ├── 04.theme/             테마 스펙 정본 (theme 입력)
│           │   └── 05.explainer/         신규 인력용 설명 노트 (ops-doc)
│           ├── 01.work/{도메인}/{NN.유닛}/   유닛 사슬 — **번호가 순서이고 1:1로 물린다**
│           │   ├── 0.requirement.md          요구·ID·완료 기준·측정 방법
│           │   ├── 1.design.md               분석·구조·화면·엣지 케이스·D-N
│           │   ├── 2.task/NN.md              실행 지시서 (Logic·File Map·Verification·History)
│           │   ├── 3.contract/{도메인}.ts    계약 — 유닛마다 self-contained
│           │   ├── 4.build/NN.md             구현 기록
│           │   ├── 5.verify/NN.md            테스트 명세·결과·결함
│           │   ├── 6.review/NN.…md           리뷰 회차
│           │   └── 7.summary/NN.…md          요약 + 발행 URL
│           ├── 02.decisions/             ADR — 채택·기각 둘 다 남긴다
│           ├── 03.integration/           브랜치 통합(머지 전) · 프로젝트 E2E + 요구 커버리지
│           └── 04.ops/                   장애 회고·운영 절차 (ops-doc)
│
└── scripts/                          ══ ② repo 운영 (플러그인에 안 들어간다) ══
    ├── bump-version.sh                   두 매니페스트를 함께 올린다 — 올리기 전후로 대조한다
    ├── lint-docs.py                      문서 정합 검사 — **문서를 고쳤으면 돌린다**
    └── tests/hooks.test.sh               훅 검증 — **훅을 고쳤으면 돌린다**
```

**여기서 읽을 것 하나** — `doc/` 전체 구조와 규칙의 정본은 `plugins/flow/project-template/doc/README.md`다. 이 트리는 요약이다.

## 라이선스

[MIT](LICENSE) · 2026 park seung hyun
