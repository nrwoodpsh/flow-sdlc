---
description: 테스트 실행(단위·브랜치·프로젝트)과 요구 커버리지 감사 — 두 일이고 인자로 가른다
argument-hint: '[unit | branch {이름} | project | coverage] [대상 (선택)]'
---

# /flow:verify — 검증

**두 일을 한다. 인자가 가른다.**

| 인자 | 무슨 일 | 무엇으로 판정하나 |
|:--|:--|:--|
| `unit`·`branch`·`project` | **테스트 실행** — 시나리오를 실제로 돌린다 | `verifier` 가 격리 실행한 **Exit code** |
| `coverage` | **요구 커버리지 감사** — 추적 축을 대조한다 | 태그 역인덱스. 테스트를 돌리지 않는다 |

이 둘은 도구·에이전트·병렬 전략이 전혀 다르다. **인자로 가르고 본문 조각도 가른다.**

## 연결

정본은 `flow.topology.json` 의 `commands.verify` 다. **조각은 여기 적힌 것만 읽는다.**

| 범위 | 스킬 | 조각 |
|:--|:--|:--|
| 단위 | `testing` · `traceability` · `plain-writing` | `testing/run` · `testing/case-source` · `traceability/coverage` |
| 통합·커버리지 | `testing` · `traceability` · `plain-writing` · `default-reference` | `testing/run` · `testing/case-source` · `testing/integration` · `traceability/coverage` · `default-reference/delegation` |

| 무엇 | 이름 |
|:--|:--|
| 에이전트 | `verifier`(실행 — 코드를 고치지 않는다) · `gatekeeper`(커버리지 결론 대조) · `explorer`(범위가 유닛을 넘을 때) |
| 절차 조각 | `${CLAUDE_PLUGIN_ROOT}/procedures/verify/run.md` · `${CLAUDE_PLUGIN_ROOT}/procedures/verify/coverage.md` |

## 게이트

게이트 조건의 정본은 `flow.topology.json` 의 `commands.verify` 의 `entry`·`exit` 다. **이 커맨드가 스스로 판정하지 않는다.**

- **약속** — `unit-task-doc`. task 문서가 있어야 무엇을 검증하는지가 정해진다.
  **아무 훅도 이걸 안 본다** — 이 커맨드는 테스트를 돌릴 뿐이라 막을 도구 호출 시점이 없고,
  그 Bash 를 문서가 없다고 막으면 과차단이라 사람이 훅을 꺼 버린다.
- **내용 · 퇴장** — `coverage-gap`. **끝낼 때 판정한다** — 구멍이 있나는 감사 결과 그 자체라 돌리기 전에는 분류표가 없다. 감사가 낸 결론을 **`gatekeeper` 에 넘긴다. 반드시 부른다** — 감사한 쪽이 자기 결론을 확인하면 편향된다.

  ```
  gatekeeper 위임 — exit.content 의 coverage-gap   (분류표가 나온 뒤 · 리포트 확정 전)
    준다: 요구 ID 별 분류표 · 각 분류의 근거(태그·task·검증 결과 경로)
    받는다: gap 판정이 맞나 / 뒤집히는 것 + 사유
    뒤집히면 분류를 고치고 **뒤집힌 사유를 리포트에 함께 적는다**
  ```

  분류표를 내는 것은 `coverage` 범위다. 테스트만 돌린 범위에는 판정할 분류표가 없다.

- **약속** — `run-not-infer`. **테스트를 실제로 돌려 exit code 로 판정한다 — 추론은 검증이 아니다**(`testing`).

## 입력 (`$ARGUMENTS`)

| 인자 | 동작 |
|:--|:--|
| (비움) | **범위를 되묻는다.** 임의로 고르지 않는다 — 범위마다 비용과 읽는 양이 다르다 |
| `unit [대상]` | 그 유닛의 단위 테스트를 다시 돌린다. 보통 `/flow:build` 루프가 이미 했다 — **고친 뒤 재확인**·flow 도입 전에 만든 유닛이 여기 온다 |
| `branch [{이름}]` | 그 브랜치 유닛들의 **조합**(머지 전). 이름을 안 주면 `git branch --show-current` |
| `project` | **전체 통합** — 계획한 유닛을 전부 만든 뒤 |
| `coverage [{도메인} \| project]` | **요구 커버리지 감사.** 범위를 안 주면 `project` |

