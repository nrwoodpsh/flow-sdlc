# 실측 커버리지와 결함 목록

**원칙은 전 기능 실측이다.** 여기 적힌 것은 전부 **실행 결과**이고, 근거는 회차 로그와
세션 트랜스크립트(`~/.claude/projects/*/*.jsonl`)의 `tool_use` 레코드다.

> **측정 방법을 한 번 틀렸다.** `claude -p` 출력에는 **도구 호출 흔적이 없다** — 최종 답변 텍스트만 나온다.
> 그것만 보고 *"에이전트가 안 불렸다"* 고 판단할 뻔했다. 실제 근거는 트랜스크립트다.
> 아래 에이전트·조각 수치는 전부 트랜스크립트에서 세었다.

## 어떻게 돌렸나

설치하지 않고 `claude --plugin-dir <v2>/plugins/flow -p "/flow:…"` 로 돌렸다.
`flow@setting-ai`(사용 중)와 `flow@inline` 이 공존하는 것을 `claude plugin list` 로 확인했다.
대상은 유튜브 채널 요약 시스템을 레거시 형태로 만든 것(`/tmp/yt-digest` → 사본 `trial-a/b/c`).

## 커맨드 — 11개 중 10개 실행

| 커맨드 | 실측 | 결과 |
|:--|:--|:--|
| `next` | ✅ ×2 | 파일에서 상태 계산 · 레거시 라우팅 · **F1 발견** |
| `setup` | ✅ | 골격·템플릿 16종·훅 설치 · **`lib/` 를 찾아 `sourceGlobs` 에 채움** |
| `prd sys legacy` | ✅ | 역추출 3층 · **근거 없는 요구를 스스로 내림** |
| `prd domain` | ⚠️ | 레벨·대상 선언까지 확인. **산출 파일(`01.domain/01.collect.md`)이 안 생겼다 → F6** |
| `design` (기능) | ✅ | 유닛 사슬 전체 · File Map 2개 · 코드 미변경 |
| `design sys` | ❌ | 워커가 죽어 로그 0바이트. **미실측** |
| `build` | ✅ | 구현 4파일 · `4.build`·`5.verify` · **F2 발견** |
| `verify unit` | ✅ | **PASS · Exit 0 · 19 tests** |
| `verify` (브랜치) | ✅ | PASS(조건부) 통과 5 / 실패 0 / **못 돌림 1** |
| `review` | ❌ | 워커가 죽어 미실행 |
| `sync` | ✅ | diff 분류·수렴. 작업 트리가 비어 diff 범위를 스스로 판단해 진행 |
| `commit` | ✅ | **드리프트에서 막혔다** (아래) |
| `spike` | ✅ | `spike/00.transcript-truncation/` + **ADR 승격** |
| `publish` | ✅ | **발행처 없음을 알리고 실행 전 정지** |

## 훅 — 런타임 발화가 확정됐다

정적 검사가 못 보던 자리다. **셋 중 둘이 실제 차단을 실증했다.**

| 훅 | 실측 |
|:--|:--|
| `gate-source-write.sh` | ✅ **런타임 34회 발화**(트랜스크립트) · 셸 직접 8케이스 — File Map 안은 통과, **밖은 전부 차단** |
| `guard-danger.sh` | ✅ **5건 차단 실증** — 아래 표 |
| `drift-hook.sh` | ✅ **`/flow:commit` 이 드리프트에서 막혔다.** `core.hooksPath=.githooks` 로 걸린 상태 |
| `check-drift-hook.sh` | ❌ **미실측**(SessionStart 경고) |

```
git commit --no-verify           ⛔ 차단   ← v1 이 스스로 붙이던 그 플래그다
git -c core.hooksPath= commit    ⛔ 차단
git checkout -- <경로>            ⛔ 차단
gh pr create                     ⛔ 차단
git push --dry-run               통과(정상) — git 자신의 "No configured push destination"
git status --short               통과·정상 실행
```

**v1 결함이 실제로 닫혔다.** v1 은 `/flow:commit` 이 `--no-verify` 를 붙여 드리프트 훅을 껐다.
v2 는 **가드가 그 플래그를 막아** 커맨드가 쓰려 해도 못 쓴다. 그래서 `commit` 이 우회하지 않고 멈췄다.

