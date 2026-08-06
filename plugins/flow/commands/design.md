---
description: 설계 — 시스템·도메인 구조부터 기능의 task·계약까지
argument-hint: '[sys | domain {도메인} | {도메인}/{NN.유닛} | 자유 문장(버그·변경)] [REFERENCE @file ...]'
---

# /flow:design — 설계

요구를 분석해 **구조를 확정**한다. 기능 레벨이면 **구현 단위(task)와 계약까지** 낸다.

> **구현 코드를 쓰지 않는다.**
> **단일 정문**: 동작·로직이 바뀌는 변경은 전부 여기를 지난다. 오타·문구만 flow 밖이다.

## 연결

**레벨이 무엇을 싣는지를 가른다.** 기능 설계는 기능마다 반복되므로 시스템 설계 절차를 같이 싣지 않는다.

| 레벨 | 스킬 | 조각 |
|:--|:--|:--|
| 시스템·도메인 | `traceability`·`usecase`·`doc-template`·`theme-apply`·`plain-writing`·`default-reference` | `traceability/level`·`traceability/id-system`·`traceability/conflict`·`traceability/tagging`·`usecase/rule-level`·`doc-template/diagram`·`doc-template/template-gap`·`default-reference/delegation` |
| 기능 | `traceability`·`doc-template`·`contract-gate`·`impact-analysis`·`plain-writing`·`default-reference` | `traceability/tagging`·`doc-template/task-doc`·`doc-verify/canon-map`·`contract-gate/config`·`contract-gate/failure`·`impact-analysis/regression-surface` |

영향·사각지대를 넓게 훑을 때는 `explorer` 에 위임한다. 위임 판정 자체는 `default-reference` 의 `delegation` 조각이 정본이다.

## 진입 조건

정본은 `${CLAUDE_PLUGIN_ROOT}/flow.topology.json` 의 `commands.design.entry` 다. **여기서는 선언만 한다.**

| 등급 | 조건 | 누가 판정 |
|:--|:--|:--|
| 내용 | 설계가 그 요구를 실제로 덮나 | **`gatekeeper`** — 진행하는 쪽이 아니다 |
| 약속 | 그 레벨의 요구 문서가 있다 | **아무도** — 훅이 커맨드 호출을 못 본다 |

**`요구 문서가 있다` 는 약속이다 — 기계가 아니다.** 걸 수 있는데 안 거는 것이 아니라,
걸면 **정상 경로가 막힌다**: 도메인 레벨은 요구와 설계가 같은 파일이고(`01.domain/{도메인}.md`),
버그·작은 변경은 이 커맨드가 요구를 **자동 발급**하는 것이 정상이다(`traceability` 의 `level`).

**착지 전에 `gatekeeper` 를 부른다.** 설계 요소가 요구 ID 를 빠짐없이 덮는지, 태그가 실제로 달렸는지를 넘긴다.
**부르지 않고 다음 국면으로 넘어가지 않는다** — 이름만 부르고 안 부르면 게이트가 없는 것이다.

## 입력 (`$ARGUMENTS`)

| 인자 | 동작 |
|:--|:--|
| (비움) | 최근 요구 산출을 자동 식별한다. 애매하면 묻는다 |
| `sys` · `domain {도메인}` | 시스템·도메인 레벨 대상 지정 |
| `{도메인}/{NN.유닛}` | 기능 레벨 대상 지정 |
| 자유 문장 | 버그·변경 요청 — 기능 레벨로 처리하고 **요구를 자동 발급**한다 |
| `REFERENCE @파일` | 로그·기존 코드·스키마 |

## 절차

### 레벨을 먼저 정하고, 그다음 절차 조각을 읽는다

레벨 판별 질문은 `traceability` 가 정본이다. **판별 전에 절차 조각을 읽지 않는다** — 순서가 바뀌면 반복되는 쪽이 안 쓰는 절차를 매번 싣는다.

```
[/flow:design] 레벨: {시스템|도메인|기능}  대상: {…}
               입력: {요구 ID 목록}   산출: {라우팅 경로}
               읽을 절차: {아래 표}
```

| 레벨 | 읽을 절차 |
|:--|:--|
| 시스템 · 도메인 | `${CLAUDE_PLUGIN_ROOT}/procedures/design/system.md` |
| 기능 | `${CLAUDE_PLUGIN_ROOT}/procedures/design/feature.md` |

- **둘을 같이 읽지 않는다.** 도메인 설계는 도메인당 1회, 기능 설계는 기능마다 반복이다.
- 레벨을 판별하지 못하면 **묻고 멈춘다.** 추측한 레벨로 진행하면 착지처와 ID 형식이 함께 틀어진다.
- 요구가 없을 때: **버그·변경 요청이면 기능 절차가 요구를 자동 발급**한다. 신규 기능이면 `/flow:prd` 를 먼저 안내한다.

### 무엇을 하든 지키는 것

- **요구에 없는 것을 설계에 넣지 않는다.** 필요하면 요구부터 추가한다.
- **영향도가 모호하면 멈추고 묻는다.** 추측으로 설계를 채우지 않는다.
- 판단이 갈린 결정은 **택한 안과 기각한 대안**을 함께 남긴다. 중요한 결정은 ADR 로 낸다.
- 같은 값이 두 문서에 있으면 그 중복이 결함이다 — 값의 정본 지도는 `doc-verify` 의 `canon-map` 조각이다.
- 태그는 **직접 충족만** 적는다(부모는 전이). 규약은 `traceability` 의 `tagging` 조각이 정본이다.

### 착지하고 넘긴다

- 시스템·도메인은 **여기서 정지**한다. 결과가 참조 정본이 된다.
- 기능은 task 와 계약까지 낸 뒤 넘긴다. 다음 국면은 위상 정본(`flow.topology.json` 의 `commands.design.next`)이 정한다.
- 넘기기 전에 **`gatekeeper` 판정을 받는다.**

## 가드레일

- **구현 코드 작성 금지.** 산출물은 설계 문서·task 문서·계약뿐이다.
- **레벨에 맞지 않는 절차를 실행하지 않는다.** 시스템·도메인 요구에 task 를 나누지 않는다.
- 버그는 **근본원인을 확정하기 전에 수정 설계를 내지 않는다.**
- **도메인 파일의 `요구` 절을 고치지 않는다** — 자리 나눔은 `/flow:prd` 가 정본이다.
- 계약은 게이트를 통과하기 전까지 완료로 보고하지 않는다.
- 추측과 확인을 구분해 표기한다.
