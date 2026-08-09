# T3 — 레거시 면제를 채우는 길 (D2)

## 무엇을 고쳤나

| 파일 | 무엇 |
|:--|:--|
| `flow.topology.json` 의 `gate` 절 | `legacy-exempt` 면제에 `whoFills`·`entryForm`(required·scopes·decide)·`tooBroad` 신설. `what` 을 *"면제로 표시된 유닛·경로"* → *"면제로 등록된 경로"* 로 정정 |
| `hooks/scripts/gate-source-write.sh` | 설정에서 온 면제를 **심사**한다 — 형식·넓이·만료. 판정값은 topology 의 `decide` 를 읽는다. 걸러진 면제는 **최종 판정이 deny 일 때만** 화면에 낸다 |
| `project-template/workflow.config.json` | `gate.$note` 를 항목 형식·scope·누가 채우나·예시로 교체. **`legacyExempt` 는 빈 배열 그대로** |
| `commands/setup.md` | `면제 구역 확정` 단계 신설(기존 코드가 있을 때만) · 요약 블록에 `면제 구역` 줄 · 가드레일 한 줄 |
| `commands/build.md` | **막혔을 때 푸는 순서** 표 4행 + 자기 승인 금지 3줄. `레거시 면제 유닛` → `면제로 등록된 경로` |
| `procedures/sync/index.md` | `면제 구역이 줄었나` 절 — 줄어드는 길의 관측 지점 |
| `scripts/lint.py` · `lint.test.py` | 검사 `exempt-fill-wired` 신설 + 픽스처 2 |
| `scripts/tests/hooks.test.sh` | 면제 케이스 6 → **55**(통과 371 → 420). topology 심사 규칙 단언 8줄 |

**새 절차 조각을 만들지 않았다.** 배선(`topology.commands.*.procedures`)이 내 소유가 아니라, 새 조각은 실릴 길이 없다.
그래서 `build` 몫은 본문에 압축해 넣었다 — 아래 `넘기는 것` 을 봐라.

## 어디에 선을 그었나 — 이 일의 판단

### 면제와 File Map 을 **가른다.** 섞으면 게이트가 이름만 남는다

과차단 시나리오를 세게 보니 두 가지가 한 키에 뭉쳐 있었다.

| 무엇을 쓰려다 막히나 | 옳은 답 |
|:--|:--|
| **이번 작업으로 고치는 레거시 파일** | task 문서 `File Map` 에 `[Mod] 경로` 를 적는다 — 사슬이 이어진다 |
| **task 문서를 붙일 뜻이 없는 코드** (벤더 배포본·생성물·남의 팀) | 면제다 — 이 구역은 flow 가 관리하지 않는다는 **선언**이다 |

**둘째 줄만 면제다.** 첫째 줄까지 면제로 풀면 "막히면 면제" 가 되고 그게 D1 과 같은 fail-open 이다.
그래서 `build` 의 회복 순서에서 **면제는 4번, 마지막**이다. 1번(File Map)이 대부분을 받는다 — 실측 ④ 가 그것이다.

> 선은 *"불편한가"* 가 아니라 *"이 파일에 요구를 붙일 뜻이 있나"* 다. 뜻이 있으면 File Map, 없으면 면제.

### 값을 못 세니 **보이게** 만든다 — 판정을 셋으로 가른다

넓이를 진짜로 재려면(면제가 게이트 대상의 몇 %인가) 매 쓰기마다 리포를 훑어야 해서 안 한다.
대신 **기록 없는 면제를 조용히 통과시키지 않는다.**

| 항목 상태 | 판정 | 왜 |
|:--|:--|:--|
| `why`·`scope` 가 있다 (+`scope: legacy` 면 `until`) | **allow** | 누가 왜 언제 열었나가 커밋에 남는다. 그 값을 받고 조용히 통과시킨다 |
| 글로브 문자열만 · 필드 누락 · 만료됨 | **ask** | 막지 않되 조용하지도 않다 |
| 와일드카드 없는 조각이 하나도 없다 (`**`·`**/*.ts`) | **deny** | 면제가 아니라 게이트 끄기다. 이 목록은 끄는 스위치가 아니다 |

