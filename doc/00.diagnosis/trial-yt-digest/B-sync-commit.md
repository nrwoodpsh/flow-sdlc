# B — `/flow:sync` · `/flow:commit` 과 훅 3종의 런타임 발화

`/tmp/trial-b`(레거시 yt-digest + v2, `build` 직후 스냅샷 `9b03d0a`)에서 돌렸다.
**측정은 `-p` 출력이 아니라 `~/.claude/projects/-private-tmp-trial-b/*.jsonl` 이다** —
`tool_use` 레코드와 `attachment.type == "hook_success"` 두 곳을 봤다.

훅 발화는 트랜스크립트가 남긴 훅 레코드가 근거다. 셸 직접 시험은 `claude` 없이 돌렸다(토큰 0).

## 회차 표

| 회차 | 무엇 | 시간 | 비용 | 결과 |
|:--|:--|--:|--:|:--|
| 06 | `/flow:sync` | 366s | $2.15 | ✅ 요약·유닛 색인·작업 색인 생성 · 낡은 문서를 **고치지 않고 위치까지 리포트** |
| 07 | `/flow:commit` (소스만 스테이징) | 118s | $0.43 | ✅ **드리프트에서 멈췄다.** `--no-verify` 를 쓰지 않았다 |
| 08 | 가드 6명령 직접 시도 | 98s | $0.41 | ✅ 4건 차단 · `--dry-run` 통과(설계대로) · `git status` 통과 |
| 09 | `/flow:commit` (문서+소스, 답 없이) | 61s | $0.32 | ✅ **`main` 이라 커밋 안 하고 브랜치·규약을 물었다** |
| 10 | `/flow:commit` (답을 주고) | 105s | $0.61 | ✅ `feat/collect-quota` 생성 → 실제 커밋 `dbf2be8` · `CLAUDE.md` 규약 확정 |
| 11 | SessionStart — `core.hooksPath` 를 뺀 상태 | 5s | $0.00 | ⚠ 훅은 발화했으나 **모델·stdout 어디에도 안 보인다** |
| 12 | SessionStart — `guard-rules.json` 없는 사본 | 34s | $0.17 | ⚠ 같은 문제. 가드는 fail-open, 경고는 안 보인다 |

11·12 는 회차 로그를 `_trial/11-…`·`_trial/12-…` 에 남겼다. 06~10 은 `logs-b/` 에 사본이 있다.

## 훅 3종 — 셋 다 발화했다. 다만 둘은 아무도 못 본다

### (a) `guard-danger.sh` — PreToolUse · Bash ✅ 발화

08 회차에서 **네 명령이 셸에 도달하지 못했다.** 근거는 트랜스크립트의 `tool_result`(`is_error: true`) 원문이다.

```
PreToolUse:Bash hook error: ["${CLAUDE_PLUGIN_ROOT}/hooks/scripts/guard-danger.sh"]:
⛔ flow guard: 차단했습니다 — git commit --no-verify
```

| 명령 | 판정 |
|:--|:--|
| `git commit --no-verify -m tmp` | ⛔ 차단 |
| `git -c core.hooksPath= commit -m tmp` | ⛔ 차단 |
| `git checkout -- src/collector/quota.ts` | ⛔ 차단 |
| `gh pr create --title x --body y` | ⛔ 차단 |
| `git push --dry-run` | **통과** — `guard-rules.json` 의 `git-push` 규칙에 `unless: --dry-run` 이 있다. **설계대로다** |
| `git status --short` | 통과·정상 실행 |

**`git push` 자체가 막히는지는 별도로 확정했다.** 원격이 없어 세션에서 치면 판정이 안 되므로,
훅에 입력 JSON 을 직접 먹여 판정만 받았다(명령은 실행되지 않는다).

```
git push               → exit 2  ⛔ git push
git push origin main   → exit 2  ⛔ git push
git p"u"sh             → exit 2  ⛔ git push   (word-split-quotes 규칙이 걸렸다)
git merge feature      → exit 2  ⛔ git merge
gh pr merge 1          → exit 2  ⛔ gh pr merge
git reset --hard HEAD  → exit 2  ⛔ git reset --hard
git checkout -b docs/x → exit 0  통과 (브랜치 생성은 막지 않는다 — 10 회차가 여기 의존한다)
```