**범위는 요구 레벨과 대응한다** — 무엇을 커버했다고 말할 수 있는 기준이 레벨마다 다르다. 어느 규칙 레벨이 어느 범위에서 닫히나는 `testing/case-source` 가 정본이고, 요구 ID 와 레벨의 대응은 `traceability/coverage` 가 정본이다.

## 절차

### 먼저 읽는다

**시작하기 전에 아래를 읽는다.** `## 연결` 의 표는 배선 선언이라 지시로 읽히지 않는다 —
실측에서 한 커맨드가 선언한 조각을 **하나도 안 읽고** 끝냈다(`build`, 0/7).
전체 경로는 **`${CLAUDE_PLUGIN_ROOT}/skills/{스킬}/references/{조각}.md`** 다 —
`references/` 를 빠뜨리면 파일이 없다(실측에서 한 번 그렇게 실패했다).
각 조각이 무엇의 정본인지는 그 파일 첫 줄에 있다.

- **단위 모드** `testing` — `references/run.md` · `references/case-source.md`
- **단위 모드** `traceability` — `references/coverage.md`
- **통합·커버리지 모드** `testing` — `references/run.md` · `references/case-source.md` · `references/integration.md`
- **통합·커버리지 모드** `traceability` — `references/coverage.md`
- **통합·커버리지 모드** `default-reference` — `references/delegation.md`
- 절차 — `procedures/verify/coverage.md` · `procedures/verify/run.md`

**대상 선언** — 무엇을 어느 범위로 도는지 먼저 밝힌다.

```
[/flow:verify] 범위: {unit | branch | project | coverage} · 대상: {유닛 | 브랜치 | 도메인}
          기록: {유닛의 5.verify/ | 03.integration/… | 그 범위의 통합 결과 파일}
```

- **읽는 양과 갈래 수를 먼저 알린다.** 비용이 거기서 정해진다.
- 범위가 유닛을 넘으면 `explorer` 에 위임한다(`default-reference/delegation`) — 결론만 받는다.

**테스트 실행** (`unit`·`branch`·`project`) — `${CLAUDE_PLUGIN_ROOT}/procedures/verify/run.md`.

**커버리지 감사** (`coverage`) — `${CLAUDE_PLUGIN_ROOT}/procedures/verify/coverage.md`.

**이어 돌릴 것을 권한다** — `project` 실행이 끝나면 `coverage` 를 이어 돌리라고 알린다. **자동으로 붙여 돌리지 않는다**: 도구도 병렬 전략도 다르고, 통과한 테스트만 보고 "다 됐다" 고 말하지 않기 위해 대조가 따로 있는 것이다.

- **커버리지 결과는 그 범위의 통합 결과 파일 안에 적는다** — 별 파일을 만들지 않는다. 따로 만들면 어느 실행의 결과인지 끊긴다.

## 가드레일

- **`testing` 의 경계를 그대로 지킨다** — 통과시키려고 테스트에 손대는 것이 거기 첫 줄이다.
- **판정만 한다.** 코드·테스트를 여기서 고치지 않는다 — 실패는 보고하고 수정은 `/flow:build` 다.
- **자동 검증이 안 되는 항목을 통과로 적지 않는다** — `사람 확인 필요` 로 남긴다.
- **gap 을 임의로 닫지 않는다.** 요구를 지우거나 줄여 커버리지를 맞추는 것은 금지다 — 리포트가 결론이다.
- **명시된 시나리오만 실행한다.** 임의로 무거운 테스트를 더 돌리지 않는다.
- **돈이 드는 호출을 상한 없이 반복하지 않는다.** 초과하면 멈추고 리포트한다.