**ask 를 고른 것이 이 설계의 무게중심이다.** deny 로 하면 과차단 → 사람이 훅을 끈다. allow 로 하면 남용 → 게이트가
이름만 남는다. `ask` 는 둘 다 아니다 — **일은 진행되고, 화면에 이유가 뜬다.** 만료도 같은 이유로 deny 가 아니라 ask 다:
면제가 사라지는 것이 아니라 **다시 판단 대상이 되는 것**이 만료다.

### 걸러진 면제가 문서·설정 쓰기를 막으면 그게 다시 과차단이다

심사에서 걸린 항목은 곧바로 판정을 내지 않고 `HOLD` 에 담아 두고, **최종 판정이 `deny` 일 때만** 그 메시지로 바꾼다.
`**` 가 설정에 있어도 `README.md`(not-source)·`spike/`·File Map 에 선언된 경로는 그대로 통과한다 — 실측 ③ 에 있다.

## 누가 언제 채우나

| 언제 | 누가 | 무엇을 |
|:--|:--|:--|
| 설치 시 (**기존 코드가 있을 때만**) | `setup` 의 `면제 구역 확정` | 벤더·생성물·`CODEOWNERS` 가 남을 가리키는 경로를 **근거와 함께** 후보로 내고 사람이 고른다 |
| 막혔을 때 | `build` 의 회복 순서 4번 | File Map(1번)이 답이 아닐 때만. **제안하고 사람 승인을 받는다** |
| 업데이트 모드 | `setup` | **더하기 전에 줄인다** — 만료된 항목·설계가 덮은 항목을 먼저 보여준다 |

- **기본은 면제 없음이다.** 템플릿은 빈 배열로 나가고, 감지 실패의 결과가 면제가 되지 않는다.
- **AI 가 자기 승인으로 늘리지 않는다.** `workflow.config.json` 은 게이트가 막지 않으므로(자기 근거를 잠그지 않으려고 — T2)
  **기계로는 막을 수 없는 자리다.** `build` 본문에 그 사실을 적고 약속으로 남겼다. 실측 ⑤.

## 면제가 줄어드는 길

| 길 | 등급 | 무엇 |
|:--|:--|:--|
| `until` 만료 → `ask` | **기계** | `scope: legacy` 는 `until` 이 필수다. 지나면 쓸 때마다 다시 묻는다 — 안 지우면 계속 걸린다 |
| `sync` 의 `면제 구역이 줄었나` | 약속 | 갱신한 File Map 이 면제 안 경로를 담았으면 알린다. **모든 코드 변경이 지나는 자리**라 빈도가 맞는다 |
| `setup` 업데이트 모드 | 약속 | 더하기 전에 만료·중복을 먼저 지운다 |

`scope` 를 둘로 가른 이유가 여기다 — `unmanaged`(벤더)는 줄어들 대상이 아니라서 만료가 없다.
안 가르면 벤더 항목이 영원히 만료 경고를 내고, **그 경고가 무시되면서 `legacy` 항목의 경고까지 같이 죽는다.**

## 남용을 막는 수단

| 수단 | 등급 | 막는 것 |
|:--|:--|:--|
| 리터럴 조각 필수 (`tooBroad` → deny) | **기계** | `**`·`*`·`**/*`·`**/*.ts`·`./**` — 리포 전체·확장자 전체 |
| 기록 없으면 `ask` | **기계** | 이유 없이 조용히 열리는 것 |
| `until` 만료 → `ask` | **기계** | 임시 면제가 영구로 굳는 것 |
| 검사 `exempt-fill-wired` | **기계(CI)** | **D2 의 재발** — 데이터가 *"setup 이 채운다"* 라 적었는데 그 커맨드가 키를 모르는 상태 |
| 사람 승인 · 면제 4순위 | 약속 | AI 가 막히자마자 면제로 푸는 것 |

**기계가 보증하는 것은 *보이는 것*이지 *참인 것*이 아니다.** `{"path":"lib/**","why":"레거시","scope":"unmanaged"}` 는
통과한다. 코드 전부가 `lib/` 에 있으면 그건 사실상 게이트 끄기인데 이 규칙으로 못 잡는다 — topology 의 `tooBroad.$note` 에
한계로 적어 두었다. 그 자리는 기록·리뷰·커밋이 받는다. **못 잡는 것을 잡는다고 적지 않는다.**

