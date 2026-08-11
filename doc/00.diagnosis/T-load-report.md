# T-load — v2 로드 가능성 정적 전수 검증

2026-08-09 · 설치하지 않고 파일만 보고 판정했다. 검증 도구: `claude plugin validate`(v2.1.226) ·
PyYAML 파싱 · 실제로 도는 `flow@setting-ai` 0.6.0 캐시와의 형식 대조 · 공식 문서.

## 결론 먼저

**안 뜨는 파일은 없다.** 커맨드 11 · 에이전트 5 · 스킬 14 · 두 매니페스트 · hooks.json 전부 "뜬다".
남는 불확실은 하나다 — **훅이 런타임에 실제로 발화하는지는 정적으로 증명할 수 없다.**

## 로드 규약의 근거 (기억이 아니라 확인한 것)

| 근거 | 무엇을 확인했나 |
|:--|:--|
| `code.claude.com/docs/en/plugins-reference` | 디렉터리 규약(`commands/`·`agents/`·`skills/*/SKILL.md`·`hooks/hooks.json`은 플러그인 루트, `.claude-plugin/`에는 plugin.json만) · plugin.json 은 `name`만 필수, `displayName` 유효(v2.1.143+), 미지 필드는 경고만 하고 로드됨 · 에이전트 frontmatter 허용 필드(`name`·`description`·`tools`…) · 커맨드는 파일명이 이름, `/플러그인명:커맨드`로 네임스페이스 · `${CLAUDE_PLUGIN_ROOT}` 치환 · `claude plugin validate`가 plugin.json·frontmatter·hooks.json 스키마를 검사한다고 명시 |
| `code.claude.com/docs/en/plugin-marketplaces` | marketplace.json 필수 필드(`name`·`owner`·`plugins`) · 플러그인 항목 필수(`name`·`source`) · 상대 `source`는 git/로컬 add에서 동작, URL 직접 add에서는 안 됨 · `flow-sdlc`는 예약어 아님 |
| `~/.claude/plugins/cache/setting-ai/flow/0.6.0` (실제로 도는 것) | 커맨드 frontmatter(`description`+`argument-hint`, 홑따옴표 인용) · 에이전트 `tools: Read, Grep, Glob` 쉼표 문자열 · hooks.json 의 `"\"${CLAUDE_PLUGIN_ROOT}/...\""` 패턴 · matcher 없는 SessionStart — **v2와 형식이 전부 동일하고, 이 세션에 flow:explorer·flow:verifier가 실제로 떠 있다** |
| `claude plugin validate` 실행 | `./plugins/flow` ✔ · `.`(marketplace) ✔ — 둘 다 통과, exit 0 |

## 전수 판정

### 커맨드 11 — 전부 뜬다
`build commit design next prd publish review setup spike sync verify` — 11개 전부:
frontmatter 가 PyYAML로 파싱됨 · 키는 `description`·`argument-hint` 둘뿐 · `argument-hint`는 전부
홑따옴표 문자열(YAML 리스트로 오파싱될 `[`가 인용됨을 코드로 확인) · 탭·BOM·CR 없음 ·
이름은 파일명에서 오므로 `/flow:build` 등으로 뜬다. 도는 v1 0.6.0과 형식 동일.

### 에이전트 5 — 전부 뜬다
`builder explorer gatekeeper reviewer verifier` — `name`이 파일명과 일치 · `description`은 `>-` 블록
스칼라로 파싱됨 · `tools` 쉼표 문자열은 도는 v1 에이전트와 같은 형식(그 형식이 이 세션에 실제로 로드돼 있음).

### 스킬 14 — 전부 뜬다
14개 전부 `name` == 폴더명, `[a-z0-9-]`만 · `description` 비어있지 않고 100~250자(한계 1024자 대비 여유) ·
SKILL.md 가 이름 짚는 `references/*.md` 전부 실재. 유일한 외부 참조
`drift-check → code-graph/references/service-boundary.md`도 실재(내 1차 스캔의 오탐이었다).

