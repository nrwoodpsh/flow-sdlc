# 재설계 인벤토리 W2 — 스킬 · 조각 층

대상은 `plugins/flow/skills/*/SKILL.md` 14개 · `references/*.md` 35개 · `doc/02.skills-map.md` 다.
읽기만 했다. `python3 scripts/lint.py` 는 이 파일을 더한 뒤에도 **검사 26 · 통과 26** 이다.

소비자는 `flow.topology.json` 의 `commands.*.loads`·`agents.*.fragments` 로 셌다 — 지도와 어긋나는 곳은 아래 `중복과 공백` 에 적었다.

## 스킬 14개

등급은 `flow.topology.json` 의 `skills.*.grade` 다.

| 스킬 | 무엇의 정본 | 등급 | 누가 싣나 | 없으면 무엇이 틀리나 |
|:--|:--|:--|:--|:--|
| `traceability` | 요구 ID · 레벨 · 태그 · gap · 유닛 상태 | 호출-전용 | `next`·`prd`·`design`·`build`·`verify`·`review`·`sync` | 추적 축이 사라진다. 기계 게이트가 읽는 `requirement:` 태그의 정본이 여기라 **게이트가 판정 근거를 잃는다** |
| `testing` | 테스트 명세와 실행 판정 | 호출-전용 | `build`·`verify`·`spike`·`review` · `verifier` | 추론이 검증으로 통과한다. 기대값을 코드에서 역산해도 아무 표시가 안 남는다 |
| `code-review` | 리뷰 층 · 등급 · 체크리스트 | 호출-전용 | `build`·`review`·`commit`·`next` · `reviewer` | `critical` 의 뜻과 하드 차단 경계가 없어져 `gatekeeper`·`commit` 이 무엇을 막을지 모른다 |
| `code-graph` | 그래프 질의 · 서비스 경계 | 호출-전용 | `design`·`build`(조건)·`review`·`commit` · `reviewer` | 교차 파일 영향이 파일 읽기로 내려간다. 축소 모드 결과를 그래프 분석으로 보고하는 길이 열린다 |
| `doc-verify` | 문서 채점 · 절 등급 · 값의 정본 지도 | 호출-전용 | `review`·`sync`·`design`(기능) · `gatekeeper` | `진행 필수`·`문서 필수` 의 차이가 없어져 `gatekeeper` 가 무엇으로 차단하는지 근거가 없다 |
| `doc-template` | 문서 골격 · 다이어그램 표기 | 호출-전용 | `prd`·`design`·`build`·`publish` | task 절 이름이 흔들린다. `File Map` 이 소스→유닛 매핑의 정본이라 **기계 게이트가 유닛을 못 찾는다** |
| `usecase` | 유스케이스 입도 · 규칙 레벨 · 표와 그림 분담 | 호출-전용 | `prd`·`design`(시스템·도메인)·`review` | 유스케이스가 엔드포인트 단위로 쪼개지고 업무 규칙이 여러 곳에 복사된다 — 경계값 테스트의 근거가 흩어진다 |
| `contract-gate` | 계약 컴파일 게이트 | 호출-전용 | `setup`·`design`·`build`·`sync` | 통과 기준이 사람 말로 돌아간다. `any` 로 덮어 통과시키는 길을 막는 문장이 없어진다 |
| `impact-analysis` | 회귀 표면 | 호출-전용 | `design`(기능)·`build`(조건) | 기존 코드를 고치기 전 전수 조사가 사라진다 — **레거시 변형의 핵심 산출물이 없다** |
| `drift-check` | 코드와 문서의 간격 판정 | 호출-전용 | `commit`·`sync` | 훅·CI 와 판정이 갈린다("로컬은 통과, CI 는 차단") |
| `default-reference` | 위임 판정 · 참조 금지 | 호출-전용 | `prd`·`design`·`build`·`verify`·`review`·`sync`·`publish` | 각자 "많으면 위임"으로 판단해 메인 컨텍스트가 터진다 |
| `ops-doc` | 운영 문서 + 운영 안전 규칙 | 자율 | `next`·`review` · 사용자 직접 | **`사람만` 단계를 AI 가 실행한다.** v1 이 라우팅 커맨드에 두었던 안전 규칙이 없어진다 |
| `theme-apply` | 테마 토큰 정본 · 적용 | 자율 | `design`(SKILL.md 만) · 사용자 직접 | 화면 설계가 토큰을 재정의해 정본이 둘이 된다 |
| `plain-writing` | 문장 · 구조 규칙 | 기본값 | 글을 쓰는 커맨드 전부 (`commit`·`next` 제외) | 지시서가 부풀고, 줄이다가 조건절·`안 본 것` 이 지워진다 |

