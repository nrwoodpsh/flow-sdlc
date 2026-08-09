# 재설계 인벤토리 W3 — 레거시 변형 경로 실사

레거시 프로젝트(코드 많음·문서 없음·테스트 빈약)에 v2 를 첫날 깔아 변형까지 걸어간 기록.
실측 = 실제로 돌려 확인. 판독 = 파일을 읽어 확인. 추측은 명시.

## 1. 경로 표

| # | 단계 | 판정 | 근거 |
|:--|:--|:--|:--|
| 1 | `/flow:setup` 기존 코드 위 | **조건부** | 기존 코드 비수정·husky 공존·훅 설치 확인은 있다(`commands/setup.md:117-127`, 122-124 가 hooksPath 공존). **단 `drift.sourceGlobs`·`gate.legacyExempt` 를 채우는 절차가 없다** — 실행 키 표(setup.md:89-98)는 contract·build·test 5키뿐 |
| 2 | 요구 역추출 | **된다** | `prd {레벨} legacy` 가 v2 에 있다(`commands/prd.md:43·87-107`). 신규용 게이트 면제(96)·`확인 필요` 전수 표기(93)·`func legacy` 유닛 발명 거부(106)·explorer 위임 필수(20) 전부 유지 |
| 3 | 변형 설계 | **된다** | `[Mod]` 면 `impact-analysis/regression-surface` 발동(`procedures/design/feature.md:31`), build 도 같은 조건부 로드(`flow.topology.json:444-454`). `code-graph` 는 도구 없으면 축소 모드로 계속(`skills/code-graph/SKILL.md:38`) |
| 4 | 구현·검증 (테스트 빈약) | **조건부** | 기대값 출처는 요구·계약 넷뿐, 없으면 정지(`skills/testing/references/case-source.md:16-26`). 레거시는 역추출 요구(`확인 필요`)가 출처가 되고 커버리지는 `현행(미검증)` 으로 분리 계산(`traceability/references/coverage.md:20`, `procedures/verify/run.md:40`) — 사슬은 닫힌다. 단 `build.command`·`test.command` 가 없거나 틀리면 검증이 조용히 빠진다(setup 이 Exit 0 확인을 하지만 못 돌리면 "적는다"뿐, setup.md:100) |
| 5 | 드리프트 도입 첫날 | **된다 — 실측** | 유닛 0 이면 pre-commit 통과·쓰기 게이트 allow(no-units) 를 스크래치 repo 에서 직접 확인. 근거 코드 `git-hooks/drift-hook.sh:29-31`, `hooks/scripts/gate-source-write.sh:248-250`. `hooks.test.sh` 371 통과 0 실패 재확인(케이스 463·633-637) |
| 6 | `sync`·`commit` 문서 없는 프로젝트 | **된다** | sync 는 "설계 문서가 아예 없으면 경고하고 요약본만"(`commands/sync.md:83`), commit 은 유닛 0 면제로 통과 + 첫 커밋 때 규약을 물어 CLAUDE.md 에 적는다(`commands/commit.md:52-54`) |

## 2. 끊기는 자리 (심각한 것부터)

**(a) setup 이 레거시 배치에 맞는 소스 판정을 안 채운다 — 조용한 무보호.**
템플릿 기본 `drift.sourceGlobs` 는 `["src/**","app/**"]`(`project-template/workflow.config.json:22-25`).
레거시 코드가 `lib/`·`server/`·`packages/*` 에 있으면 전부 "소스 아님" — 드리프트 훅은 영원히 안 막고
쓰기 게이트도 전부 allow(not-source) 다(`drift-hook.sh:84-88`, `gate-source-write.sh:219-220` — 실측 아님, 코드 판독).
게이트가 있다는 착각만 남는 fail-open — v1 이 낡던 바로 그 형태다. **잇는 것**: setup 실행 키 표에
`drift.sourceGlobs` 를 넣고, 스택 스캔이 감지한 소스 루트로 채운 뒤 `--why` 로 1회 실측 확인.

**(b) `gate.legacyExempt` 를 채우는 커맨드가 없다 — 둘째 날 절벽.**
첫 유닛이 생기는 순간 File Map 에 없는 레거시 파일 쓰기는 전부 deny(exit 2, 실측 — not-declared,
`gate-source-write.sh:325-329`). 탈출구인 `gate.legacyExempt` 는 기계로는 완동(실측 — allow legacy-exempt)하지만,
그 키를 언제 누가 채우나를 말하는 곳이 topology 주석과 템플릿 빈 배열뿐이다(`flow.topology.json:139-144`,
`workflow.config.json:32-35`). setup·prd·design 어느 본문에도 없다. 변형 중 이웃 파일로 번지는 수정은
File Map 갱신 또는 훅 끄기 중 하나로 몰린다 — 설계가 스스로 적은 실패 경로(과차단→사람이 훅 끔)다.
**잇는 것**: setup(기존 코드 모드)과 design/feature 의 `[Mod]` 절차에 legacyExempt 기입 지점 한 줄.

