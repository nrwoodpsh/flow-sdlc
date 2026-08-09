---
description: 코드 ↔ 문서 수렴 — diff 로 설계 문서를 갱신하고 요약·색인을 계산한다. 커밋하지 않는다
argument-hint: '[도메인 (선택 — 없으면 git diff 에서 자동 분류)]'
---

# /flow:sync — 수렴

코드와 문서를 맞추는 **유일한 퇴장구**다. 어느 진입점에서 왔든 커밋 전에 여기를 지난다.
**커밋하지 않는다** → `/flow:commit`.

## 연결

정본은 `flow.topology.json` 의 `commands.sync` 다. **조각은 여기 적힌 것만 읽는다.**

| 무엇 | 이름 |
|:--|:--|
| 스킬 | `traceability` · `drift-check` · `doc-verify` · `contract-gate` · `plain-writing` · `default-reference` |
| 조각 | `traceability/tagging` · `traceability/unit-state` · `traceability/coverage` · `traceability/conflict` · `drift-check/rule` · `doc-verify/canon-map` · `contract-gate/failure` · `default-reference/delegation` |
| 에이전트 | `explorer`(diff 가 크거나 유닛이 여럿일 때 — 원문을 메인으로 끌어오지 않는다) |
| 절차 조각 | `${CLAUDE_PLUGIN_ROOT}/procedures/sync/index.md` |

> 드리프트 **판정**은 `/flow:commit` 이 한다(`drift-check`). 여기는 **갱신하는 쪽**이다 — 짝을 이루지만 하는 일이 다르다.

## 게이트

게이트 조건의 정본은 `flow.topology.json` 의 `commands.sync` 의 `entry`·`exit` 다. **이 커맨드가 스스로 판정하지 않는다.**

- **약속** — `source-changed`. `git diff` 가 비었으면 동기화할 것이 없다.
  **진행하는 쪽이 자기 diff 를 보는 것**이라 판정 독립성이 없다 — 그래서 약속이다.
- **내용** — 없다. `entry.content`·`exit.content` 가 둘 다 비어 있으니 **여기서 `gatekeeper` 를 부르지 않는다.** 부를 자리를 만들려면 `flow.topology.json` 에 먼저 적는다 — 커맨드 본문이 게이트를 발명하지 않는다.


## 입력 (`$ARGUMENTS`)

| 인자 | 동작 |
|:--|:--|
| (비움) | `git diff` 변경을 도메인별로 자동 분류 |
| `도메인` | 그 도메인 변경만 |

## 절차

**diff 수집·분류** — 백엔드·프론트·DB·설정으로 나눈다. 비었으면 `동기화 대상 없음` 을 알리고 끝낸다.

- **유닛을 넘으면 `explorer` 에 위임한다**(`default-reference/delegation`) — 무엇이 어느 유닛에 속하는지는 **결론만** 필요하다. 큰 diff 를 메인에서 통째로 읽지 않는다.

**설계 문서 갱신** (`doc/01.work/`) — **의도된 변경만 반영한다.**

- **`/flow:build` 의 Deviation 로그를 먼저 읽는다** — task `History` 의 이탈이 "무엇이·왜 벗어났나" 의 1차 입력이다.
- **의도된 변경**: 계약·`2.task` 를 코드 기준으로 갱신하고 `History` 에 사유를 적는다. 계약은 `contract-gate` 를 통과해야 한다(실패 처리는 `contract-gate/failure`).
- **설명 안 되는 코드↔계약 불일치**(버그 의심)는 **덮어쓰지 말고 리포트만** 한다 — 나쁜 구현을 정본으로 세탁하지 않는다.
- 같은 값이 두 문서에 있으면 그 중복 자체가 결함이다 — 정본을 `doc-verify/canon-map` 으로 찾는다.
- 프로젝트 수준 결정·정책 변경은 `doc/02.decisions/` 에 ADR 로 남긴다.

**DB 변경이 분류에 있으면 `doc/00.ref/02.db-schema/` 를 맞춘다.** 거기가 **지금 상태의 정본**이다.

- `/flow:build` 가 이미 갱신했으면 확인만 한다. 안 됐으면 여기서 맞춘다.
- **드리프트 판정이 이걸 못 잡는다** — `doc/` 아래라 문서로 취급된다(`drift-check/rule`). 퇴장구인 여기와 `/flow:commit` 이 마지막 확인이다.
- **실행문을 설계 문서로 옮기지 않는다** — 설계에는 구조와 이유만 있다.

**요약 생성** — `{유닛}/7.summary/NN.내용.YYYYMMDD.md` 에 회차로 남긴다. 개요(유닛·날짜·브랜치) / 변경 / API 변경 / 특이사항(설계 대비 변경·제약·후속). 언어는 `workflow.config.json` 의 `language`, 문장은 `plain-writing`.

**색인 갱신** — 계산해서 채운다. 규칙과 머지 충돌 처리는 `${CLAUDE_PLUGIN_ROOT}/procedures/sync/index.md`.

**갱신한 문서 점검** — `doc-verify` 로 **이번에 손댄 문서만** 템플릿과 대조한다. 빠진 절·빈 껍데기·남은 자리표시자를 리포트에 함께 낸다. **고치지 않는다.**

**ID 중복 확인** — 머지 전 마지막 관문이다(`traceability/conflict`). 같은 ID 가 두 번 발급됐으면 **리포트하고 멈춘다** — 재발급은 요구 표와 그 ID 를 가리키는 태그를 **전부 함께** 고쳐야 하므로 임의로 하지 않는다.

**PR 초안 제시** (선택 — 브랜치 작업일 때) — `7.summary/` 에 이미 있는 내용을 모아 **텍스트만 만든다.**

- **새 내용을 지어내지 않는다** — 요약·검증·리뷰 결과에 있는 것만이다.
- **올리지 않는다.** PR 을 만드는 명령은 가드가 막고, 치는 것은 사람이다.

**리포트 후 종료** — **커밋하지 않는다** → `/flow:commit`.

## 가드레일

- **커밋·push 금지.** 문서 수렴까지다.
- 코드↔계약 불일치는 **리포트만.** 자동 정정 금지.
- **도메인 문서의 `하위 기능` 절 밖을 건드리지 않는다** — 요구는 `/flow:prd`, 경계·용어는 `/flow:design` 의 자리다.
- **색인을 손으로 채우지 않는다** — git 과 태그에서 계산한다. 충돌도 손으로 풀지 않는다.
- **유닛 상태값은 `traceability/unit-state` 만 쓴다.** 멈춘 유닛을 `구현중` 으로 적지 않는다 — `정지(사유)` 다.
- **PR 을 만들지 않는다.** 초안 텍스트만 제시한다 — 외부 상태를 만드는 것은 사람이 한다.
- 설계 문서가 아예 없으면 경고하고 요약본만 만들고 끝낸다.

> **여기가 퇴장구다.** 건너뛰면 두 곳에서 걸린다 — `/flow:commit` 이 묻고, **git 훅이 커밋을 막는다**. 둘이 같은 규칙을 본다.