## 조각 35개 — 성격 재판정

판정 규칙은 하나다. **산출물에 그 값이 그대로 나와야 하면 어휘형**이고, 값이 아니라 정하는 방법을 바꾸면 판단형이다.
설정 키 이름 · 절 이름 · 경로 형식 · 표기 문자열도 닫힌 값이다 — 여기서 앞선 휴리스틱과 갈렸다.

**결과는 어휘형 21 · 판단형 14** 다. 휴리스틱의 `12 · 23`(`review-v2-resume.md:165`)을 고친다.
휴리스틱이 잡은 것은 인용부호에 든 열거값(`critical`·`**[진행 필수]**` 꼴)뿐이고, **설정 키·절 이름·경로·표기 문자열을 판단형으로 보냈다.**

| 조각 | 성격 | 미적재 심각도 | 근거 |
|:--|:--|:--|:--|
| `traceability/level` | 어휘 | 높음 | 착지 경로가 닫힌 값이다 (`level.md:5-9`). 틀리면 다음 국면이 문서를 못 찾는다 |
| `traceability/id-system` | 어휘 | 치명 | ID 형식·이름 도출 (`:23-35`). **불변·append-only 라 되돌릴 수 없다** |
| `traceability/conflict` | 판단 | 중 | 발급 순서·예방 선택 (`conflict.md:23-54`). 결과는 머지 시점의 중복 |
| `traceability/tagging` | 어휘 | 치명 | frontmatter 키 `requirement:`·`design:` (`:20-27`). 기계 게이트의 판정 근거다 |
| `traceability/coverage` | 어휘 | 치명 | 상태 3값 · 분류 4값 (`coverage.md:11,22-26`). 레거시에서 안 가르면 **요구 전부가 gap** 이다 |
| `traceability/unit-state` | 어휘 | 높음 | 상태 5값 + `정지(사유)` 문형 (`:14-20,65-70`) |
| `traceability/revert-scope` | 판단 | 중 | 되돌아갈 범위 계산 · 정지 조건 (`:16-25`) |
| `testing/run` | 판단 | 높음 | 3회 루프 · 환경과 코드의 이분법 (`run.md:19-35`) |
| `testing/case-source` | 판단 | 치명 | 역산 금지 (`case-source.md:5-28`). 안 읽으면 **통과하는 가짜 테스트**가 나온다 |
| `testing/integration` | 판단 | 중 | 매트릭스 승인 · 모아 온 `미검증` 닫기 (`:9-32`) |
| `testing/llm-cost` | 판단 | 중 | 층 4개 · 상한 (`llm-cost.md:5-32`). 대상이 LLM 기능일 때만 |
| `code-review/layers` | 어휘 | 높음 | 층 이름 7개와 리포트 절 이름 (`layers.md:3-11,48-72`) |
| `code-review/severity` | 어휘 | 치명 | 등급 4값 · 상태 3값 (`severity.md:3-8,33`). `gatekeeper`·`commit` 이 이 값을 읽는다 |
| `code-review/checklist` | 판단 | 중 | 게이트 항목 (`checklist.md:5-35`). 스스로 "AI 는 이미 표준을 따른다" 고 적는다 (`:41`) |
| `code-graph/query` | 어휘 | 높음 | 반환 형식 · 정확도 3값 (`query.md:73-113`). `impact-analysis` 가 그대로 옮긴다 |
| `code-graph/service-boundary` | 어휘 | 치명 | 계약 범위 3값과 알림 문형 (`service-boundary.md:15-34`). **MSA 에서 유일한 방어다** |
| `doc-verify/grade` | 어휘 | 치명 | 등급 표기 `**[진행 필수]**` 등 (`grade.md:5-9`). 차단 판정이 여기서 갈린다 |
| `doc-verify/scoring` | 판단 | 높음 | 항목별 기준 · 역추출 면제 (`scoring.md:25-46,67-80`) |
| `doc-verify/canon-map` | 어휘 | 높음 | 값→정본 지도 (`canon-map.md:12-23`). 리포트에 정본 위치를 그대로 적는다 |
| `doc-template/diagram` | 어휘 | 높음 | `!pragma layout smetana` · 대상별 표기 (`diagram.md:7-30`). `lint` 도 이 문자열을 본다 |
| `doc-template/task-doc` | 어휘 | 치명 | 절 이름 5개 · 경로 형식 (`task-doc.md:9-26`). `File Map` 이 게이트의 판정 대상이다 |
| `doc-template/template-gap` | 판단 | 중 | 없는 절을 만났을 때의 선택 (`template-gap.md:11-25`) |
| `usecase/granularity` | 어휘 | 높음 | 표 칸 이름 · `종류` 값 · `측정 방법` 의 `—` (`granularity.md:21-31`) |
| `usecase/rule-level` | 어휘 | 높음 | `R`·`DR`·`SYS` 번호와 `참조:` 표기 (`rule-level.md:20-36`) |
| `usecase/figure-scope` | 어휘 | 중 | 관계 표기 `«include»`·`..>` (`figure-scope.md:15-20`) + 그림 대상 판정표 |
| `contract-gate/config` | 어휘 | 높음 | 설정 키 `contract.pathGlob`·`contract.gate` 와 기본값 (`config.md:5-11,34`) |
| `contract-gate/failure` | 판단 | 높음 | 실패 원인 이분법 (`failure.md:5-8`). 안 읽으면 계약을 3회 헛고친다 |
| `impact-analysis/regression-surface` | 어휘 | 치명 | 판정 3값 · `안 본 범위` 절 · `repo 밖 — 사람 확인` (`:14-18,26-51`) |
| `drift-check/rule` | 어휘 | 높음 | 설정 키 `drift.ignore`·`drift.sourceGlobs` 와 판정 순서 (`rule.md:7-11`). 훅과 같아야 한다 |
| `default-reference/delegation` | 판단 | 중 | 위임 2분법 (`delegation.md:7-30`). 결과는 컨텍스트 비용이고 산출물은 그럴듯하다 |
| `ops-doc/safety` | 판단 | 치명 | 완화를 우리가 실행하지 않는다 · `사람만` 미실행 (`safety.md:27,35-39`) |
| `ops-doc/postmortem` | 판단 | 중 | 회고 규칙 · `어디로` (`postmortem.md:13-20`) |
| `ops-doc/authoring` | 어휘 | 높음 | `담당` 표의 `사람만` 표기 (`authoring.md:8`). **이 표기가 `safety` 의 판정 입력이다** |
| `theme-apply/spec` | 어휘 | 중 | 토큰 4범주 키 · 출처 표기 `AI 초안` (`spec.md:9-14,21-31`) |
| `theme-apply/apply` | 판단 | 중 | Tier 범위 · 적용 절차 (`apply.md:16-54`) |