`exempt-fill-wired` 는 넣자마자 실제 결함을 하나 잡았다 — `build.md` 가 면제를 설명하면서 `gate.legacyExempt` 라는
키 이름을 한 번도 안 적고 있었다. 사람이 그 문서를 읽고 무엇을 고쳐야 하는지 알 수 없는 상태였고, 그게 D2 의 축소판이다.

## 실측

스크래치 repo `/tmp/flow-t3-legacy` — 코드는 `lib/billing`·`lib/auth`·`backend/api`·`vendor/thirdparty` 에,
유닛 하나(`doc/01.work/billing/00.invoice/`)에 task 문서 1개(`requirement: [BILL-1]`, File Map 은 `lib/billing/invoice.js` 하나).
훅 호출은 `hooks.test.sh` 방식 그대로(`--path`·`--root`·`--why`, exit 0/2/3). **끝나고 지웠다.**

### ① 지금 — 결함 재현 (면제 없음)

| 경로 | 판정 |
|:--|:--|
| `lib/billing/invoice.js` (File Map 안) | 통과 `declared-file-map` |
| `lib/auth/session.js` | **차단** `not-declared` |
| `backend/api/legacy_handler.py` | **차단** `not-declared` |
| `vendor/thirdparty/lib.js` | **차단** `not-declared` |

첫 유닛이 생기는 순간 File Map 밖 레거시가 전부 막힌다. **벤더 배포본까지 막힌다** — 여기에 task 문서를
붙일 방법은 없고, 고치기 전 리포 전체에서 `legacyExempt` 를 채우라는 지시는 0건이었다. D2 그대로다.

### ② 고친 뒤 — 절차대로 등록

```json
[{"path":"vendor/**",  "why":"벤더 배포본 — 우리가 고치지 않는다", "scope":"unmanaged", "added":"20260809"},
 {"path":"backend/**", "why":"역추출 전 · BILL-0 으로 덮는다",     "scope":"legacy", "until":"20261231", "added":"20260809"}]
```

| 경로 | 판정 |
|:--|:--|
| `vendor/thirdparty/lib.js` | **통과** `legacy-exempt` — 면제: 벤더 배포본… |
| `backend/api/legacy_handler.py` | **통과** `legacy-exempt` — 면제: 역추출 전 · BILL-0… |
| `lib/auth/session.js` | **차단** `not-declared` — **면제 밖은 그대로 막힌다** |
| `lib/billing/invoice.js` | 통과 `declared-file-map` |

기록 등급도 갈린다 — 같은 `backend/**` 라도 문자열만이면 `ask (exempt-unrecorded)`,
`until` 없으면 `ask (exempt-unrecorded)`, `until: 20260101` 이면 `ask (exempt-expired)`.

### ③ 면제 남용

| 넣은 값 | `lib/auth/session.js` | `README.md` | `src`→`lib/billing/invoice.js` | `spike/x.ts` |
|:--|:--|:--|:--|:--|
| `["**"]` | **차단** `exempt-too-broad` | 통과 `not-source` | 통과 `declared-file-map` | 통과 `spike` |
| `["**/*.js"]` | **차단** `exempt-too-broad` | — | — | — |
| `["*"]`·`["**/*"]`·`["./**"]` | **차단** `exempt-too-broad` | — | — | — |

차단 화면:

```
⛔ flow gate: 면제 항목이 너무 넓어 무시했다
   왜: gate.legacyExempt 의 `**` 은 와일드카드 없는 경로 조각이 없다 — 리포 전체·확장자 전체 면제다
   → 면제할 구역을 경로로 좁혀 적으세요 (예: `vendor/**`). 이번에 고치는 파일이면 면제가 아니라
     task 문서 File Map 에 `backend/api/legacy_handler.py` 을 적으세요. 이 목록은 게이트를 끄는 스위치가 아닙니다.
```

**넓은 면제가 문서·spike·선언된 경로를 막지 않는다** — 그게 다시 과차단이라서다.

### ④ 회복 경로 1(File Map)이 실제로 푸나

`lib/auth/session.js` 가 `not-declared` 로 막힌 상태에서 task 문서에 `- \`[Mod] lib/auth/session.js\`` 한 줄을 더하니
곧바로 `allow (declared-file-map)`. **면제 없이 풀린다.** 이게 `build` 회복 순서 1번이 4번보다 위에 있는 근거다.

### ⑤ 훅 모드 · 자기 승인 경로

- `PreToolUse` stdin JSON 으로 부르면 기록 없는 면제가 `{"permissionDecision":"ask", ...}` 로 나간다 (exit 0). 실측했다.
- `--path workflow.config.json` → `allow (not-source)`. **설정을 스스로 고칠 수 있다** — T2 가 의도한 것이고(자기 근거 잠금 방지),
  그래서 면제 자기 승인은 기계로 못 막는다. 약속으로 남겼다.

### 되돌림 확인 — 케이스가 정말 지키나

| 무엇을 되돌렸나 | 훅 테스트 |
|:--|:--|
| 넓이 규칙 (`has_literal_segment` → 항상 True) | **실패 12** |
| 글로브 정규화 (`norm_pat` → 그대로) | **실패 6** |
| 심사 (맞으면 무조건 allow) | **실패 10** |
| topology 에서 `decide.unrecorded` 삭제 | **실패 1** |
| 복원 | 실패 0 |

정규화 케이스는 **테스트를 쓰다가 찾은 결함**이다. `./vendor/**` 는 아무것에도 안 맞아 **조용히 죽은 면제**가 됐다 —
사람은 면제를 걸었다고 믿는데 계속 막히고, 그게 과차단의 입구다. 대상 경로와 같은 규칙으로 글로브도 정규화했다.

### 완료 조건

```
python3 scripts/lint.py            검사 35 · 통과 35 · 실패 0 · 검사기 고장 0 · 대상 0건 0
python3 scripts/lint.test.py       검사 35 전부 통과·위반 픽스처를 갖췄다
bash scripts/tests/hooks.test.sh   통과 420 · 실패 0   (371 → +49)
python3 scripts/gen_docs.py --check  생성물 4곳이 정본과 같다
```

## 넘기는 것

| 무엇 | 왜 |
|:--|:--|
| **`procedures/build/gate-denied.md` 조각** | 회복 순서 표의 제 자리는 조건부 절차 조각이다(막혔을 때만 실린다). **배선은 `topology.commands` 라 내 소유가 아니다.** 지금은 `build.md` 본문에 +9줄로 넣었다 |
| **`guide/getting-started.md:185`** — *"레거시 면제 유닛"* | 유닛 면제는 **기계에 없었다**(글로브만 본다). topology 에서 문구를 고쳤으니 guide 도 `면제로 등록된 경로` 로 맞춰야 한다. 다른 워커 소유 |
| **`guide/getting-started.md:235`** — 넓으면 `gate.legacyExempt` 로 좁히라 | 틀리진 않지만 **항목 형식이 바뀌었다.** 문자열만 적으면 이제 통과가 아니라 `ask` 다 |
| `doc/01.architecture.md:68·332` 의 *"레거시 면제 유닛"* | 같은 문구. `doc/**` 는 내 소유가 아니다 |
| `commands/prd.md`·`procedures/design/*` 의 면제 기입 지점 (W3 2-b 제안) | **일부러 안 넣었다.** 설계 국면에서 면제를 열면 *"설계 대신 면제"* 가 된다. 설계의 답은 File Map 이다 |
| 면제 사용 로그 | 게이트가 면제로 통과시킨 횟수를 파일에 남기면 남용이 수치로 보인다. **훅이 쓰기를 하게 되어** 안 넣었다 |

**추측**

- **`ask` 가 얼마나 오래 물어보나.** Claude Code 의 권한 프롬프트에 *"이번 세션은 묻지 않음"* 류가 있으면
  기록 없는 면제가 한 번의 승인으로 조용해질 수 있다. 확인 안 했다 — 그러면 `ask` 층의 값이 세션 단위로 깎인다.
- **`unmanaged` 후보 감지의 적중률.** `vendor/`·`@generated`·`CODEOWNERS` 를 근거로 적었지만 실제 레거시 리포에서
  몇 건이나 잡히는지는 안 세어 봤다. 못 잡으면 `build` 가 막힐 때 제안하는 쪽으로 떨어진다 — 그 폴백은 있다.
- **`ask` 의 실제 빈도.** T2 가 `sourceGlobs` 를 비워 게이트 대상이 넓어졌는데, 그 위에서 기록 없는 면제가
  얼마나 자주 프롬프트를 띄울지는 실제 레거시 리포를 돌려 봐야 안다.