### 매니페스트 — 뜬다
- `plugins/flow/.claude-plugin/plugin.json`: validate ✔ · `name: flow` · `displayName` 유효 · JSON 파싱 ✔
- `.claude-plugin/marketplace.json`: validate ✔ · `name`·`version`(0.9.0)·`description`이 plugin.json과 일치 ·
  `source: ./plugins/flow` 실재 · `flow-sdlc`는 예약어 아니고 현재 등록된 마켓플레이스(`setting-ai`·`claude-plugins-official`)와도 안 겹침

### hooks.json — 뜬다 (정적 한계 하나만 남음)
- validate ✔ (문서상 validate 가 hooks.json 스키마까지 검사) · 최상위 `$note` 키도 통과
- 스크립트 4개 전부 실재 · 실행권한(rwxr-xr-x) · `bash -n` 문법 ✔
- matcher(`Bash` / `Write|Edit|MultiEdit|NotebookEdit`) · matcher 없는 SessionStart — 도는 v1과 같은 구조
- `${CLAUDE_PLUGIN_ROOT}` 참조 전수: 커맨드·스킬·hooks.json이 가리키는 **23개 경로 전부 실재**
  (procedures 13 · hooks/scripts 4 · presets 3 · git-hooks 1 · flow.topology.json · project-template/)
- `flow.topology.json` ↔ 실제 파일: commands 11·skills 14·agents 5 집합이 정확히 일치, 조각 참조 결손 0

**불확실(정직하게)**: 정적 통과 ≠ 런타임 발화. 훅이 세션에서 실제로 돌고 차단하는지는
설치(또는 `--plugin-dir` 세션 로드) 없이는 아무도 증명 못 한다. 이것이 남은 유일한 미검증 항목이다.

## 설치 예행 — 빠진 것

| 빠진 것 | 영향 |
|:--|:--|
| `LICENSE` 파일 없음 | plugin.json 이 `"license": "MIT"`를 선언하는데 파일이 없다(v1엔 있음). 로드는 막지 않음 |
| **git remote 없음** | git 소스 add 불가. 로컬 경로 add(`/plugin marketplace add {당시 작업 경로}`)나 `--plugin-dir`만 가능 |
| `.claude/` 없음 | 이미 알던 것 |

플러그인 파일 125개 전부 git 추적 중이고 트리가 깨끗하다 — 커밋 누락으로 안 실리는 파일은 없다.
상대 `source`라 URL 직접 add 방식으로는 배포 불가(git/로컬 add는 됨).

## 이름 충돌 — 선택지 (판단은 사용자 몫)

`flow@setting-ai`가 user 스코프로 enable 돼 있다. v2도 `flow`라서 동시에 켜지면 `/flow:*` 커맨드 ·
`flow:*` 스킬·에이전트 네임스페이스가 겹치고 훅이 양쪽에서 발화한다. **동명 플러그인 동시 enable 의
해소 규칙은 공식 문서에서 못 찾았다** — 어느 쪽이 이기는지 미정의로 봐야 한다.

1. **`claude --plugin-dir plugins/flow`** — 설치 없이 그 세션에만 로드. `--setting-sources`로 user 설정을
   빼면 flow@setting-ai 로드 자체를 배제할 수 있을 것이다(이 조합의 동작은 추측 — 한 번 확인 필요).
2. **테스트 기간만 개명** — plugin.json·marketplace.json 두 곳의 `name`을 `flow2` 등으로 바꿔 설치,
   컷오버 때 되돌림. 충돌 원천 차단, 대신 `/flow2:*`로 떠서 문서와 이름이 어긋난다.
3. **컷오버** — flow@setting-ai 를 disable/uninstall 하고 v2 설치. 되돌리기 쉬우나 사용 중 환경을 건드린다.
4. 그대로 둘 다 설치 — 비추천(위 미정의 동작).

참고: v1 저장소 자체의 marketplace.json 도 이름이 `flow-sdlc`다. v1·v2를 마켓플레이스로 동시 등록하면
같은 이름이라 나중 것이 먼저 것을 대체한다(문서 명시) — v2 등록 전에 인지할 것.