### 이 재판정이 바꾸는 결론

`review-v2-resume.md:177` 은 *"어휘형 12개에 `doc-verify` 값 대조를 걸면 싸다"* 로 갔다. 어휘형이 21개면 그 범위가 넓어지는데, **전부에 걸리지는 않는다.** 대조는 채점 대상 문서에만 걸 수 있다.

| 어휘형 | 값이 어디 나타나나 | 대조 가능 |
|:--|:--|:--|
| 18개 | 요구·설계·task·리뷰·검증·운영 문서 | 가능 — `doc-verify` 가 이미 그 문서를 본다 |
| `contract-gate/config` · `drift-check/rule` | `workflow.config.json` | **불가** — 설정 파일은 채점 대상이 아니다 |
| `code-graph/service-boundary` | 계약 파일 머리 | **불가** — `scoring.md:21` 이 계약 파일을 채점에서 뺀다 |

그리고 심각도 판정 하나가 앞선 리뷰와 갈린다. `review-v2-resume.md:172` 는 `delegation` 을 가장 위험한 셋에 넣었는데, **그 미적재의 결과는 비용이고 산출물 오류가 아니다.** 그 자리에 들어갈 것은 `testing/case-source` 다 — 역산한 테스트는 통과로 나오고 흔적이 없다(`case-source.md:27`).