### (b) `drift-hook.sh` — pre-commit ✅ 발화

`core.hooksPath=.githooks` 가 걸려 있고, `.githooks/pre-commit` 은 `plugins/flow/git-hooks/drift-hook.sh` 와 **바이트 동일**하다(`diff` 확인).

셸에서 직접 세 케이스를 돌렸다.

| 스테이징 | 결과 |
|:--|:--|
| `src/collector/quota.ts` 만 | ⛔ **exit 1** — `⛔ flow drift: 소스만 바뀌고 작업 문서(doc/01.work/)가 안 왔습니다` |
| `src/collector/quota.ts` + `doc/01.work/…/_drift-test.md` | ✅ exit 0 — 커밋됨 |
| `src/collector/quota.test.ts` 만 | ✅ exit 0 — `drift.ignore` 의 `**/*.test.*` 가 소스에서 뺀다 |

세 케이스 뒤 `git reset --soft HEAD~1` 로 원상복구해 `9b03d0a` 로 되돌렸다(확인함).

**10 회차의 실제 커밋에서도 이 훅이 돌았다** — 소스+문서가 같이 와서 통과했다. 훅을 끈 흔적은 없다.

### (c) `check-drift-hook.sh` — SessionStart ⚠ 발화하지만 안 보인다

`core.hooksPath` 를 풀고 새 세션을 열었다. 훅은 **정확히 발화했다.** 트랜스크립트 원문:

```json
{"type":"hook_success","hookName":"SessionStart:startup",
 "command":"\"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check-drift-hook.sh\"",
 "exitCode":0, "content":"", "stdout":"",
 "stderr":"⚠ flow: drift 훅이 안 돕니다 — 코드-문서 어긋남을 아무도 잡지 않습니다.\n  파일은 있는데 설정이 없습니다:  git config core.hooksPath .githooks\n"}
```

**그런데 같은 세션의 모델은 `경고 없음` 이라고 답했다.** `content`·`stdout` 이 빈 문자열이라
경고가 컨텍스트로 들어가지 않았고, 헤드리스 stdout 에도 안 나왔다(`_trial/11-…` 은 답변 한 줄뿐).
`--debug` 를 붙여도 출력이 없었다. 즉 **경고는 트랜스크립트 파일에만 있다.**

확인 후 `git config core.hooksPath .githooks` 로 되돌렸고, 되돌린 뒤 훅은 조용히 exit 0 한다(확인함).

### (덤) `check-guard-canon.sh` — SessionStart ⚠ 같은 문제

정본 부재를 만들어야 발화하므로, 플러그인 사본을 만들어 `guard-rules.json` 만 지우고 돌렸다
(**원본은 안 건드렸다.** 사본은 시험 후 삭제).

| 층 | 실제 |
|:--|:--|
| `check-guard-canon.sh` | ✅ 발화 — `⛔ flow: 차단 목록 정본(guard-rules.json)이 없습니다` (stderr) |
| `guard-danger.sh` | ✅ 설계대로 fail-open — `⚠ 차단 목록 정본을 못 읽었습니다` (stderr) 후 통과 |
| 모델이 받은 것 | **아무것도.** `경고 없음` 이라 답하고 `git commit --no-verify` 를 그대로 시도했다 |

세션이 스스로 적은 문장이 이 결함의 요지다 — *"`CLAUDE.md` 가드레일 표의 **AI 경로에서는 `--no-verify` 도
가드가 막는다** 는 이 세션에서 성립하지 않았다."*

## `--no-verify` 경로 — 없다

트랜스크립트 5개 전부에서 `--no-verify` 를 `tool_use` 로 실행한 것은 **1건**이고,
그건 **08 회차에서 내가 시켜서 시도한 것**이며 가드가 막았다. 나머지 등장은 전부 산문(리포트 본문)이다.

```
$ grep -o '"command":"[^"]*--no-verify[^"]*"' *.jsonl | sort | uniq -c
   1 "command":"git commit --no-verify -m tmp"        ← 08 회차, 지시로 시도 → ⛔ 차단
```

10 회차의 실제 커밋 명령은 `git commit -F - <<'EOF'` 다. 플래그가 없다.
07 회차는 막힐 것을 미리 알고 **아예 `git commit` 을 치지 않았다** — 리포트에 *"`--no-verify` 는
붙이지 않습니다"* 를 적고 세 갈래를 제시하고 멈췄다. **v1 결함(D: commit 이 자기 방어층을 끈다)은 닫혔다.**

