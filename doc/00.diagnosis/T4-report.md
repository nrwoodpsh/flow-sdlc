# T4 — `entry.content` 를 퇴장 조건으로 재획정

닫는 것은 D5 다. **D3(`who` 축)은 T1 이 이미 닫았고 건드리지 않았다** — `who` 값은 그대로 옮겨만 왔다.
네 관문 전부 초록이다 — `lint` 34·실패 0·고장 0·대상 0건 0 · `lint.test` 34 · 훅 371 · 생성물 4곳.

## 데이터 모양 — `entry` 옆에 `exit` 를 두고, 시점 축은 `content` 에만 뒀다

```
commands.{name}.entry = { machine[], content[], promise[] }    시작할 때 이미 있는 것으로 판정
commands.{name}.exit  = { content[] }                          끝낼 때 그 커맨드가 만든 것으로 판정
```

**`when: enter|exit` 를 항목마다 붙이는 쪽을 버렸다.** 키를 빠뜨리면 기본값이 조용히 생기고,
그 기본값이 곧 D5 다(안 적었더니 진입으로 읽혔다). **자리가 곧 선언이면 빠뜨릴 수가 없다** —
`topology-pending` 이 11개 커맨드 전부에 `exit` 키와 그 안의 `content` 를 요구한다.

**`entry` 라는 키 이름은 안 바꿨다.** `setup.md` 가 `commands.setup.entry` 를 가리키는데 그 파일은
내 소유가 아니다. 이름을 바꾸면 고칠 수 없는 자리가 거짓이 된다.

**`exit` 에 `machine`·`promise` 를 두지 않았다.** 빈 껍데기가 되기 때문이다 — 훅은 도구 호출마다
보므로 판정 시점이 도구 호출이고, 약속은 판정하는 자가 없어 시점이 없다. 없는 시점을 적는 것이
"기계라 적고 훅은 없던" H1 과 같은 종류의 거짓이다. 필요해지면 그때 키를 더한다.

**남은 부정확 하나를 적어 둔다.** `entry.promise` 에는 진입 조건(`has-config`)과 상시 규칙
(`no-self-verify`·`append-only`)이 섞여 있다. 시점 축이 `content` 에만 있으니 그 섞임은 그대로다 —
D5 의 범위가 아니라 손대지 않았지만, **약속에도 같은 종류의 부정확이 남아 있다**는 것은 사실이다.

## 조건 5개를 어디로 보냈나 — 전부 퇴장. 하나도 지우지 않았다

| 조건 | 어디로 | 근거 |
|:--|:--|:--|
| `prd.level-decision` | **퇴장** | 레벨이 맞는지는 요구 초안이 나와야 본다. `prd.md` 가 이미 *"착지 전에"* 라 적었다 — 본문이 퇴장이었고 데이터만 진입이었다 |
| `design.requirement-covered` | **퇴장** | 덮었는지는 설계 요소가 나와야 보인다 |
| `build.contract-followed` | **퇴장** | 구현을 해 봐야 안다 |
| `verify.coverage-gap` | **퇴장** | 감사 결과 그 자체다. 돌리기 전에는 분류표가 없다 |
| `review.finding-severity` | **퇴장** | 등급은 발견이 나와야 매긴다 |

**`design.requirement-covered` 를 `build` 의 진입으로 올리는 쪽도 검토했고 버렸다.** 그러면 같은
사실을 두 자리가 갖고(정본 단일성 위반), 구멍을 고칠 수 있는 쪽(`design`)이 아니라 다음 국면에서
늦게 잡힌다. 전환에서 보는 것은 어차피 `design` 의 퇴장 조건이라 얻는 것이 없다.

**그래서 `entry.content` 는 11개 전부 비었다.** 채울 것을 발명하지 않았다 — `build` 의 계약 컴파일
같은 후보는 판정자가 `verifier`(도구를 돌리는 쪽)라 `judges` 에 못 들어가고, 커맨드가 스스로
돌리는 것이라 정의상 약속이다. 없는 게이트를 자리 채우려고 만드는 것이 이 프로젝트가 고치려는 병이다.

## 퇴장 조건은 누가 언제 부르나

**그 커맨드가 끝내면서 `gatekeeper` 에 넘긴다.** 이 구조는 이전과 같고 — 부르는 것은 진행하는
쪽이지만 **판정하는 것은 `gatekeeper`** 다 — 달라진 것은 *언제* 를 데이터와 본문이 같이 말한다는 점이다.

- 커맨드 본문의 라벨이 `**내용 · 퇴장**` 이고, 위임 블록에 **언제** 를 적었다
  (`구현·단위 검증을 끝낸 뒤, 기록 전` · `분류표가 나온 뒤 · 리포트 확정 전`).
