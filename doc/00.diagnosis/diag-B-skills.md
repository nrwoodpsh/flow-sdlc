# 진단 B — 스킬 층 (flow 0.8.0, 16개)

대조한 것: `skills/*/SKILL.md` 16개 · `commands/*.md` 14개의 `## 연결` · `agents/*.md` · `.claude/rules/plugin-authoring.md` · `scripts/lint-docs.py`.

## 사실 먼저 — 무엇이 얼마나 실리나

스킬 본문은 발동될 때 통째로 실린다. 커맨드가 `## 연결`에 적은 스킬을 합치면:

| 커맨드 | 실리는 스킬 줄 | 전체(2315줄) 대비 |
|:--|--:|--:|
| `/flow:design` | 1107 | 48% |
| `/flow:verify` | 1019 | 44% |
| `/flow:spec` | 1006 | 43% |
| `/flow:run` | 983 | 42% |
| `/flow:sync` | 901 | 39% |
| `/flow:review` | 849 | 37% |
| `/flow:commit` | 215 | 9% |

가장 자주 불리는 것이 가장 크다 — `traceability` 332줄이 14개 중 8개 커맨드에, `doc-verify` 307줄이 3개(+`gatekeeper`), `code-graph` 212줄이 4개에 걸린다.

**16개 전부 어떤 커맨드의 `## 연결`에 이름이 있다.** 안 불리는 스킬은 없다 — 문제는 호출 여부가 아니라 **입도**다.

---

## 1) 남길 것

- **`traceability`의 레벨 판별 질문** — `traceability/SKILL.md:14-33`. *"도메인을 하나 더 추가하면 이 요구가 거기에도 걸리나"* 로 물어 `append-only` 위반을 막는다. `"여러 도메인에 걸치나"`를 왜 안 쓰는지까지 근거가 붙어 있다(`:23`). 이 층에서 가장 값어치 하는 한 문단.
- **`default-reference`의 위임 판정** — `default-reference/SKILL.md:64-93`. *"결론만이면 위임 · 원문이면 직접, 둘 다 걸리면 위임"* + **숫자 임계를 두지 않는 이유**(`:93`). `impact-analysis:17`이 이걸 이름으로 가리켜 실제로 정본이 하나다. 유일하게 제대로 작동하는 정본 참조.
- **`test-spec`의 기대값 역산 금지** — `test-spec/SKILL.md:53-77`. 출처를 넷으로 못 박고(`:66-73`), *"기대값 출처 칸이 비면 역산이다"*(`:249`)라는 **기계로 확인되는 판정**을 만들었다. `tdd-verify:62`가 이름으로 가리킨다.
- **`contract-gate`의 실패 원인 이분법** — `contract-gate/SKILL.md:52-77`. `command not found`(환경) vs `TS2322`(계약)를 가르고 *"구분하지 않으면 계약을 3회 고치려 시도하고 3회 다 실패한다"*(`:61`). 오프라인 케이스까지 있다(`:69-77`). `tdd-verify:66`이 같은 규칙을 상속한다.
- **`code-review`의 "없으면 어떻게 되나" 표** — `code-review/SKILL.md:14-21`. 층마다 도구가 없을 때 **무엇을 못 잡게 되는지**를 적는다. `"안 봤다"를 "문제없다"로 적지 않는다`(`:125`)와 짝이다.
- **`code-graph`의 두 모드 능력 대조** — `code-graph/SKILL.md:36-44`. 축소 모드에서 **데이터 흐름은 아예 불가능**(`:41`)임을 명시해, 축소 결과가 그래프 분석으로 읽히는 것을 막는다.
- **`usecase`의 규칙 레벨 3단** — `usecase/SKILL.md:92-113`. `R`/`DR`/`SYS`를 걸리는 범위로 가르고 *"올린 규칙은 `참조:`로 번호만"*. `test-spec:106-133`이 이 번호로 검증 범위를 정하고 `doc-verify:125`가 채점한다 — **세 스킬이 한 규약으로 실제로 이어지는 유일한 사슬**이다.
- **`plain-writing`의 `줄이지 않는 것`** — `plain-writing/SKILL.md:37-46`. 축약이 거짓말로 바뀌는 경계(조건절·안 본 것·추측 표기·수치 조건)를 박았다. 이 층 전체의 안전장치다.
- **`impact-analysis`의 `안 본 범위` 강제** — `impact-analysis/SKILL.md:46-56`. *"비었으면 옮기다 지운 것이다"*(`:56`)로 빈 칸을 결함으로 만든다.

## 2) 버릴 것