**(c) `next` 가 레거시 사용자를 역추출로 못 보낸다.**
v1 `ask` 에는 명시 라우팅 행이 있었다 — "남의 코드를 파악해야 한다 | 레거시 | `/flow:prd sys legacy`"
(v1 `commands/ask.md:43`). v2 `next` 는 유형 표시(`commands/next.md:76`)에 `레거시` 가 남았지만, next 가 싣는
조각(traceability/level·unit-state·revert-scope·ops-doc/safety·code-review/severity — topology `commands.next.loads`)
어디에도 legacy 라우팅이 없고 `traceability/level.md`·SKILL.md 에도 없다(grep 실측). 위상 정본에도 legacy 는
개념이 없다. 역추출 경로는 prd.md 를 이미 연 사람만 안다. **잇는 것**: `traceability/level` 에
"기획서 없음·코드가 진실 → `prd {레벨} legacy`" 한 행.

**(d) 역추출 면제 규약이 gatekeeper 위임 지시에 실리는지가 약속뿐.**
prd 본문은 면제를 안다(`prd.md:96-105`). 그런데 gatekeeper 는 "기준을 발명하지 않는다 — 위임 지시가 준다"
(`agents/gatekeeper.md:29`)이고 "애매하면 차단한다"(31)다. prd 의 위임 문구(prd.md:32-33)는 레벨·쿼터만 넘기라
하고 면제 표는 안 넘긴다. design 의 `requirement-covered` 판정에서 `확인 필요` 요구를 어떻게 다루나도 위임
지시 몫이다. 안 실리면 기본 태도가 차단이라 레거시가 게이트에서 막힌다. — **추측**: 실제 차단 빈도는 돌려봐야
안다. v1 은 이 규약을 gatekeeper 본문에 박아 뒀다(v1 `agents/gatekeeper.md:56`).

**(e) 테스트 빈약 + 검증 명령 부재의 바닥이 무르다.** verify 의 `run-not-infer` 는 약속 등급이고
(topology `commands.verify.entry.promise`), `test.command` 가 없으면 setup 은 "그 사실을 요약에 적는다"까지다
(setup.md:100). 레거시에서 흔한 상태(테스트 러너 자체가 없음)에서 build 루프의 Exit code 판정이 성립하지
않는데, 그때 무엇으로 내려가나(수동 확인? 스모크만?)를 말하는 조각이 없다. — 판독. **잇는 것**: `testing/run` 에
"러너 부재 시" 한 절.

## 3. v1 에 있었는데 v2 에서 사라진 것

| 무엇 | v1 근거 | v2 상태 | 판단 |
|:--|:--|:--|:--|
| **규모 게이트** — `legacy` 전체 읽기 전 모델·비용 확인 | v1 `prd.md:53` (run:102·verify:58 도) | 어디에도 없다(grep 실측). explorer 위임 필수가 부분 대체 | 01.architecture.md:312 는 "정본 하나로, 낡는 값은 뺀다"였지 삭제가 아니다 — **누락으로 보인다. 확신은 못 한다** |
| 역추출 보조 도구 지시 — GitHub·DB MCP("왜"의 근거)·ponytail(과설계 지도) | v1 `prd.md:18·93-94` | v2 prd 에 없다 | 하드코딩 제거 방침과 결이 같아 **의도로 추정 — 모른다.** 다만 "코드만 보면 왜를 모른다"는 실전 규칙 자체가 함께 사라졌다 |
| gatekeeper 본문의 레거시 면제 규약 | v1 `gatekeeper.md:56` | 커맨드(prd)로 이동 | **의도** — 복제 정본 제거(v2 `gatekeeper.md:41-42`). 대가가 2-(d) |
| `ask` 의 레거시 라우팅 행 | v1 `ask.md:43·147` | next 에 미승계 | **누락으로 판단** — 147(유닛 존재 질문)은 prd 가 흡수했으나 43(진입 라우팅)은 갈 곳이 없다 |

사라지지 않고 강화된 것도 적는다: 역추출 절차 본문(prd 2')·`확인 필요`≠gap 분리 계산·no-units 면제·
`func legacy` 거부는 전부 이식됐고, 레거시 유닛 계획(`procedures/design/system.md:72` — 손댈 범위만 유닛으로)은
v2 에서 새로 명문화됐다.

## 4. 한 줄 결론

첫날 깔고 커밋하고(실측) 역추출→설계→변형→sync 까지 사슬은 이어지지만, **setup 이 소스 판정과 레거시 면제를
안 채워 주는 탓에** 표준 배치(src/) 밖 레거시에서는 보호가 조용히 꺼지거나(2-a) 둘째 날부터 과차단(2-b)으로
몰린다 — 기계는 다 있고, 그 기계에 레거시의 지형을 알려주는 자리가 빠졌다.