- `build.md` 의 `종료 조건` 에 **퇴장 게이트 통과**를 한 줄로 넣었다 — 미충족이면 끝난 것이 아니다.
- 부르는 것 자체는 여전히 약속이다. 기계가 볼 수 있는 것은 **지시가 본문에 있나**(`gatekeeper-delegation`)와 **무엇을 넘기는지 id 로 적나**(`gate-item-named`)까지다.

## `next` 의 전환 게이트가 보는 것 — 직전 커맨드의 퇴장 조건

| 등급 | 전환에서 |
|:--|:--|
| 기계 | 훅이 이미 봤다 — 다시 판정하지 않는다 |
| 내용 | **직전 커맨드의 `exit.content`** 를 준다. 다음 커맨드에 `entry.content` 가 있으면 그것도 함께 준다 |
| 약속 | 아무도. 넘어갔다는 사실만 적는다 |

- 직전 커맨드가 끝내면서 이미 걸었으면 **결과를 받아 쓰고**, 결과가 없으면 **`next` 가 거기서 건다.**
  같은 게이트를 두 번 돌리지도, 안 돈 채 넘기지도 않는다.
- **이것이 D5 가 고쳐진 자리다.** 전에는 *다음* 커맨드의 내용 조건을 그 커맨드가 시작하기도 전에
  판정시켰다 — 5개 중 3개가 원리상 판정 불가였다. 이제 전환에서 보는 것은 이미 만들어진 것이다.

## 검사기 — 둘을 넓히고 셋을 신설했다 (31 → 34)

| 검사 | 무엇을 잡나 | 왜 이 자리에 |
|:--|:--|:--|
| `topology-pending`(확대) | `exit` 키·`exit.content` 누락 · `exit` 에 없는 등급을 넣는 것 | 모양을 지키는 것이 먼저다. 대상 11 커맨드 |
| `gatekeeper-delegation`(확대) | `entry`·`exit` **양쪽**의 내용 조건에 위임 지시가 있나 | `entry` 만 보게 두면 **대상 0건으로 조용히 통과**한다 |
| `gate-judge-independence`(확대) | 같음 — `who` 를 양쪽에서 본다 | 같음. T1 의 `who` 축을 잃지 않기 위해 |
| **`gate-timing`**(신설) | `entry.content` 인데 `producedBy` 가 없다/자기 자신이다/`after` 밖이다 · `exit.content` 에 `producedBy` 가 있다 | 진입이라 적으려면 **그 대상을 만든 앞 커맨드**를 대야 한다 |
| **`gate-item-named`**(신설) | 위임 지시가 넘길 항목 id 를 본문에 안 적은 것 | `gatekeeper.md` 가 *"기준을 발명하지 않는다"* 라 적는다 |
| **`gate-timing-shown`**(신설) | 본문이 `내용` 에 시점을 안 적은 것 · `기계`·`약속` 에 시점을 붙인 것 | **사용자는 데이터가 아니라 본문을 읽는다.** D5 는 본문에도 있었다 |

**검사를 셋으로 가른 이유는 T1 과 같다** — 한 id 에 규칙을 묶으면 위반 픽스처가 하나만 건드려도
통과라 나머지가 사문화돼도 테스트가 못 잡는다. `entry-grade-parity` 는 등급 대조를 그대로 갖고,
시점 표시는 `gate-timing-shown` 이 갖는다. 시점을 안 적은 라벨은 `entry-grade-parity` 에서
**데이터에 있는 시점을 가리킨 것으로 읽어** 두 검사가 같은 흠을 두 번 세지 않게 했다.

**`gate-timing` 의 한계 둘.**

1. **entry 가지는 지금 repo 에서 대상이 0이다**(내용 조건이 전부 exit 로 갔다). 검사 전체 대상은
   exit 5건이라 0건은 아니지만, 그 가지는 `lint.test.py` 의 위반 픽스처만 밟는다.
2. **`producedBy` 는 선언이다.** `contract-followed` 를 진입으로 올리고 `producedBy: design` 이라
   적으면 통과한다 — 조건의 `what` 이 실제로 무엇을 보는지는 기계가 못 읽는다. 막히는 것은
   *아무 앞 커맨드도 못 대는 경우*까지다. `machine` 의 `enforcedBy` 가 훅 실재로 증명되는 것과
   달리 여기는 증명 축이 없다.

## 되돌림 확인 — 아홉 개 전부 실패로 떨어졌고 원복했다