- **`doc-template`의 절 등급 표** — `doc-template/SKILL.md:14-18`. `doc-verify/SKILL.md:68-72`와 같은 표다(행 유사도 0.77·0.79 — 검사기 임계 0.85 **직하로 통과한다**). 등급을 쓰는 쪽은 `doc-verify` 하나다. `doc-template`에 둘 이유가 없다.
- **`default-reference`의 `/flow:setup` 행** — `default-reference/SKILL.md:15`. **`setup.md`는 `## 연결`에 `default-reference`를 적지 않는다**(확인: `grep default-reference commands/setup.md` → 없음). 안 실리는 커맨드의 행이라 다른 13개 커맨드가 그 줄 값을 낸다. description의 `모든 커맨드가 쓴다`도 이 때문에 거짓이다.
- **`tdd-verify`의 화면 테스트 도구 표** — `tdd-verify/SKILL.md:18-21`. 같은 `test.browser` 규약이 `test-spec:20`·`test-spec:49`·`theme-apply:19`에도 있다. `tdd-verify`는 *"여기서 도구·모드를 정하지 않는다"*(`:16`)고 적고도 표를 갖고 있다 — 정본은 `workflow.config`고 스킬은 아무 것도 안 더한다.
- **`tdd-verify`의 `기록` 절** — `tdd-verify/SKILL.md:44-57`. `test-spec:171-206`의 출력 형식과 같은 자리를 정한다. `tdd-verify`는 `/flow:verify`에서 `test-spec`과 **항상 같이 실린다**(둘 다 verify·build의 연결에 있다) — 두 번 적을 필요가 없다.
- **`drift-check`의 계약 범위 알림 절** — `drift-check/SKILL.md:76-92`. `code-graph:159-187`(정본)·`impact-analysis:29,51,63`이 같은 것을 말한다. **같은 개념이 세 스킬에 흩어져 있고**, 서술이 달라 검사기의 유사도(0.62 이상 쌍 0건)에 안 걸린다.
- **`doc-verify`의 표↔그림 발견 표** — `doc-verify/SKILL.md:144-148`. 바로 위 `:135`·`:151`에서 *"판정표는 `usecase`에 있다. 여기 옮겨 적지 않는다"*고 선언하고 `usecase:171-173`을 그대로 옮겼다(유사도 0.71).
- **`code-audit`의 `/flow:review 5층` 참조** — `code-audit/SKILL.md:39`. 다른 스킬의 **층 번호**를 가리킨다. `plugin-authoring:27`이 금지한 형태이고, 층이 하나 늘면 조용히 어긋난다. `claude-security`가 본다는 사실만 남기면 된다.

## 3) 고칠 것

**(a) 자율/호출 전용 2등급이 `description`에 구현돼 있지 않다.**
`plugin-authoring:30-38`은 **자율 7개**(`impact-analysis`·`plain-writing`·`tdd-verify`·`drift-check`·`code-audit`·`code-review`·`ops-doc`)에 *"발동 조건을 쓴다 — 이게 없으면 커맨드 밖에서 안 뜬다"*, 호출 전용 9개에 *"`/flow:X 가 쓴다`를 지우지 않는다 — 그 절이 오발동을 막는 신호다"*라고 정한다. 실제 description:

| 스킬 (자율) | description 끝 | 발동 조건 |
|:--|:--|:--|
| `ops-doc` | `…사용자가 직접 요청할 수도 있다` | ✅ |
| `impact-analysis` | `/flow:build·/flow:spec·/flow:design 이 쓴다` | 🟡 `고치기 전`만 |
| `plain-writing` | `문서를 만들거나 고치는 커맨드가 쓴다` | ❌ |
| `tdd-verify` | `/flow:build 루프·/flow:verify 가 쓴다` | ❌ |
| `drift-check` | `/flow:commit·/flow:run 이 쓴다` | ❌ |
| `code-audit` | `/flow:build·/flow:review 가 쓴다` | ❌ |
| `code-review` | `/flow:review·/flow:run 이 쓴다` | ❌ |

**7개 중 6개가 오발동 억제 신호를 달고 있다** — 등급이 사실상 뒤집혔다. 규칙 파일이 아니라 파일이 정본이므로, v2는 등급을 description 문형으로 강제하거나 등급 자체를 걷어야 한다.

**(b) 다이어그램 표기 정본이 그것을 쓰는 커맨드에 실리지 않는다.**
정본은 `doc-template/SKILL.md:42-85`(`!pragma layout smetana`). `doc-template`을 `## 연결`에 적은 커맨드는 **`spec.md` 하나뿐**이다. 그런데 `design.md:127`("표기는 `doc-template`")·`publish.md:81`이 이름으로 가리키고, `usecase:134`도 가리키며, `doc-verify:117`은 그 규칙으로 **채점한다**. `prd.md:145`는 유스케이스 그림을 그리라고 하면서 `doc-template`을 안 싣는다. **그림을 그리는 커맨드는 규약을 못 읽고, 안 그리는 커맨드가 갖고 있다.**

**(c) `traceability` 332줄이 성격이 다른 6개 규약의 묶음이다.**
`:10-46` 레벨·라우팅 / `:48-104` ID 체계·이름 / `:115-170` 동시 발급 충돌 / `:172-212` 태깅·gap / `:214-227` 요구 상태값 / `:229-299` **유닛·task 상태 계산·재개 지점**. 마지막 것은 추적 축이 아니라 진행 상태 계산이고 소비자가 다르다(`/flow:build`·`/flow:ask`·`/flow:run`, 근거 `:279-283`). `/flow:verify`는 gap 판정 20줄을 쓰려고 332줄을 싣는다.

