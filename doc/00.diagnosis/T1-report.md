# T1 — 검사 신설과 그 검사가 잡은 것

닫는 것은 D3(판정 독립성) · D4(조각 배선) · D6(중복 검사 면적)의 **재발**이다.
네 관문 전부 초록이다 — `lint` 30·실패 0·고장 0·대상 0건 0 · `lint.test` 30 · 훅 371 · 생성물 4곳.

## 검사는 셋이 아니라 넷이 됐다

지시는 검사 3종이었는데 **넷으로 갈랐다.** `lint.test.py` 는 **검사 id 마다** 픽스처 한 쌍을 요구한다 —
규칙 셋을 한 id 에 묶으면 위반 픽스처가 그중 하나만 건드려도 통과라, **나머지 둘이 사문화돼도 테스트가 못 잡는다.**
표 렌더 검사를 넷으로 가른 것과 같은 이유다. 26 → 30.

| 검사 | 무엇을 잡나 | 근거 |
|:--|:--|:--|
| `gate-judge-independence` | `entry.content[].who` 가 판정자가 아닌 것 | D3 · 능력 2 · `01.architecture.md` 자기 검증 금지 |
| `fragment-load-wired` | **조건부로** 실은 스킬이 그 표의 `반드시 읽는다` 조각을 빠뜨린 것 | D4 (`build` ↔ `service-boundary`) |
| `skill-loaded-body-only` | 스킬을 싣고 **조각을 하나도** 안 실어 라우터만 실리는 것 | W2 `배선이 끊긴 자리` |
| `read-order-wired` | 커맨드·절차가 **읽으라 지시한** 조각이 `loads` 에 없는 것 | D4 (`design` ↔ `service-boundary`) |
| `skill-duplication`(확대) | 조각 35개·커맨드·절차까지 대조 | D6 |

### 어느 `who` 를 허용으로 정했나 — 그 근거

**정본은 `flow.topology.json` 의 `grades.content.judges` 이고 지금 `gatekeeper` 하나다.** 목록을 스크립트에
열거하지 않았다 — v1 의 화이트리스트 22개가 그렇게 사문화됐다. 현 5건 중 4건이 이미 `gatekeeper` 였다.

**선언만으로는 늘릴 수 없게 했다.** `machine` 이 `enforcedBy` 로 배선을 증명하듯, 판정자는 **도구 권한으로
증명한다** — `judges` 에 적힌 에이전트의 `tools` 에 `Write`·`Edit`·`Bash` 가 있으면 실패다.
근거는 `agents/gatekeeper.md` 가 스스로 적은 경계다: *"`Bash` 가 없는 것은 의도다. 도구를 돌리는
쪽(`verifier`·`reviewer`)과 그 결과를 의심하는 쪽을 가른다."* 실측 — `gatekeeper` 에 `Bash` 를 주면 실패한다.

### 왜 `반드시 읽는다` 표 전체를 요구하지 않았나

**요구해 봤다. 88건이 걸린다**(측정). `traceability` 한 스킬이 조각 일곱인데 싣는 커맨드마다 전부 요구하면
컨텍스트 예산(능력 6)이 무너진다 — 조각 고르기는 커맨드의 권한이다. 그래서 **고르기라는 변명이 성립하지
않는 자리만** 본다: ① 조건부 적재(그 상황일 때만 실리니 예산 논거가 없다) ② 조각을 하나도 안 싣는 적재
③ 본문·절차의 **읽기 지시**. 88 → 6건으로 줄고, 남은 6건은 전부 실제 구멍이었다.

`③` 은 같은 줄에 `읽는다`·`읽어라`·`읽고` 가 있어야 지시로 본다. **인용은 일부러 넘긴다** —
*"그 사실은 `drift-check/rule` 에도 적혀 있다"* 같은 줄까지 배선을 요구하면 커맨드가 남의 조각을 다 싣게 된다.
놓치는 쪽으로 틀린다(넘긴 인용 3건을 확인했다).

## 고친 것

| # | 무엇 | 근거 |
|:--|:--|:--|
| 1 | `review.entry.content.finding-severity` 의 `who` 를 `reviewer` → `gatekeeper` (`wasWho`·`$why` 남김) | D3. 발견을 만든 쪽이 자기 발견 등급을 확정하면 게이트가 없다 |
| 2 | `review.md` 게이트 절 — *등급 초안은 `reviewer`, **판정은 `gatekeeper`*** 로 갈라 적음 | 위와 짝. 본문이 데이터와 어긋나면 사용자는 본문을 읽는다 |
| 3 | `build` 에 `code-graph/service-boundary` 조건부 배선(topology + `## 연결`) | D4. MSA 레거시 "영향 없음" 오보 경로 |
| 4 | `design`(기능)에 `code-graph/service-boundary` 조건부 + `default-reference/delegation` | `procedures/design/feature.md:82` 가 읽으라 지시하는데 배선이 없었다 |
| 5 | `sync` 에 `drift-check/rule` · `prd` 에 `default-reference/delegation` | 스킬만 싣고 조각이 없어 라우터만 실렸다 |
| 6 | `prd` 에 `traceability/coverage` 배선 + 사본 삭제 | **배선이 사본을 만든 자리다**(W2). 정본을 안 실어서 커맨드가 옮겨 적었다 |
| 7 | `theme-apply` 에 `bodyOnly` + `$bodyOnly-why` | 설계 국면은 본체 한 줄만 읽는 것이 **의도**다(SKILL.md 가 그렇게 적는다). 면제를 데이터로 적고 이유를 요구한다 |
| 8 | `code-graph` description 에 `/flow:design` 추가 | 배선이 늘면 `skill-description-users` 가 양방향으로 잡는다 |
| 9 | 규약 사본 9건 — 정본 하나를 두고 다른 쪽은 이름으로 가리키게 | 아래 표 |