| 되돌린 것 | 결과 |
|:--|:--|
| `build` 의 `exit.content` → `entry.content` | `gate-timing` 실패 1 |
| `verify` 의 `exit` 키 삭제 | `topology-pending` 실패 1 |
| `verify` 에 `exit.promise` 신설 | `topology-pending` 실패 1 |
| `review` 의 `exit.content.who` → `reviewer` | `gate-judge-independence` 실패 1 — **T1 의 축이 exit 에서도 산다** |
| `build.md` 의 `내용 · 퇴장` → `내용` | `gate-timing-shown` 실패 1 |
| `build.md` 의 `내용 · 퇴장` → `내용 · 진입` | `entry-grade-parity` 실패 2 |
| `build.md` 에서 항목 id 삭제 | `gate-item-named` 실패 1 |
| `build.md` 에서 위임 지시 삭제 | `gatekeeper-delegation` 실패 1 |
| `prd.md` **표** 라벨에서 시점 삭제 | `gate-timing-shown` 실패 1 — 표 형식도 본다 |

**대상 0건 경로를 따로 확인했다.** `_content_items` 를 `entry` 만 보게 좁히면
`gatekeeper-delegation`·`gate-item-named`·`gate-timing` 이 **대상 0건**으로 떨어지고
`gate-judge-independence` 는 대상 1(판정자 선언만)이 된다. 이때 `lint.py` 는 실패 0 이지만
`대상 0건 3` 을 이름과 함께 출력하고, `lint.test.py` 는 실패 6 으로 잡는다 — **두 층이 다 부른다.**

## 따라 고친 것 전수

| 파일 | 무엇 |
|:--|:--|
| `flow.topology.json` | 머리말에 진입/퇴장·`producedBy`·시점 축 근거 · `grades.content` 설명 · 커맨드 11개에 `exit` · 내용 조건 5개 이동(`$why-exit` 남김) · `agents.gatekeeper.$note` |
| `scripts/lint.py` | 위 표의 검사 6개 · `_content_items`·`_gate_labels`·`_slot_grades` 헬퍼 |
| `scripts/lint.test.py` | 픽스처 — `_topology`·`_cmd_topo`·`_judge`·`_grade_doc` 에 `exit` · `_timing`·`_timing_doc`·`_GK_ITEM` 신설 · 케이스 3쌍 추가 |
| `commands/build.md`·`verify.md`·`review.md` | 게이트 절 라벨·위임 블록의 시점 · `build` 는 `종료 조건` 에 퇴장 게이트 한 줄 |
| `commands/prd.md`·`design.md` | `## 진입 조건` → `## 게이트` · 표 라벨에 시점과 항목 id · 퇴장 근거 한 줄 |
| `commands/next.md` | 전환 게이트 표를 `exit.content` 로 · 결과를 받아 쓰거나 거기서 거는 규칙 |
| `commands/sync.md`·`commit.md`·`spike.md`·`publish.md` | 정본 가리킴에 `exit` 추가 · *"`entry.content` 가 비어 있으니"* → 양쪽 |
| `agents/gatekeeper.md` | description · 무엇을 읽나 · 입력 · **대개 퇴장 게이트다**를 존재 이유에 |
| `procedures/verify/coverage.md`·`design/system.md`·`design/feature.md` | 게이트 서술에 `exit.content` 와 항목 id |

`commands/setup.md`·`project-template/**`·`skills/**`·`doc/02.skills-map.md` 는 손대지 않았다.

## 넘기는 것 — 내가 고치지 않았다

1. **`doc/02.skills-map.md:246` 이 *"`gatekeeper` 는 … 각 커맨드의 진입 조건만 읽는다"* 라 적는다.**
   이제 대개 퇴장 조건이다. **남의 파일이라 안 고쳤다**(T8 소유).
2. **`doc/01.architecture.md` 에 시점 축이 없다.** 강제력 3등급 표는 그대로 맞지만(등급은 안 건드렸다),
   진입/퇴장 분리는 그 문서에 기록되지 않았다. `README.md:35`·`CLAUDE.md:14`·`guide/getting-started.md:14`
   도 topology 를 *"위상·진입 조건·게이트 면제"* 로 적는다 — 세 곳 다 내 소유 밖이다.
3. **모드로 갈린 커맨드에 게이트가 하나다**(W1 3절 (자)). `coverage-gap` 은 `coverage` 범위에서만
   뜻이 있어 `verify.md` 에 그 사실을 한 줄 적었지만, **데이터는 커맨드 단위 그대로다.** 모드별
   게이트는 W1 이 따로 제안한 항목이라 손대지 않았다.
4. **워킹트리에 T6 의 변경이 함께 있다** — `doc/02.skills-map.md`·`skills/traceability/references/reverse-*.md`·
   `doc/00.diagnosis/T6-report.md`. 내 것이 아니다.