## 중복과 공백

### 정본이 둘

| 무엇 | 어디와 어디 | 판정 |
|:--|:--|:--|
| 환경 실패 신호 목록 (`command not found`·`Cannot find module`·Exit 127) | `contract-gate/references/failure.md:8` ↔ `testing/references/run.md:32` | `run.md:35` 가 "정본은 저쪽" 이라 적고 **목록을 그대로 갖는다**. `drift-check` 가 계약 범위를 안 옮긴 것과 반대 처리다 |
| 역추출 면제 기준 | `doc-verify/references/scoring.md:71-80` ↔ `commands/prd.md:98-105` ↔ `traceability/references/coverage.md:22-31` | 정본 선언이 없는 3사본. `prd.md:104-105` 는 `coverage.md:30-31` 과 거의 같은 문장이다 |
| `유닛을 넘으면 explorer 에 위임` | `default-reference/references/delegation.md:26` ↔ `impact-analysis/references/regression-surface.md:10` ↔ `doc-verify/references/scoring.md:10` | 정본은 선언돼 있으나(`impact-analysis/SKILL.md:27`) 결론 문장이 두 조각에 복사됐다 |
| `미검증` 이라는 이름 | `testing/case-source.md:79`(규칙이 이 범위에서 안 돌았다) · `traceability/coverage.md:11`(`현행(미검증)`) · `impact-analysis/regression-surface.md:36`(영향처에 테스트가 없다) | **같은 낱말이 세 뜻이다.** 레거시에서 셋이 동시에 나와 리포트가 섞인다 |
| 어느 조각을 읽나 | 12개 SKILL.md 의 판정표 ↔ `flow.topology.json` 의 `loads`·`conditional` | 같은 결정을 두 곳이 갖는다. `02.skills-map.md:207-209` 가 이 중복을 스스로 인정하면서 **정본을 정하지 않았다** |

**검사기가 왜 못 잡나** — `skill-duplication` 은 `ctx.skills()` 를 도는데 그건 `SKILL.md` 14개뿐이다(`scripts/lint.py:124-125`). 조각 35개(약 1,900줄, 이 층의 82%)와 커맨드 본문은 **중복 검사 밖**이다.

### 배선이 끊긴 자리 — 가리킨 조각을 아무도 안 싣는다

`fragment-reference-exists` 는 **실존만** 본다(`scripts/lint.py:1399-1417`). 가리킨 쪽이 그 조각을 싣는지는 아무 검사도 안 본다.

| 어디서 가리키나 | 무엇을 | 싣나 |
|:--|:--|:--|
| `code-graph/SKILL.md:27` | 계약을 건드리거나 MSA 면 `service-boundary` 를 **반드시** 읽는다 | `build` 조건 로드에 없다 (`commands/build.md:21` 은 `code-graph/query` 만) |
| `procedures/design/feature.md:82` | 계약 범위 표기의 정본은 `service-boundary` | `design`(기능) 은 `code-graph` 를 아예 안 싣는다 |
| `doc-template/references/task-doc.md:5` | 어느 값이 어디 사는지는 `doc-verify` 의 정본 지도 | `build` 는 `doc-verify/canon-map` 을 안 싣는다 |
| `usecase/references/granularity.md:31` | 요구 표 `상태` 칸은 `traceability` 의 커버리지 조각 | `prd` 는 `traceability/coverage` 를 안 싣는다 |
| `code-review/references/severity.md:37` | 되돌아가기 상한은 `traceability` 의 되돌아갈 범위 조각 | `review` 는 `revert-scope` 를 안 싣는다 |

