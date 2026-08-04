---
name: default-reference
description: 커맨드별로 무엇을 자동 참조하고 무엇을 서브에이전트에 위임하나 — 컨텍스트 예산의 정본. 모든 커맨드가 쓴다.
---

# 기본 참조 관리

Claude Code는 자동 RAG 인덱싱이 없다. 파일 참조는 항상 명시적이어야 한다. 이 스킬은 커맨드별 "항상 로드할 표준 컨텍스트"와 "자동으로 읽지 말 경로"를 일관되게 적용한다. 사용자 `[REFERENCE]`는 기본값에 **추가**된다(덮어쓰지 않는다).

## 커맨드별 기본 참조

| 커맨드 | 자동 로드 | 템플릿 (`00.ref/03.templates/`) |
|:---|:---|:---|
| `/flow:ask` | `CLAUDE.md` + `00.ref/` 인덱스만 (본문 로드 안 함 — 판별에 충분). 세팅 여부는 `CLAUDE.md`·`workflow.config.json`·`doc/` 존재로 판단 | 없음 — 판별만 한다. 문서를 쓰게 되면 `ops-doc`이 제 템플릿을 연다 |
| `/flow:setup` | 스택 지표(`package.json`·`build.gradle`…) + 기존 `CLAUDE.md`(있으면) + `presets/`(원형·도구 카탈로그) | **복사 원본** `${CLAUDE_PLUGIN_ROOT}/project-template/` 전체 — 읽어서 쓰는 게 아니라 그대로 옮긴다 |
| `/flow:prd` | `CLAUDE.md` + 상위 요구(`00.ref/00.architecture/00.requirement.md`·`01.domain/`) + 사용자 지정 `[REFERENCE]` | 레벨별 — `sys`→`13.architecture` · `domain`→`09.domain` · `func`→`00.requirement` (규약은 `usecase` 스킬) |
| `/flow:spike` | `CLAUDE.md` + 관련 `00.ref/` | `08.adr` (판정을 ADR로 남길 때) |
| `/flow:design` | `CLAUDE.md` + 대상 `0.requirement.md` + `00.ref/01.domain/` + `00.ref/00.architecture/` + `02.decisions/` | 레벨별 — `sys`→`13.architecture` · `domain`→`09.domain` · `func`→`01.design` · +`08.adr` |
| `/flow:spec` | `CLAUDE.md` + 대상 `1.design.md` + 기존 `3.contract/` | `02.task-doc` · `03.api-contract` |
| `/flow:build` | `CLAUDE.md` + 대상 work-unit의 `2.task/` + `3.contract/` + **`1.design.md`의 `엣지 케이스`·`화면 구조`** | `04.build` · `05.verify`(루프 테스트 기록) |
| `/flow:verify` | `CLAUDE.md` + 대상 `2.task/` + `3.contract/` + 기존 `5.verify/` (`project`는 요구 등록소도) | `unit`→`05.verify` · `branch`·`project`→`14.integration` |
| `/flow:review` | `CLAUDE.md` + 대상 `2.task/`·`3.contract/` + 변경 소스 + 기존 `6.review/` (`doc`이면 대상 문서) | `06.review` · **`doc`이면 대상 문서에 해당하는 템플릿** |
| `/flow:sync` | `CLAUDE.md` + `git diff` + 대상 work-unit의 `2.task/`·`3.contract/`·기존 `7.summary/` + 영역 인덱스 README | `07.summary` · `08.adr`(결정 시) |
| `/flow:commit` | `git status`·`git diff --stat` + `CLAUDE.md`의 `Git 규약`·`가드레일` | 없음 |
| `/flow:theme` | `CLAUDE.md` + `00.ref/04.theme/`(기존 스펙·매핑) + `workflow.config.json`의 `theme.*` + 프론트 진입점·스타일 파일 | `15.theme` |
| `/flow:run` | 첫 국면의 기본값만 먼저 읽는다 — 나머지는 **각 국면이 자기 차례에** 로드한다(체인 전체를 미리 읽지 않는다) | 없음 — 국면이 자기 것을 쓴다 |
| `/flow:publish` | **`00.ref/01.domain/00.common.md`(용어 — 필수)** + 대상 유닛의 `0.requirement`·`1.design`·`2.task/`·`3.contract/`·`5.verify/`·`7.summary/` + `02.decisions/`·`03.integration/` + **범위가 `project`면 `00.ref/` 전부** + `workflow.config.json`의 `publish.*` | 없음 — 있는 산출물을 옮긴다 |

**글을 쓰는 커맨드는 `plain-writing`을 쓴다 — 기본값이다.** 안 쓰는 것은 셋뿐이다.

| 커맨드 | 왜 안 쓰나 |
|:--|:--|
| `/flow:ask` | 판별만 한다 — 글을 쓰면 그건 `ops-doc` 쪽이다 |
| `/flow:commit` | git 조작이다 |
| `/flow:run` | 오케스트레이션이다 — 글은 각 국면이 쓴다 |

