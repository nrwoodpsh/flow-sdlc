---
description: 리뷰 — 코드(층으로 쌓아 등급) 또는 문서(템플릿과 대조). 리포트만 낸다
argument-hint: '[doc | deep] [파일/도메인/유닛 경로 (선택 — 없으면 git diff 대상)]'
---

# /flow:review — 리뷰

**두 대상을 본다. 인자가 가른다.**

| 인자 | 무엇을 | 기준 |
|:--|:--|:--|
| (비움) · 경로 · `deep` | **코드** | 층을 쌓아 잡고 등급을 매긴다 (`code-review`) |
| `doc [경로]` | **문서** | 그 문서의 템플릿 (`doc-verify`) |

**리포트만 낸다.** 코드도 문서도 고치지 않는다. 필요할 때 끼워 넣는 오버레이라 설계 없는 레거시에도 돌 수 있다.

## 연결

정본은 `flow.topology.json` 의 `commands.review` 다. **조각은 여기 적힌 것만 읽는다.**

| 대상 | 스킬 | 조각 |
|:--|:--|:--|
| 코드 | `code-review` · `code-graph` · `testing` · `plain-writing` · `default-reference` | `code-review/layers` · `code-review/severity` · `code-review/checklist` · `code-graph/query` · `code-graph/service-boundary` · `testing/run` · `default-reference/delegation` |
| 문서 | `doc-verify` · `usecase` · `traceability` · `ops-doc` · `plain-writing` · `default-reference` | `doc-verify/grade` · `doc-verify/scoring` · `doc-verify/canon-map` · `usecase/granularity` · `usecase/figure-scope` · `usecase/rule-level` · `traceability/coverage` · `ops-doc/postmortem` · `default-reference/delegation` · (조건 — 역추출 문서를 채점할 때만) `traceability/reverse-check` |

| 무엇 | 이름 |
|:--|:--|
| 에이전트 | `reviewer`(격리 리뷰 — 정적분석 도구를 **Bash 로 직접 돌려** 룰 기반 발견을 만든다) · `gatekeeper`(진입 내용 판정 — 발견 등급 반증) · `explorer`(문서 다수 대조) |
| 절차 조각 | `${CLAUDE_PLUGIN_ROOT}/procedures/review/code.md` · `${CLAUDE_PLUGIN_ROOT}/procedures/review/doc.md` |

## 게이트

게이트 조건의 정본은 `flow.topology.json` 의 `commands.review` 의 `entry`·`exit` 다. **이 커맨드가 스스로 판정하지 않는다.**

- **기계** — 없다. 리뷰는 아무 때나 끼울 수 있어야 한다.
- **내용 · 퇴장** — `finding-severity`. **끝낼 때 판정한다** — 시작할 때는 발견이 없어 등급을 매길 대상이 없다. 발견과 등급 **초안**은 `reviewer` 가 만든다(도구를 돌리는 쪽이 근거를 갖는다). 그러나 **판정은 `gatekeeper` 에 넘긴다. 반드시 부른다** — 발견을 만든 쪽이 자기 발견의 등급을 확정하면 판정 독립성이 없다.

  ```
  gatekeeper 위임 — exit.content 의 finding-severity   (발견 목록이 나온 뒤 · 리포트 확정 전)
    준다: 발견마다 파일:라인 · 근거(어느 층·어느 룰) · 재현 조건 · reviewer 가 매긴 등급
    받는다: 진짜 문제인가 / 재현되는가 / 등급이 맞나 — 반증 우선
    뒤집히면 등급을 내리고 **뒤집힌 사유를 리포트에 함께 적는다**
  ```

  등급 산정 규칙 자체는 `code-review/severity` 가 정본이다 — 판정자가 그 규칙을 새로 만들지 않는다.

- `medium`·`low` 는 반증하지 않는다 — 비용 대비 값이 낮다.
- **약속** — `critical-rule-based`. **critical 하드 차단은 룰 기반 발견만이다.** LLM 단독 추측은 리포트로만 — 오탐으로 파이프라인을 멈추지 않는다.

## 입력 (`$ARGUMENTS`)