**`build.md:15` 는 "조각은 여기 적힌 것만 읽는다" 고 못 박는다.** 그래서 위 두 줄은 어긋남이 아니라 **정면 충돌**이다 — SKILL.md 는 반드시 읽으라 하고 커맨드는 읽지 말라 한다.
그리고 `prd` 가 `coverage` 를 안 싣는 것이 `prd.md` 에 사본이 생긴 구조적 이유다. **정본을 안 싣는 배선이 사본을 만든다.**

### 지도가 실제와 어긋난 곳

| 어디 | 지도 | 실제 |
|:--|:--|:--|
| `02.skills-map.md:218` | `build` 는 `doc-template` 을 **조건부**로 싣는다 | `topology` 와 `commands/build.md:19` 는 무조건이다 |
| `02.skills-map.md:119` | `canon-map` 을 싣는 쪽에 `build` 가 있다 | `topology`·`build.md`·같은 지도의 `:52`·`:218` 모두 없다 |

### 아무도 말하지 않는데 필요한 것

- **역추출 절차의 정본이 없다.** 조각 35개 중 역추출을 다루는 것은 면제·채점 쪽뿐이고(`coverage.md:25` · `scoring.md:67` · `usecase/SKILL.md:30` · `figure-scope.md:34`), *어떻게 코드에서 요구를 뽑나* 는 `commands/prd.md:87-94` 본문에만 있다. **재사용도 대조도 안 된다.**
- **역추출한 요구가 코드와 맞나를 아무도 안 본다.** `doc-verify/SKILL.md:38` 은 내용을 안 보고, `canon-map.md:34` 는 코드와 문서의 불일치를 남에게 넘기고, `drift-check` 는 존재만 보고, `coverage.md:25` 는 면제한다. **레거시에서 가장 자주 틀리는 자리에 층이 없다.**
- **레거시 코드에서 유닛 경계를 어떻게 가르나** 가 없다. `id-system.md:37-50` 은 폴더명 불변만 말하고 `:50` 은 "처음 만들 때 잘 정한다" 로 넘긴다. `prd.md:106` 은 `func legacy` 를 거부하며 `domain legacy` 로 보내는데, 받는 쪽 규약은 `procedures/design/system.md:72` 한 줄이다.
- **DB 스키마 역추출** 의 주인이 없다. `drift-check/rule.md:26-34` 는 `00.ref/02.db-schema` 를 못 잡는다고 적고, `procedures/build/schema-change.md:11` 은 변경 시 갱신만 말한다. 기존 DB 에서 그 문서를 처음 만드는 규약이 없다.

## 레거시 변형 렌즈

요구를 역추출하고 · 영향 범위를 재고 · 계약을 뽑는 세 일로 나눠 본다.