## 에이전트 — 5개 중 3개 (트랜스크립트 실측)

| 에이전트 | 호출 | |
|:--|--:|:--|
| `verifier` | 3 | ✅ 실제 호출 |
| `gatekeeper` | 3 | ✅ |
| `builder` | 2 | ✅ 코드 쓰기가 여기로 갔다 |
| `explorer` | **0** | ❌ **F3** — `prd.md` 는 레거시에서 위임이 필수라 적는다 |
| `reviewer` | **0** | ❌ `review` 회차가 없었다 |

## 조각 적재 — 선언 ↔ 실제

`build` 회차에서 **선언 7개 중 실제로 읽은 것은 1개**다.

| | |
|:--|:--|
| 읽었다 | `default-reference/delegation` |
| **선언했는데 안 읽었다** | `testing/run` · `testing/case-source` · `contract-gate/failure` · `code-review/checklist` · `traceability/unit-state` · 절차 `build/unit-verify`·`build/schema-change` |

**`testing/run` 을 안 읽고 `5.verify` 문서를 썼다.** 그 조각이 *"추론은 검증이 아니다 — Exit code 로 판정한다"* 를 담은 자리다.

반대로 **조건부 배선은 정확히 작동했다** — `traceability/reverse-extract`·`reverse-check` 가 `legacy` 일 때만,
`impact-analysis/regression-surface` 가 *기존 코드를 고칠 때만* 조건대로 실렸다.

전체로는 조각 35개 중 **11개** 적재 확인, 절차 13개 중 **1개**(`design/feature`).

## 결함 목록 — 수정 대기

| ID | 결함 | 심각도 | 근거 · 재현 |
|:--|:--|:--|:--|
| **F1** | **`${CLAUDE_PLUGIN_ROOT}` 읽기가 권한에 매달린다** — 헤드리스에서 위상 정본 없이 판정한다 | **높음** | 01회차에서 커맨드가 *"권한이 없어 거절됐다"* 고 보고. `--allowedTools Read` 를 열면 읽힌다 → 경로 문제 아님 |
| **F2** | **선언한 조각을 안 읽는다** | **높음** | `build` 선언 7 → 적재 1. 설계가 *위험 칸*에 적어 둔 것이 첫 실전에서 났다 |
| **F3** | `explorer` 가 한 번도 안 불렸다 | 중간 | 트랜스크립트 0회. `prd.md` 는 레거시에서 필수라 적는다 |
| **F4** | `gatekeeper` 판정이 **수정 전 문서 기준**이고 재판정을 안 돌렸다 | 중간 | 03회차에서 **커맨드가 스스로 신고**했다 |
| **F5** | `verify` 브랜치 모드에 **못 돌린 항목 1건**이 남았다 | 낮음 | PASS(조건부) 로 나왔다. 무엇을 못 돌렸는지 확인 필요 |
| **F6** | `prd domain` 이 선언만 하고 **산출 파일을 안 만들었다** | 중간 | `01.domain/01.collect.md` 부재. **다만 워커가 죽어 중간에 잘렸을 수 있다 — 재실행으로 가려야 한다** |

## 방법론 결함 — 다음에 되풀이하지 않을 것

**서브에이전트에게 중첩 `claude -p` 를 기다리게 하면 안 된다.** 회차당 3~15분이 걸리는데 그동안
스트리밍 진전이 없어 **워치독이 정지로 판정해 죽인다**(A·C 가 그렇게 죽었다).
회차 실행은 코디네이터가 백그라운드로 돌리고, 서브에이전트는 **분석·집계처럼 짧은 일**만 맡는다.
다만 **회차 로그는 살아남았다** — 파일에 쓰게 했기 때문이다.

## 남은 실측

| 층 | 남은 것 |
|:--|:--|
| 커맨드 | `review`(코드·문서) · `design sys` · `prd func` · `verify` 프로젝트 모드 |
| 에이전트 | `explorer` · `reviewer` |
| 훅 | `check-drift-hook.sh`(SessionStart) |
| 조각 | 35개 중 24개 · 절차 13개 중 12개 미확인 |
| 스킬 | `code-graph` · `drift-check` · `ops-doc` · `usecase` · `theme-apply`(프론트 없어 N/A일 수 있다) |