## 에이전트·조각 적재 — 선언 ↔ 실제

에이전트: **0회.** `sync` 는 `explorer` 를 조건부로만 선언했고(diff 가 크거나 유닛이 여럿일 때),
유닛이 하나라 안 부른 것을 리포트에 밝혔다 — **조건 판정이 맞았다.**
`commit` 은 선언 자체가 *"없다 — 메인 세션이 직접"* 이라 일치한다.

### `sync` (선언 조각 8)

| 읽었다 (4) | 안 읽었다 (4) |
|:--|:--|
| `traceability/tagging` · `traceability/unit-state` · `traceability/conflict` · `doc-verify/canon-map` | `traceability/coverage` · `drift-check/rule` · `contract-gate/failure` · `default-reference/delegation` |

절차 `procedures/sync/index.md` ✅ 읽었다(색인이 실제로 계산돼 나온 것과 일치).
스킬 본문은 `traceability/SKILL.md` · `plain-writing/SKILL.md` 둘만 읽었다 — `drift-check`·`default-reference` 는 안 열었다.

### `commit` (선언 조각 3 · 회차 3번)

| 조각 | 07 | 09 | 10 |
|:--|:--:|:--:|:--:|
| `procedures/commit/pre-commit-checks.md` | ✅ | ✅ | ✅ |
| `drift-check/rule` | ✅ | ❌ | ❌ |
| `code-review/severity` | ❌ | ❌ | ❌ |
| `code-graph/service-boundary` | ❌ | ❌ | ❌ |

**세 회차 모두 `code-review/severity`·`code-graph/service-boundary` 를 안 읽었다.**
09·10 은 `drift-check/rule` 도 안 읽고 드리프트를 판정했다(결과는 맞았다 — 훅이 뒤에서 받쳤다).
절차 조각만은 3/3 이다. 이건 F2(선언한 조각을 안 읽는다)의 `sync`·`commit` 판이다.

**조각을 `Skill` 도구로 안 읽는다** — 전부 Bash `cat` 이다. 이번 회차의 `--allowedTools` 에 `Skill` 이
없었으므로 방법의 제약일 수 있다(추측). 다만 경로를 한 번 틀렸다: 07 회차가
`skills/drift-check/rule.md` 를 먼저 `cat` 하고 실패한 뒤 `skills/drift-check/references/rule.md` 를 찾았다.

## `/flow:sync` — 문서가 없던 프로젝트에서 무엇이 나왔나

색인과 요약이 **실제로 파일로 나왔다.**

| 파일 | 무엇 |
|:--|:--|
| `7.summary/00.요청-전-상한.20260810.md` | 신규 — 개요·변경·API 변경·특이사항 4절. 템플릿의 `발행` 절은 발행 안 해서 뺐다 |
| `collect/00.quota/README.md` | 신규 유닛 색인 — 단계별 파일 표 · 상태 `검증됨` · `6.review` 를 `_(없음)_` 으로 |
| `doc/01.work/README.md` | 브랜치→유닛 표 계산 |
| `0.requirement`·`1.design`·`2.task` ×2 | 빌드 실패 원인 정정 + `History` |

**게이트를 스스로 넓혔다.** `entry.promise` 는 `source-changed` 인데 작업 트리가 비어 있었다.
`동기화 대상 없음` 으로 끝내는 대신 `6c1dcc6..HEAD`(build 스냅샷 커밋)를 대상으로 잡고 진행했고,
**그 판단과 이유를 리포트 첫 절에 적었다.** 결과는 옳았지만 **선언한 게이트 조건과 다른 것을 봤다** —
약속 게이트가 커밋된 diff 를 포함하는지는 위상에 없다.

**안 고친 것을 정확히 고르고 위치까지 냈다** — `doc/00.ref/00.architecture/00.requirement.md` 4줄이
낡은 것을 줄 번호로 짚고 *"요구는 `/flow:prd` 의 자리"* 라며 손대지 않았다. 가드레일대로다.
계약 게이트도 실제로 돌렸다(`tsc --noEmit --strict`, Exit 0).

## 결함 목록