### 중복 9건 — 어디서 어디로

| 사본이 있던 곳 | 정본 | 처리 |
|:--|:--|:--|
| `build.md:64` · `next.md:61` | `traceability/unit-state` | 문장을 지우고 조각을 가리킴 |
| `prd.md:105` | `traceability/coverage` | **배선을 먼저 고치고** 사본 삭제 |
| `prd.md:72`·`:84` | `usecase/granularity` | 표 칸의 세부·중복 불릿을 정본에 남김 |
| `verify.md:83` | `testing` 경계 | 가리키게 바꿈 |
| `procedures/build/unit-verify.md:35` | `testing` 경계 | 같음 |
| `procedures/review/doc.md:12` | `doc-verify/scoring` | 같음 |
| `setup.md:131` ↔ `drift-check/rule.md:44` | — | **`setup.md` 는 남의 파일이라 반대쪽을 고쳤다.** `옵트인` 뒤의 뜻풀이(`켜는 것은 프로젝트의 선택이다`)를 조각에서 뺐다 — 낱말이 곧 뜻이라 정보 손실이 없고, 사용자가 그 뜻을 읽는 자리는 `setup` 이다 |

**지시 층끼리는 대조하지 않는다.** 커맨드·절차는 커맨드마다 자기 게이트·경계를 선언해야 해서 같은 문장이
겹치는 것이 정상이고(`내용 — 없다…` 가 네 커맨드에), 둘 다 정본을 **이름으로 가리키는 정상 인용**까지
사본으로 잡힌다(`publish` ↔ `verify` 의 위임 인용이 실측 예다). 잡는 것은 **규약이 두 곳에 사는 것**과
**지시 층이 규약을 베낀 것**이다.

## 되돌림 확인 — 전부 실패로 떨어졌고 원복했다

| 되돌린 것 | 결과 |
|:--|:--|
| `review` 의 `who` 를 `reviewer` 로 | `gate-judge-independence` 실패 1 |
| `judges` 선언을 비움 | 실패 5 (내용 조건 전부) |
| `gatekeeper` 에 `Bash` 부여 | 실패 1 — **선언만으로 판정자를 늘리는 길이 막힌다** |
| `build` 의 `service-boundary` 제거 | `fragment-load-wired` 실패 1 |
| `design` 의 `service-boundary` 제거 | `read-order-wired` 실패 1 |
| `sync` 의 `drift-check/rule` 제거 | `skill-loaded-body-only` 실패 1 |
| `theme-apply` 의 `$bodyOnly-why` 제거 | 실패 1 — 이유 없는 면제가 안 통한다 |
| `verify.md` 사본 복원 | `skill-duplication` 실패 1 |
| **중복 대상을 `SKILL.md` 로 축소** | `lint` 는 **통과한다**(대상 14) — `lint.test.py` 가 `대상 0건`·`위반 픽스처 통과` 로 잡았다 |

마지막 줄이 이 확대의 핵심이다. 대상을 좁히면 repo lint 는 조용히 초록이 되고 **자기 테스트만 그것을 부른다.**

## 내 판단으로 남긴 것

- **`entry.content` 를 퇴장 조건으로 재획정하지 않았다** — T4 의 일이다. `who` 축만 건드렸다.
- **`fragment-load-wired` 의 대상은 2건뿐이다**(조건부로 스킬을 싣는 커맨드가 `build` 하나라서).
  지키는 면적이 작다는 것을 숫자로 남긴다 — 대상 0건이 아니므로 사문화는 아니다.
- **`explorer` 는 도구 축으로 판정자와 구별되지 않는다**(쓰기·실행 도구가 없다). `judges` 에 적히지
  않는 것으로만 막힌다. 두 축 중 하나는 여전히 선언이다 — 주석에 적었다.
- 인용/지시 구분은 **낱말 휴리스틱**이다. 다르게 쓴 지시는 못 잡는다.

## 넘기는 것 — 내가 고치지 않았다

1. **`plugins/flow/procedures/build/` 가 git 에 없다.** 사용자 전역 `~/.gitignore_global` 의 `build/` 규칙이
   `unit-verify.md`·`schema-change.md` 를 통째로 무시한다(`git check-ignore` 로 확인). **커밋도 배포도 안 된다** —
   내가 거기 고친 한 줄도 워킹트리에만 있다. 리포 `.gitignore` 에 `!plugins/flow/procedures/build/` 가 필요하다.
2. **소유 밖 파일을 고쳤다** — `prd.md`(4곳) · `next.md` · `verify.md` · `sync.md` ·
   `procedures/review/doc.md` · `procedures/build/unit-verify.md` · `skills/drift-check/references/rule.md` ·
   `skills/code-graph/SKILL.md`. 전부 중복·배선 때문이고 한두 줄씩이다. **T6(`prd` 역추출)·T7(`next` 라우팅)과
   같은 파일이라 충돌할 수 있다.** `setup.md`·`project-template/**` 는 손대지 않았다.
3. `prd.md:98-102` 의 역추출 면제 **표**는 `coverage.md`·`scoring.md` 와 3중 사본인데(W2) 행 단위 유사도가
   문턱 아래라 검사가 안 잡는다. 역추출 정본은 T6 의 일이라 표는 그대로 뒀다.
4. `02.skills-map.md` 의 `어느 조각을 읽나` 중복(T8)은 손대지 않았다 — 이 검사들은 그 표가 접힌 뒤에도
   같은 것을 본다(표가 없어지면 `must` 가 비고 대상 0건으로 드러난다).
