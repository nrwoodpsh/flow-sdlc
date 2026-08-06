---
description: 구현 + 단위 검증 — 설계·계약대로 코드를 쓰고 그 루프 안에서 테스트로 판정한다
argument-hint: '[도메인/유닛 또는 task 경로 (선택 — 없으면 파일에서 계산)]'
---

# /flow:build — 구현

설계(`2.task`)·계약(`3.contract`)을 정확히 따라 구현하고, **단위 검증을 이 루프 안에서** 끝낸다.
핵심 가치: **설계 충실도 > 클린 코드 > 테스트 통과.**

v1 은 `build` 와 `verify unit` 을 갈라 뒀지만 build 루프가 이미 단위 테스트를 돌리고 `5.verify/` 에 적었다. 합친다.

## 연결

정본은 `flow.topology.json` 의 `commands.build` 다. **조각은 여기 적힌 것만 읽는다.**

| 무엇 | 이름 |
|:--|:--|
| 스킬 | `traceability` · `testing` · `contract-gate` · `code-review` · `code-graph` · `impact-analysis` · `doc-template` · `plain-writing` · `default-reference` |
| 조각 | `traceability/tagging` · `traceability/unit-state` · `testing/run` · `testing/case-source` · `contract-gate/failure` · `code-review/checklist` · `impact-analysis/regression-surface` · `code-graph/query` · `doc-template/task-doc` · `default-reference/delegation` |
| 에이전트 | `builder`(구현 — **쓰기 권한은 여기 하나**) · `verifier`(실행 판정) · `gatekeeper`(진입 내용 판정) · `explorer`(넓게 읽을 때) |
| 절차 조각 | `${CLAUDE_PLUGIN_ROOT}/procedures/build/unit-verify.md` · `${CLAUDE_PLUGIN_ROOT}/procedures/build/schema-change.md` |

## 게이트

진입 조건의 정본은 `flow.topology.json` 의 `commands.build.entry` 다. **이 커맨드가 스스로 판정하지 않는다.**

- **기계** — `unit-task-doc`·`unit-req-tag`. 소스에 `Write`·`Edit` 가 들어가는 순간 `gate-source-write.sh` 가 task 문서와 요구 태그를 본다. 없으면 차단이다. **훅을 끄거나 우회하지 말고 task 문서를 먼저 만든다**(`/flow:design`).
- **내용** — `contract-followed`. **`gatekeeper` 에 넘긴다. 반드시 부른다** — 진행하는 쪽이 자기 조건을 판정하면 판정 독립성이 없다.

  ```
  gatekeeper 위임 — entry.content 의 contract-followed
    준다: task 경로 · 계약 경로 · 이번에 건드릴 파일 목록
    받는다: 충족 / 미충족 + 근거(파일:라인)
    미충족이면 여기서 멈춘다 — 계약을 코드에 맞춰 고치지 않는다
  ```

- **약속** — `no-self-verify`. **구현한 쪽이 자기 검증을 하지 않는다.** 도구 권한이 일부를 가르지만 호출 자체는 약속이다.

**면제는 `gate.exemptions` 가 정본이다** — `spike/` 아래 · **레거시 면제 유닛** · 유닛이 하나도 없는 도입 첫날 · 소스가 아닌 것. 레거시에 신규용 게이트를 그대로 걸면 정상 작업이 전부 막히고, **과차단이면 사람이 훅을 꺼 버린다** — 그러면 그 층이 영구히 없어진다. 면제를 커맨드가 판정하지 않는다.

## 입력 (`$ARGUMENTS`)

| 인자 | 동작 |
|:--|:--|
| (비움) | 미완료 task 를 **파일에서 계산**한다 — `2.task/NN` 이 있고 `4.build/NN` 이 없는 것(`traceability/unit-state`). 후보가 둘 이상이거나 모호하면 확인받는다 (임의 "최근" 금지) |
| `도메인/유닛` 또는 task 경로 | 그 대상으로 바로 구현 |

## 절차

**대상 선언** — 작업 전 필수.

```
[/flow:build] 대상 task: doc/01.work/{도메인}/{NN.유닛}/2.task/NN.name.md
         계약: .../3.contract/  → 이 설계로 구현합니다.
```

**상태는 파일에서 계산한다.** README 의 `상태` 는 캐시라 낡을 수 있다 — 믿지 않는다.