| 일 | 이 층이 충분한가 | 모자란 규약 (근거) |
|:--|:--|:--|
| 요구 역추출 | **아니다** | `prd` 가 싣는 조각에 코드를 읽는 규약이 하나도 없다 — `traceability/level`·`id-system`·`conflict` · `usecase/*` · `doc-template/*` 뿐이다(`topology` `commands.prd.loads`). `default-reference/delegation` 도 안 싣는데 `prd.md:20` 은 `explorer` 위임을 `legacy` 에서 필수라고 한다 |
| 영향 범위 | **절반** | `impact-analysis/regression-surface.md` 는 충분하다. 그런데 `:24` 가 요구하는 계약 범위 판정의 정본(`service-boundary`)이 `build`·`design` 배선에 없다. **MSA 레거시에서 "영향 없음" 오보의 경로가 열려 있다** |
| 영향 범위 (스키마) | **아니다** | `impact-analysis/SKILL.md:16` 은 DB 컬럼 변경을 발동 대상으로 잡고 절차를 `code-graph` 에 넘기는데, `query.md:32` 는 `.sql` 이 CPG 밖이라 grep 뿐이라고 적는다. **그 한계가 `regression-surface` 의 `안 본 범위` 항목으로 이름이 붙어 있지 않다** |
| 계약 뽑기 | **아니다** | `contract-gate/config.md:42-48` 의 레거시 폴백은 *설정* 이야기다. 기존 엔드포인트·타입에서 계약 파일을 만드는 규약은 어느 조각에도 없다 |
| 채점 | 된다 | `scoring.md:67-80` 의 역추출 면제와 `coverage.md:20` 의 `현행(미검증)` 분리가 레거시를 막지 않는다. **이 층에서 가장 잘 된 부분이다** |
| 게이트 | 된다 | `rule.md:48` 의 "유닛이 하나도 없으면 통과" 가 도입 첫날을 막지 않는다 |

`traceability`·`code-graph` 는 **변경 국면 전제**로 쓰여 있다. `code-graph/SKILL.md:33-34` 는 상시 인덱스를 금지하고 스코프를 "변경 파일과 그 모듈" 로 못 박는데, **레거시 분석 시점에는 변경 파일이 아직 없다.** 분석 목적의 스코프 규약이 없다 — `query.md:50-56` 의 목적 5개도 전부 변경 기준이고 *"이 코드가 무슨 규칙을 구현하나"* 가 없다.

## 재설계 후보

각 줄에 근거를 하나만 붙인다.

**합칠 것**

- `contract-gate/failure` 의 신호 목록을 `testing/run` 에서 걷고 이름만 남긴다 — `run.md:35` 가 이미 정본을 선언했는데 목록을 갖고 있다.
- 12개 SKILL.md 의 `어느 조각을 읽나` 표를 `topology` 하나로 접는다 — 같은 결정을 두 곳이 갖고 그 중 하나만 기계가 읽는다(`02.skills-map.md:207-209`).

**나눌 것**

- `doc-verify/scoring`(135줄) 에서 회고 조치 대조(`:48-65`)를 떼어 `ops-doc` 쪽 소비자와 짝지운다 — 문서 채점과 회고 등록 대조는 소비 시점이 다르고, 이 조각이 이 층의 최대 조각이다.

**없어야 하는 것**

- `commands/prd.md:98-105` 의 역추출 면제 표 — `coverage.md`·`scoring.md` 와 3중 사본이고, 커맨드 본문은 중복 검사 밖이다.

**새로 필요한 것**

- 역추출 조각 하나 (`traceability/reverse-extract` 또는 새 스킬) — 코드에서 요구를 뽑는 절차 · 레거시 유닛 경계 획정 · 역추출 요구와 코드의 대조. **사용자가 확정한 주 사용 상황에 정본이 없다.**
- `code-graph/query` 에 분석 목적 행과 분석 스코프 규약 — `:50-56` 의 목적 5개가 전부 변경 기준이다.
- 배선 검사 하나 — 조각이 "반드시 읽는다" 로 가리킨 것을 그 커맨드가 싣는지 대조한다. `fragment-reference-exists` 는 실존만 본다(`scripts/lint.py:1399`).
- `skill-duplication` 의 대상을 조각 35개와 커맨드 본문까지 넓힌다 — 지금은 `SKILL.md` 14개뿐이라 이 층의 82%가 검사 밖이다(`scripts/lint.py:124`).
- `build`·`design`(기능) 배선에 `code-graph/service-boundary` 추가 — `code-graph/SKILL.md:27` 과 `commands/build.md:15` 가 정면으로 충돌한다.
- `미검증` 세 뜻에 서로 다른 이름 — 레거시에서 셋이 한 리포트에 같이 나온다.