## 갱신 — `review` 회차와 B 리포트 반영

**`review` 는 조각을 제대로 읽었다.** `code-review/{checklist,layers,severity}` ·
`testing/{run,case-source,integration}` **6개 적재**. `reviewer` 가 실제로 불려 Bash 로 도구를 돌렸고
(계약 tsc · 소스 tsc · `npm test` 19 passed · 셔플 전부 Exit 0), `gatekeeper` 반증으로 **2건이 기각**됐다.
`npm run build` 가 Exit 127(`tsc` 없음)인 것도 잡아 보고했다.

> **그래서 F2 는 계통 결함이 아니라 커맨드별 편차다.** `review` 6개 · `sync` 4/8 · `build` 1/7 · `commit` 0/3.
> *"조각을 못 읽는다"* 가 아니라 **어떤 커맨드는 읽고 어떤 커맨드는 안 읽는다** 가 정확한 서술이다.
> 수정도 계통 장치가 아니라 **안 읽는 커맨드의 본문**을 봐야 한다.

**에이전트는 5개 중 4개가 실측됐다** — `verifier`·`gatekeeper`·`builder`·`reviewer`.
`explorer` 만 전 회차 **0회**다(F3).

### B 회차가 더한 것 — 훅은 발화하는데 둘은 아무도 못 본다

| 훅 | 발화 | 모델·stdout 에 닿나 |
|:--|:--|:--|
| `guard-danger` | ✅ | ✅ 차단이 곧 전달 |
| `drift-hook` | ✅ | ✅ 커밋이 멈춘다 |
| `check-drift-hook` | ✅ | ❌ **stderr(`1>&2`) — 안 닿는다** |
| `check-guard-canon` | ✅ | ❌ 같음. **그 세션은 가드가 열린 줄 모르고 `--no-verify` 를 시도했다** |

가드는 훅에 입력을 직접 먹여 확정했다 — `git push`·`push origin main`·`git p"u"sh`·`merge`·
`gh pr merge`·`reset --hard` **전부 exit 2**, `checkout -b`·`commit` 통과.
`push --dry-run` 통과는 결함이 아니라 `guard-rules.json` 의 `unless: --dry-run` — **설계된 예외다.**

**`--no-verify` 경로는 트랜스크립트 5개 전체에서 없었다.** 실제 커밋은 `git commit -F -` 이고
`main` 이라 `feat/collect-quota` 를 만들어 커밋했다. **v1 결함이 닫혔다.**

## 결함 목록 — 갱신

| ID | 결함 | 심각도 |
|:--|:--|:--|
| **F1** | 플러그인 루트 읽기 차단 — 정본 없이 판정. `permissions.allow` 절대경로·`--setting-sources` **둘 다 실패**(문법 미확인) | **높음** |
| **B1** | **SessionStart 경고가 stderr 라 아무도 못 본다.** `check-guard-canon` 은 가드 fail-open 을 알리려는 훅인데 그 알림이 안 닿는다 | **높음** |
| **F2** | 조각 적재가 커맨드마다 다르다 — `build` 1/7 · `commit` 0/3 · `sync` 4/8 · `review` 6 | **높음** |
| B3 | `commit` 이 브랜치를 만들면 `sync` 가 쓴 색인이 즉시 낡는다 | 중간 |
| F3 | `explorer` 전 회차 0회 | 중간 |
| F4 | `gatekeeper` 재판정 누락(커맨드가 자진 신고) | 중간 |
| B4 | `sync` 가 약속 게이트와 다른 diff 범위를 스스로 넓혔다(근거는 밝힘) | 낮음 |
| B5 | 조각 경로를 `references/` 없이 먼저 찾아 한 번 실패 | 낮음 |
| F5 | `verify` 브랜치 못 돌린 1건 | 낮음 |
| F6 | `prd domain` 산출 부재 — 워커 절단 가능. **재실행으로 가려야 한다** | 중간 |

**F1 과 B1 은 같은 뿌리다** — 플러그인이 모델에게 닿지 못한다. 하나는 정본을, 하나는 경고를.