- 남은 task 가 여럿이면 계산한 진행(구현·검증)을 함께 보여주고 이어갈 자리를 지목한다.
- **번호가 빠져 있으면 알린다**(`00`·`02` 만 있고 `01` 없음) — 스파인이 깨졌다는 뜻이다.
- **계산한 상태가 README 와 다르면 알리고 `/flow:sync` 를 권한다.** 여기서 README 를 고치지 않는다.

**사전 게이트** — `contract-gate` 로 계약을 컴파일한다. 실패 원인이 계약인지 환경인지는 `contract-gate/failure` 가 정본이다. **`build` 가 계약의 뜻을 바꾸지 않는다** — 그 계약을 쓰는 다른 task 가 조용히 깨진다. 모르겠으면 멈춘다.

**영향 분석** — File Map 에 `[Mod]`(기존 수정)가 있으면 `impact-analysis/regression-surface` 로 회귀 표면을 뽑는다(그래프 질의는 `code-graph/query`). 순수 `[New]` 면 생략한다.

**`1.design.md` 의 `엣지 케이스` 를 함께 읽는다.** task 는 규약상 설계·화면을 복사하지 않고 ID 로 가리킨다 — 가리키는 쪽을 안 열면 **엣지 케이스가 구현과 테스트에서 같이 빠진다.**

- 읽는 절은 `엣지 케이스`·(FE 면)`화면 구조` 뿐이다. 분석·데이터 구조는 설계 국면이 이미 소화했다.
- **엣지 케이스마다 테스트를 만든다** — 정상 흐름만 통과하면 검증이 아니다.

**스키마 변경** — 설계에 마이그레이션이 있으면 **구현보다 먼저** 처리한다. 순서와 담당은 `${CLAUDE_PLUGIN_ROOT}/procedures/build/schema-change.md`.

**구현↔검증 루프** (`builder` ⇄ `verifier`, 최대 3회) — 단위 검증의 케이스·실행·기록은 `${CLAUDE_PLUGIN_ROOT}/procedures/build/unit-verify.md`.

```
builder 구현 → verifier 실행
  Exit 0            → 통과
  Exit ≠ 0 (1·2회차) → 원인 분석 → builder 재수정 → 재실행
  Exit ≠ 0 (3회차)   → 중단 · 사람에게 리포트   (자율 무한루프 금지)
```

- 계획 이탈(엣지 케이스·설계 누락)은 보수적으로 택하고 task `History` 에 **Deviation** 으로 즉시 적는다 — *계획이 말한 것 / 코드가 드러낸 것 / 택한 선택 / 사유*. 이 로그가 `/flow:sync` 의 입력이다.
- 이탈이 **설계 결함**을 드러내면 멈추고 리포트한다.

**전체 빌드** — `workflow.config.json` 의 `build.command` 로 1회 돌린다. 테스트는 건드린 파일만 컴파일할 수 있어 **전체 컴파일 오류는 여기서만 드러난다.** 키가 비었으면 건너뛴다. 실패는 3회 루프에 넣지 않고 **즉시 리포트**한다.

**기록** — task 번호와 1:1 로 둘 다 남긴다. `4.build/NN.md`(구현 요약·변경 파일·계약 준수·이탈 한 줄, 상세는 task `History`) · `5.verify/NN.md`(명세·결과·결함). 마지막으로 `code-review/checklist` 로 자기 점검한다.

## 종료 조건

- 계약 게이트 + 단위 검증 + 전체 빌드 통과(Exit 0) · `4.build/`·`5.verify/` 기록 · task `History` 갱신
- **커밋·push 안 함** → `/flow:sync` 로 문서를 맞춘다

## 가드레일

- **막히면 자율로 헤매지 않는다.** 3회 초과 실패·설계 결함·기존 테스트 깨짐이면 즉시 멈추고 원인·영향·권장을 리포트하고 승인을 기다린다. **테스트 약화·우회 절대 금지.**
- **설계 규격을 임의로 바꾸지 않는다.** 바꿔야 하면 멈추고 `/flow:design` 으로.
- **프로젝트 수준 결정은 ADR 로** — `doc/02.decisions/` 에 제안하고 사람 확인을 받는다.
- **테스트 코드를 `doc/` 안에 만들지 않는다.** 실행 코드는 소스 트리, 문서는 `5.verify/` 다.
- **운영·스테이징 DB 는 읽기만.** 되돌릴 수 없는 것은 사람에게 넘긴다 — 커밋·push·merge 는 이 커맨드의 일이 아니고, 민감정보 하드코딩은 금지다.
