# T9docs — 문서 정정 + `skills-map` 배선 표 정리 (D9)

네 관문 초록 — `lint.py` 검사 37 · 통과 37 · 실패 0 · 고장 0 · `gen_docs --check` 4곳 일치.
`plugins/**`·`scripts/**`·금지 목록의 doc 은 안 건드렸다. lint 가 빨간 적이 없어 `--only` 분리는 필요 없었다.

## 1. `레거시 면제 유닛` → 사실에 맞춤

**전수 grep** (`면제 유닛`·`면제로 표시된`·`레거시 면제`, 편집 가능 문서 전체) — 지시서의 자리 외 추가 발견 0건.
줄 번호는 이동해 있었다(185→그대로 · 235→그대로 · `01.architecture.md` 68→77, 332→341).

| 자리 | 무엇 |
|:--|:--|
| `guide/getting-started.md:185` | *"레거시 면제 유닛"* → *"면제로 등록된 경로(`gate.legacyExempt`)"* |
| `guide/getting-started.md:236` (신설 줄) | 항목 형식 변경 반영 — 문자열 글로브만이면 통과가 아니라 **확인(ask)**, 기록(`why`·`scope`)이 있어야 조용히 통과, 리포 전체급이면 무시. **규칙 본문은 복제하지 않고** `flow.topology.json` `gate` 절의 `legacy-exempt` 를 정본으로 지목 |
| `doc/01.architecture.md:77` | 면제 표의 행 — *"레거시 면제 유닛"* → *"면제로 등록된 경로(`gate.legacyExempt`)"* + 유닛이 아니라 **경로 글로브**라는 한 줄 |
| `doc/01.architecture.md:80-81` | *"면제 목록도 `flow.topology.json`이 갖는다"* — 이제 절반만 사실이라 정정: 규칙·판정은 topology `gate` 절, 레거시 면제 **항목**은 프로젝트 설정(`gate.legacyExempt`) |

**보고 남긴 것** — `doc/01.architecture.md:341` *"레거시 면제 게이트"* (남기는 것 표).
게이트라는 **기능**을 가리키고 유닛 개념을 말하지 않아 사실이 맞다. 안 고쳤다.

## 2. `doc/02.skills-map.md` — 배선 사본을 지우고 topology 를 가리킨다 (능력 7)

**지우기 전에 대조했다** — 옛 `커맨드가 무엇을 싣나` 표 14행 전부 + 뒤 문단 셋을 topology 와 항목 단위로
비교(T8 정비 뒤라 전부 일치). **그 표에만 있고 topology 에 없는 정보는 0건** — gatekeeper·reviewer 배선은
`agents` 에, D5 시점 근거는 각 조건의 `$why-exit` 와 `01.architecture.md`(T8 신설 절)에, `build` 조건 로드는
`conditional` 라벨 + `$note` 에 이미 있다. 지워서 잃은 것이 없다.

| 지운 것 | 어디로 |
|:--|:--|
| `커맨드가 무엇을 싣나` 표 14행 | `flow.topology.json` `commands.*.loads` |
| gatekeeper·reviewer 가 읽는 것 문단 | topology `agents` (+`$note`) |
| `build` 의 조건 로드 문단 | topology `commands.build.loads.conditional` 의 라벨 |
| 스킬 14개 표의 `싣는 커맨드`·`조각 수` 열 | `commands.*.loads` · `skills.*.fragments` |
| 각 스킬 절의 `싣는 쪽` 열 (14개 표) | `commands.*.loads`(모드·조건 포함)·`agents`·`direct_fragments` |
| 머리말의 *"이 지도가 소비자를 정하고 topology 가 데이터로 갖는다"* | 방향을 뒤집어 topology 단일 정본으로 |

| 남긴 것 (topology 가 표현 못 한다) | 왜 |
|:--|:--|
| `분할 기준은 소비자다` · `안 나눈 것` · 재획정 표 · T6 역추출 배치 근거 | 분할 근거 — 이 문서의 존재 이유 |
| 각 조각의 `담는 것`·`v1 근거` | 조각 내용 요약과 출처는 topology 에 없다 |
| **조각→조각 이름 참조** 4건 — `impact-analysis`→`code-graph/query` · `drift-check`→`service-boundary` · `testing/run`→`contract-gate/failure` · `impact-analysis`·`doc-verify`→`delegation` | topology 는 커맨드→조각만 표현한다. 지운 `싣는 쪽` 칸의 괄호 주석에만 있던 것을 산문으로 승격 — **지우면 잃을 뻔한 유일한 정보** |
| topology 읽는 문법 둘 — SKILL.md 없이 조각만 싣는 것이 정상 · 이름 참조는 loads 에 안 보인다 | 데이터가 스스로 말하지 않는다 |
| `v1 대비 실측` (설계 확정 시점 값이라 명시, 갱신 안 함) · `남은 위험` | 측정 기록과 위험 — topology 밖 |

새 `배선` 절이 topology 의 세 키(`commands.*.loads`·`agents`·`direct_fragments`)를 지목하고,
지운 이유(T8 이 드리프트 9건을 손으로 고쳤다 · `command-loads-parity` 는 `## 연결` 만 보고 이 문서는 검사 밖)를 적는다.

**연쇄 정정** — `guide/getting-started.md:57` 이 이 지도를 배선의 공동 정본으로 지목하고 있었다(정본 둘 = 능력 7 위반).
topology 단독 정본 + "왜는 지도" 로 고쳤다.

## 확인 못 해 남긴 것 · 추측

- 각 스킬 `SKILL.md` 본문이 지도의 `담는 것` 요약과 여전히 일치하는지는 전수 대조 안 했다 — 이 일의 범위 밖이고 `plugins/**` 는 다른 워커 소유다.
- **추측** — `ops-doc/safety` 의 직접 호출 경로는 `direct_fragments` 에 없다(등급 `자율` + SKILL.md 라우팅으로 닿는다고 판단해 그렇게 적었다). 실제 발동 실측은 안 했다.