- 그 밖은 전부 쓴다. **템플릿이 없는 `setup`·`publish`도 쓴다** — `CLAUDE.md`·발행문이 사람이 읽는 글이다.
- **커맨드의 `## 연결`에 적는 것이 기제다.** 여기 적은 것은 새 커맨드가 빠뜨렸을 때의 근거고, 어긋나는 것은 검사가 막는다.

> **템플릿은 필요한 것만 읽는다.** `03.templates/`를 폴더 통째로 읽지 않는다 — 전부 읽으면 대부분이 낭비다. 레벨은 `traceability`로 먼저 판별한 뒤 해당 템플릿만 연다.

**`/flow:build`가 `1.design.md`을 읽는 이유** — task는 **설계 결정·화면을 복사하지 않고 ID로 가리킨다**(`spec`). 가리키는 쪽을 안 열면 `엣지 케이스`가 구현·테스트에서 함께 빠진다.

- **필요한 절만 읽는다** — `엣지 케이스`·(FE면)`화면 구조`. 분석·데이터 구조는 `spec`이 이미 소화했다.
- **유닛 안이라 위임하지 않는다**(아래 위임 판정 ②).

> "자동 로드"는 **인덱스 우선**이다. `00.ref/00.architecture`·`02.db-schema`의 큰 본문은 인덱스(README)만 훑고, 필요한 파일만 `@` 또는 `explorer`로 선택 로드한다 (트래픽 절약).

**인덱스가 없는 정본이 하나 있다 — 용어집(`00.common.md`).** 통째로 읽거나 안 읽는다.

| | |
|:--|:--|
| `/flow:design` 전 확인 | **필수**(`CLAUDE.md`의 `참조 통제`) — 용어를 모르면 설계가 어긋난다 |
| 커지면 | **공유하는 것만 남긴다** — 도메인 전용 용어는 그 도메인 파일로. 규칙은 `00.common.md` 안에 |

- **용어집이 길어지면 매 `design`이 그 비용을 낸다.** 절을 나누는 것으로는 줄지 않는다 — **양을 줄여야** 한다.

## 항상 참조 금지 (자동 로드 안 함)

필요 시 사용자가 `@`로 명시 주입한다.

- `doc/01.work/{작업 중이 아닌 타 도메인}/`
- `spike/` — 버릴 실험 코드

> `7.summary/`·`02.decisions/`는 참조 허용 — 이력·결정 맥락이 필요할 때 명시 주입 가능.

## 위임 판정 (정본)

**"많으면·넓으면 위임"은 판단이 흔들린다.** 판정을 둘로 고정한다 — 이 규칙을 `sync`·`review`·`publish`·`impact-analysis`가 함께 쓴다.

### ① 무엇이 필요한가

| 필요한 것 | 어떻게 |
|:--|:--|
| **결론만** — "무엇이 있나"·"어디에 속하나"·"몇 건인가" | **`explorer`에 위임** |
| **원문** — 그 값을 그대로 태그·복사·대조해야 한다 | **직접 읽는다** |

```
sync 가 diff에서 유닛을 가른다        → "이 파일은 이 유닛"  결론만  → 위임
design 이 요구를 읽어 D-N에 태그한다   → 요구 ID·완료 기준 원문 필요   → 직접
review doc 이 문서를 채점한다         → FAIL 목록만          결론만  → 위임
build 이 task를 읽어 구현한다         → Logic·File Map 원문 필요     → 직접
```

### ② 범위가 유닛을 넘나

원문이 필요해도 **양이 많으면** 위임한다. 기준은 **유닛**이다 — 우리 격리 단위다.

| 범위 | 어떻게 |
|:--|:--|
| **한 유닛 안** | 직접 읽는다 — 유닛 사슬 전체가 한 작업 단위다 |
| **유닛을 넘는다** (유닛 여럿·도메인 전체·`project`) | **위임한다** |

- **둘 다 걸리면 위임이 이긴다** — 원문이 필요하고 범위가 넓으면, `explorer`가 **필요한 부분만 인용해** 돌려준다.
- **`explorer`는 인용도 한다** — "결론만"이 요약만을 뜻하지 않는다. 원문 조각이 필요하면 그 조각을 받는다.
- **숫자 임계를 두지 않는다** — "파일 5개"는 튜닝 대상이 되고 상황마다 다르다. **유닛 경계**가 안정된 기준이다.

## 경계

- **`@` 파일 주입은 한 턴에 최대 5개.** 단일 파일 500줄 초과 시 분할 검토.
- **위임 판정은 위 규칙을 따른다** — "많으면·넓으면"으로 각자 판단하지 않는다.
- **참조 금지 경로를 자동으로 읽지 않는다.** 필요하면 사용자가 `@`로 명시 주입한다.
- **사용자 `[REFERENCE]`가 기본값을 덮지 않는다** — 더한다.