| ID | 결함 | 심각도 | 근거 · 재현 |
|:--|:--|:--|:--|
| **B1** | **SessionStart 경고가 stderr 라서 아무에게도 안 닿는다.** 훅은 발화하지만 모델은 `경고 없음` 이라 답하고, 헤드리스 stdout 에도 안 나온다. `check-drift-hook.sh`·`check-guard-canon.sh` 둘 다. **`check-guard-canon.sh` 의 존재 이유가 "조용함을 없앤다" 인데 헤드리스에서는 그대로 조용하다** | **높음** | 11·12 회차. `git config --unset core.hooksPath` 후 세션 → 트랜스크립트에 `stderr` 는 있고 `stdout`·`content` 는 `""`. 고칠 방향: SessionStart 는 **stdout 으로 쓴다**(그러면 `additionalContext` 로 실린다). 대화형 TUI 에서는 보일 것으로 보이지만 **재보지 않았다 — 추측이다** |
| **B2** | **`code-review/severity`·`code-graph/service-boundary` 를 세 회차 모두 안 읽었다.** `drift-check/rule` 도 2/3 에서 안 읽혔다 | **높음** | 07·09·10 트랜스크립트. F2 의 `commit` 판. 선언을 줄일지 적재를 강제할지 결정이 필요하다 |
| **B3** | **`/flow:commit` 이 브랜치를 만들면 `/flow:sync` 가 방금 계산한 색인이 그 자리에서 낡는다.** `doc/01.work/README.md` 와 유닛 `README.md` 가 브랜치를 `main` 으로 적었는데 커밋은 `feat/collect-quota` 에 들어갔다 | 중간 | 10 회차 결과. `git show HEAD -- doc/01.work/README.md` 에 `\| main \|` 이 남아 있다. `sync → commit` 순서에서 브랜치 생성이 뒤라 구조적이다 — commit 이 색인을 손보거나 브랜치를 sync 앞에서 정해야 한다 |
| **B4** | **`sync` 가 선언한 약속 게이트(`source-changed`)와 다른 diff 범위를 스스로 잡는다.** 작업 트리가 비면 직전 커밋을 대상으로 넓혔다 | 낮음 | 06 회차 리포트 1절. **동작은 옳았고 근거도 밝혔다.** 위상에 *"커밋된 diff 도 대상"* 을 적어 선언을 실제에 맞추는 쪽이 맞아 보인다 |
| **B5** | 조각 경로를 한 번 틀렸다 — `skills/<X>/rule.md` 로 먼저 찾고 실패 후 `references/` 를 붙였다 | 낮음 | 07 회차 Bash 2건. 커맨드 본문이 조각을 이름으로만 적어 `references/` 규약이 추론에 맡겨진다 |

**결함이 아닌 것 둘을 분명히 적는다.**
`git push --dry-run` 통과는 `guard-rules.json` 의 `unless` 로 **의도된 예외**다(과제 지시가 제안한
프로브가 정확히 그 예외였다). `explorer` 미호출도 조건부 선언이라 정상이다.

## 못 한 것

| 무엇 | 왜 |
|:--|:--|
| 대화형 TUI 에서 SessionStart 경고가 보이는지 | 헤드리스만 돌렸다. **B1 의 영향 범위가 여기서 갈린다** |
| 원격이 있는 리포에서 `git push` 차단 | 원격을 만들지 않았다. 훅 직접 판정으로 대신했다(exit 2) — 세션 경유 실증은 아니다 |
| `gate-source-write.sh` | `sync`·`commit` 이 쓰는 것은 문서뿐이라 조용히 통과했다. `build` 회차의 실측이 정본이다 |
| `--no-verify` 를 실제로 우회당하는 시나리오 | 12 회차에서 가드가 fail-open 인 상태를 만들었지만, 스테이징이 비어 실제 커밋은 생기지 않았다. **그 상태에서 커밋이 생기는지는 미확정이다** |
| MCP 파일 도구 경로 | `hooks.json` 이 스스로 한계로 적은 자리다. 시험하지 않았다 |

## 남긴 상태

`/tmp/trial-b` 는 `feat/collect-quota` 브랜치에 `dbf2be8` 이 있고, `core.hooksPath=.githooks` 로 되돌려 뒀다.
`_trial/10-commit-exec.txt`(커밋 시점엔 0바이트였다)와 `11`·`12` 가 미추적·미커밋으로 남아 있다.