**(d) `theme-apply` 154줄이 `/flow:design`에 한 줄을 주려고 실린다.**
`design.md:128`이 필요한 것은 *"토큰 정본은 `00.ref/04.theme/` · 재정의 금지"* 하나다. 나머지(스펙 착지처·Tier 1·2·3·적용 절차·출력 형식)는 `/flow:theme` 전용이다.

**(e) `tdd-verify` + `test-spec`은 한 스킬이다.**
319줄이 "테스트를 어떻게 명세하고 돌려 판정하나" 하나를 말하며 서로를 4곳에서 가리킨다(`tdd-verify:50,62,63` / `test-spec:147`). 두 커맨드(`build`·`verify`) 모두 **둘을 같이** 싣는다 — 분리가 로드를 줄이지 않는다. `/flow:spike`만 `tdd-verify`를 홀로 쓴다(`spike.md:16`).

**(f) 번호로 남의 파일을 가리키는 곳 7군데.**
`drift-check:46`(`/flow:commit` 절차 2)·`:47`(`/flow:build` 절차 3-1) · `doc-template:84`(`/flow:publish` 절차 3-1) · `traceability:225`(절차 2') · `doc-verify:91`·`:300`(`/flow:run` 3층) · `code-audit:39`(`/flow:review` 5층). `plugin-authoring:27`이 *"번호를 붙이면 사용자가 절을 하나 더할 때 밖의 참조가 조용히 어긋난다"*고 금지한 형태다. 검사기 8번은 **번호 붙은 제목만** 잡고 번호로 가리키는 참조는 안 잡는다.

**(g) description의 `누가 쓴다`가 세 곳 틀렸다 — 검사기가 한 방향만 본다.**
`lint-docs.py:401-446`은 *description이 주장한 커맨드가 그 스킬을 적었나*만 확인한다. 반대 방향(커맨드가 적었는데 description에 없다)과 `/flow:` 토큰이 없는 문장은 **검사가 아예 안 돈다**:

| 스킬 | description | 사실 |
|:--|:--|:--|
| `default-reference` | `모든 커맨드가 쓴다` | **거짓** — `setup.md`가 안 적는다 |
| `tdd-verify` | `/flow:build 루프·/flow:verify` | `spike.md:16`도 쓴다 |
| `doc-verify` | `/flow:review doc·gatekeeper` | `sync.md`·`run.md`도 쓴다 |
| `traceability` | `대부분의 커맨드가 쓴다` | 8/14 — 참이지만 확인 불가 |

description은 매 턴 실린다 — 위 두 줄은 **매 턴 실리는 거짓말**이다.

## 4) 이 층의 가장 큰 구조적 결함

**스킬이 규약의 단위이면서 동시에 로드의 단위다. 부르는 쪽이 필요한 조각만 가져올 방법이 없다.**

`/flow:design` 한 번에 스킬 1107줄이 실린다. 그중 실제로 쓰는 것은 레벨 판별(~35줄)·유스케이스 입도(~40줄)·위임 판정(~30줄)·`04.theme` 금지(1줄) 정도다. `traceability` 332줄 중 `동시 발급 충돌`(56줄)·`유닛 상태 계산`(70줄)은 `/flow:design`에 아무 일도 하지 않는다.

**증상이 전부 여기서 나온다.** (c)의 묶음화·(d)의 154:1·(e)의 안 줄어드는 분리는 같은 원인의 세 얼굴이다. 그래서 저자에게 남는 선택은 둘뿐이다 — **큰 스킬 하나로 묶어 통째로 싣거나**(→ `traceability`·`doc-verify`), **쪼개고 정본을 이름으로 가리키거나**(→ 개념 삼중화: `서비스 경계`가 `code-graph`·`impact-analysis`·`drift-check` 세 곳에, `test.browser`가 네 곳에). 검사기는 **줄 단위 유사도 0.85**로만 후자를 잡으므로(`lint-docs.py:643`), 서술을 바꿔 쓴 중복은 전부 통과한다 — 위 두 개념 쌍의 유사도 ≥0.62 일치는 **0건**이다.

v2에서 달라져야 하는 것: **규약의 정본과 로드 단위를 분리한다.** 스킬 하나 = 한 정본이 아니라, **호출하는 쪽이 지정한 조각만 실리는 형태**여야 한다. 그 축을 안 바꾸면 v2도 "묶어서 비용을 내거나 흩어서 드리프트를 내거나"의 같은 자리로 돌아온다.

### 부수 관찰 (추측)

- **추측** — `default-reference`의 커맨드별 표는 각 커맨드의 `## 연결`·`## 입력`과 같은 정보를 두 번째로 적은 것으로 보인다. `:38`이 *"커맨드의 `## 연결`에 적는 것이 기제다. 여기 적은 것은 새 커맨드가 빠뜨렸을 때의 근거"*라고 스스로 인정한다 — 검사기가 대조하면 표는 필요 없어진다.
- **추측** — `code-audit` 45줄은 `code-review` 4층의 체크리스트다(`code-review:32`). `/flow:build`가 독립으로 쓰기에 분리했겠으나, v2에서 build의 셀프체크와 review의 층을 한 규약으로 두면 스킬 하나가 준다.