| 인자 | 동작 |
|:--|:--|
| (비움) | **코드** — `git diff` 변경 파일 |
| `파일/도메인 경로` | **코드** — 그 범위만 |
| `deep` | **코드** — 일반 층 + **외부 모델이 설계 선택을 의심한다.** 코드를 외부로 보내는 것이라 실행 전에 알리고 확인받는다 (`code-review/layers`) |
| `doc [경로]` | **문서** — 유닛 · `00.ref/` · `02.decisions/` · `04.ops/` |

## 절차

### 먼저 읽는다

**시작하기 전에 아래를 읽는다.** `## 연결` 의 표는 배선 선언이라 지시로 읽히지 않는다 —
실측에서 한 커맨드가 선언한 조각을 **하나도 안 읽고** 끝냈다(`build`, 0/7).
전체 경로는 **`${CLAUDE_PLUGIN_ROOT}/skills/{스킬}/references/{조각}.md`** 다 —
`references/` 를 빠뜨리면 파일이 없다(실측에서 한 번 그렇게 실패했다).
각 조각이 무엇의 정본인지는 그 파일 첫 줄에 있다.

- **코드 모드** `code-review` — `references/layers.md` · `references/severity.md` · `references/checklist.md`
- **코드 모드** `code-graph` — `references/query.md` · `references/service-boundary.md`
- **코드 모드** `testing` — `references/run.md`
- **코드 모드** `default-reference` — `references/delegation.md`
- **문서 모드** `doc-verify` — `references/grade.md` · `references/scoring.md` · `references/canon-map.md`
- **문서 모드** `usecase` — `references/granularity.md` · `references/figure-scope.md` · `references/rule-level.md`
- **문서 모드** `traceability` — `references/coverage.md`
- **문서 모드** `ops-doc` — `references/postmortem.md`
- **문서 모드** `default-reference` — `references/delegation.md`
- *역추출 문서를 채점할 때만* — `skills/traceability/references/reverse-check.md`
- 절차 — `procedures/review/code.md` · `procedures/review/doc.md`

**대상 선언** — 무엇을 어느 층으로 보는지, **무엇이 빠졌는지 먼저 밝힌다.**

```
[/flow:review] 대상: {git diff 목록 | 지정 경로}   단계: {일반 | deep | doc}
          기준: {2.task·3.contract (있으면) | 프로젝트 템플릿}
          층: {실제로 돌 것}      빠진 층: {없는 도구와 그 영향}
```

- **빠진 층을 먼저 적는다.** 나중에 "다 봤다" 로 읽히면 안 된다. **"안 봤다" 를 "문제없다" 로 적지 않는다.**
- **도구가 없다고 멈추지 않는다.** 그 층을 빼고 나머지로 진행하고 리포트에 적는다.

**코드 리뷰** — `${CLAUDE_PLUGIN_ROOT}/procedures/review/code.md`.

**문서 리뷰** — `${CLAUDE_PLUGIN_ROOT}/procedures/review/doc.md`.

**리포트** — 유닛이면 `{유닛}/6.review/NN.내용.YYYYMMDD.md` 에 회차로 남긴다. 유닛 밖(`00.ref`·`02.decisions`·`04.ops`)이면 파일로 남기지 않고 리포트만 낸다.

- 항목마다 **파일:라인 + 발견 + 출처(어느 층) + 권장 조치.** 문서에 없던 위험은 **근거**도 붙인다.
- **안 본 주제**와 **빠진 층**을 함께 적는다 — 통과 목록만 보면 "다 봤다" 로 읽힌다.
- **회차를 합치거나 지우지 않는다.** 이력이다 — 다음 회차가 이미 지적된 것을 알아야 한다.

## 가드레일

- **코드도 문서도 고치지 않는다** — 수정은 `/flow:build`·`/flow:sync` 다.
- **critical 만 하드 차단**(룰 기반). 임계는 `workflow.config.json` 의 `review.severity` 이고 **리뷰가 그 값을 바꾸지 않는다.**
- **자기 발견을 자기가 확인하지 않는다** — critical·high 는 `gatekeeper` 가 반증한다.
- **근거 없이 등급을 매기지 않는다.** 확인 안 된 것은 `확인 필요` 로 명시한다.
- **이전에 정리된 지적을 다시 올리지 않는다** — *"그건 이래서 괜찮다"* 로 닫힌 것은 그 판단을 인용한다.
- **코드를 외부로 보내기 전에 알린다.** 확인 없이 전송하지 않는다.
