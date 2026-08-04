# 추천 도구 (LSP · MCP · CPG · 스킬) — /flow:setup이 설치하는 것

> **[시스템 참조]** `/flow:setup`이 도구 제안·설치 시 읽는 정본.

`/flow:setup`은 스택을 감지해 아래를 제시한다 — 스택에 맞는 것은 **`[필수]`로 추천(기본 선택)**, 나머지는 **`[선택]`**. 사용자가 확정하면 **선택 항목을 설치까지 실행**한다.

**종류를 이름 앞에 반드시 붙인다** — 종류가 설치 방법을 정한다.

| 종류 | 설치 | AI가 깔 수 있나 |
|:--|:--|:--:|
| **MCP** | `claude mcp add …` — **셸 명령** | ✅ |
| **플러그인** | `/plugin install …` — **대화형 슬래시 커맨드** | ❌ 사용자가 |
| **확장** | 브라우저 웹스토어 | ❌ 사용자가 |
| **CLI** | `npm i -g …` · `brew install …` — 셸 | ✅ |
| **스킬** | **설치가 없다** — Claude Code 내장(`docx`·`pdf` 등) | — 이미 있다 |

> **공식이냐 아니냐는 상관없다.** Notion MCP도 공식이지만 셸이라 AI가 깔고, `skill-creator`는 공식이지만 플러그인이라 못 깐다.

**설치 마커:**
- **`[자동]`** — 크리덴셜이 없어 `/flow:setup`이 **확인(권한 승인) 후 셸로 바로 설치** (MCP·CLI).
- **`[인증필요]`** — 서버·설정 등록은 자동, **OAuth·토큰 입력은 사용자**가 마친다 (AI가 대신 못 함 — 보안).
- **`[사용자 설치]`** — 설치 자체를 사람이 한다. **플러그인·확장**이 여기 해당한다.
- **`[필수·택1]`** — 묶음 중 **하나는 반드시** 있어야 한다. 없으면 그 커맨드가 멈춘다.
- 전제: `node`·`jdk` 등 기반 툴체인이 있어야 하며, 없으면 그 설치부터 안내한다.
- **새 도구는 이 형식(종류·용도·설치 명령·마커·없을 때)으로 여기에 추가**한다.

**대부분은 있으면 쓰고 없으면 대체한다** — 도구가 없다고 커맨드가 멈추지 않는다. 각 항목에 **없을 때 어떻게 되는지**를 반드시 적는다.
**예외는 브라우저 하나뿐** — 화면을 안 보고 "통과"라고 적는 건 검증이 아니라서 대체 경로를 두지 않았다.

## LSP (Language Server) — 코드 "의미" 이해

LSP를 붙이면 Claude Code가 grep이 아니라 **타입·정의·참조·실시간 컴파일 에러**로 코드를 이해한다. `/flow:build`·`/flow:review`의 정확도가 크게 오른다.

**공식 플러그인이 가장 쉽다.** Anthropic 마켓에 스택별 LSP 플러그인이 있다 — 직접 설치하는 것보다 간단하다.

```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install {스택}-lsp@claude-plugins-official
```

| 스택 | **플러그인** (권장) | **CLI** 직접 설치 (대체) |
|:---|:---|:---|
| **Java/Spring/eGov** | `jdtls-lsp` | JDK + jdtls |
| TypeScript/Node | `typescript-lsp` | `npm i -g typescript-language-server typescript` |
| Python | `pyright-lsp` | `npm i -g pyright` |
| Go | `gopls-lsp` | `go install golang.org/x/tools/gopls@latest` |
| 그 밖 | `rust-analyzer-lsp` · `clangd-lsp` · `ruby-lsp` · `php-lsp` · `kotlin-lsp` · `swift-lsp` · `csharp-lsp` · `lua-lsp` | 각 언어 배포판 |

- **플러그인 경로 = `[사용자 설치]`** — `/plugin install`은 대화형이라 `/flow:setup`이 **명령만 안내**한다.
- **CLI 경로 = `[자동]`** — 셸이라 setup이 바로 깐다. 플러그인을 안 쓰겠다면 이쪽으로.
- **없을 때**: grep·`Read`로 대체된다. `/flow:build`·`/flow:review`의 정확도가 떨어질 뿐 동작은 한다.
- 직접 설치 시 설정 위치: 프로젝트 `.lsp.json` (또는 플러그인 `lspServers`).

> eGov/Spring 프로젝트라면 **jdtls를 붙이는 걸 강력 권장** — 계약 게이트(tsc)와 별개로 Java 컴파일 수준 진단을 얻는다.

## MCP (외부 도구 연결)

**전부 종류가 MCP다** — `claude mcp add`로 등록하므로 `/flow:setup`이 깔 수 있다.

| 도구 | 종류 | 어느 커맨드가 쓰나 | 마커 | 설치 | 없을 때 |
|:---|:---|:---|:---|:---|:---|
| **DB — 개발** | **MCP** | `/flow:design`·`/flow:build`·`/flow:verify` — 컬럼 확인 · **마이그레이션 실행해 검증** · 시드 | `[인증필요]` | 엔진마다 다름 — **벤더 문서를 따른다** | `02.db-schema/` 파일만 본다. 마이그레이션은 사람이 돌린다 |
| **DB — 운영·스테이징** | **MCP** | `/flow:prd legacy` — 현행 스키마 파악 | `[인증필요]` `[선택]` | **읽기 전용 계정으로만** | 사람이 스키마를 떠서 `02.db-schema/`에 넣는다 |
| **Context7** | **MCP** | `/flow:spec`·`/flow:build` — **쓰는 라이브러리의 최신 문서**를 끌어온다. 낡은 API로 짜는 것을 막는다 | `[자동]` `[선택]` | `npx ctx7 setup --claude` (대화형 OAuth) · 무료 등급 있음 | 학습 시점 기억에 의존 — 버전이 다르면 틀릴 수 있다 |
| **GitHub** | **MCP** | 아래 `이력 조회` 절 | `[인증필요]` `[선택]` | `claude mcp add --transport http github https://api.githubcopilot.com/mcp` · 또는 설정→커넥터 | 로컬 `git log`만 |
| **Figma** | **MCP** | 아래 `디자인` 절 | `[인증필요]` `[선택]` | `claude mcp add --transport http figma https://mcp.figma.com/mcp` · 또는 설정→커넥터 | `.md` 스펙을 사람이 준다 |
| **Git** | **MCP** | `/flow:sync`·`/flow:commit` — 브랜치·커밋 메타 | `[자동]` `[선택]` | `claude mcp add git npx -y @modelcontextprotocol/server-git` | 로컬 `git` 명령으로 충분 |

**DB는 환경마다 따로 붙인다 — 권한이 다르다.**

| 환경 | 권한 | 왜 |
|:--|:--|:--|
| **개발·로컬** | **읽기·쓰기·스키마 변경 전부** | 마이그레이션을 **실제로 돌려봐야** 스크립트가 맞는지 안다. 시드·초기화도 필요하다. 언제든 다시 만들 수 있는 DB다 |
| **운영·스테이징** | **읽기 전용** | 되돌릴 수 없다. 아예 안 붙이는 것이 기본이고, 붙일 때도 조회만 |

```
claude mcp add db-dev  …   # 전권
claude mcp add db-prod …   # 읽기 전용 계정 (필요할 때만)
```

- **이름으로 구분한다** — `db-dev`·`db-prod`. 접속 문자열이 어느 환경인지 헷갈리면 사고가 난다.
- 프로젝트 규칙은 `CLAUDE.md`의 `가드레일`·`도구 정책`에 적는다.

> **명령이 확실치 않으면 지어내지 말고 벤더 문서를 안내한다.** 틀린 명령은 사용자 시간을 버린다. 위 명령도 패키지가 바뀔 수 있으니 실패하면 그 도구의 저장소를 확인한다.

- 설정 위치: 프로젝트 `.mcp.json` 또는 `.claude/settings.json`의 `mcpServers`.
- **DB MCP는 감지한 엔진에 맞춰 제시한다** — Postgres · MySQL · **Supabase** · Neo4j · MongoDB 등. 목록에는 엔진 이름을 붙여 보여준다(`DB MCP (Supabase)`).
- **운영·스테이징은 읽기 전용**, 개발은 전권 (위 표).
- 엔진마다 서버 패키지·인증 방식이 다르다. **정확한 설치 명령은 그 벤더 문서를 따르고**, 지어내지 않는다. Supabase는 액세스 토큰이 필요하다 — `[인증필요]`.

### 브라우저 — `/flow:verify`·`/flow:theme`

화면이 있는 테스트는 **브라우저를 띄워 실제로 클릭**한다. 모드는 `workflow.config.json`의 `test.browser`.

**둘 중 하나는 반드시 고른다 — 대체 경로가 없다.** 화면을 안 보고 "통과"라고 적는 것은 검증이 아니다. 프론트가 없는 프로젝트면 이 항목 자체를 제시하지 않는다.

| 도구 | 종류 | 모드값 | 언제 | 마커 | 설치 |
|:---|:---|:---|:---|:---|:---|
| **Playwright** ⭐ | **MCP** 또는 **플러그인** | `playwright` (기본) | 케이스가 확정된 회귀 테스트 · CI 재실행 | **`[필수·택1]`** | 아래 두 경로 |
| **Claude in Chrome** | **확장** | `chrome` | 시나리오를 처음 만들 때 · 화면을 눈으로 봐야 판단될 때 | **`[필수·택1]`** `[사용자 설치]` | 아래 |

**Playwright 설치는 두 경로 중 하나** — 결과는 같다.

| 경로 | 명령 | 마커 |
|:--|:--|:--|
| MCP 직접 | `claude mcp add playwright npx @playwright/mcp@latest` | `[자동]` — setup이 깐다 |
| 공식 플러그인 | `/plugin install playwright@claude-plugins-official` | `[사용자 설치]` — 명령만 안내 |

**Claude in Chrome 설치** — 셸로 안 되니 사용자가 한다.

1. [claude.ai/chrome](https://claude.ai/chrome) 에서 확장을 받는다 (또는 크롬 웹스토어에서 "Claude in Chrome" 검색)
2. 크롬에 설치하고 **Claude 계정으로 로그인**
3. 설치되면 `/flow:verify unit chrome`으로 쓴다

> 확장이 붙으면 Claude Code에 브라우저 도구가 자동으로 나타난다 — 별도 MCP 등록이 필요 없다.

- **둘 다 없으면 `/flow:verify`·`/flow:theme`이 멈추고 설치를 안내한다.**
- 둘 다 있어도 된다 — 상황에 맞게 인자로 고른다(`/flow:verify unit chrome`).
- `chrome` 모드는 **모달·확인창을 띄우는 조작을 피한다** — 대화가 멈춘다.

### 디자인 — `/flow:theme`

| 도구 | 종류 | 용도 | 마커 | 없을 때 |
|:---|:---|:---|:---|:---|
| **Figma** | **MCP** | 디자인 파일에서 색·타이포·간격을 읽어 `15.theme` 스펙을 채운다 | `[인증필요]` · `[선택]` | 사람이 `.md` 스펙을 `@파일`로 준다 (기본 방식) |
| **frontend-design** (Anthropic 공식) | **플러그인** | **스펙이 아예 없을 때** 테마 초안을 만든다 | `[선택]` `[사용자 설치]` | Claude가 직접 만든다 — 결과 형식은 같다 |

```
/plugin install frontend-design@claude-plugins-official
```

> **스펙이 있으면 쓰지 않는다.** 우리 원칙은 *받은 값을 정확히 반영*이다. 있는 스펙의 빈칸을 이걸로 채우면 사람 결정과 AI 추측이 섞여 구분이 안 된다.
> 생성한 것은 `15.theme`에 **`출처: AI 초안` · `상태: 승인 대기`** 로 남고, **승인 전에는 코드에 적용하지 않는다.**

### 이력 조회 — `/flow:design`·`/flow:prd legacy`·`/flow:review`

| 도구 | 종류 | 용도 | 마커 | 없을 때 |
|:---|:---|:---|:---|:---|
| **GitHub** | **MCP** | **왜 이렇게 됐나**를 찾는다 — PR 리뷰 코멘트·이슈 논의·revert 사유. 커밋 메시지에 없는 배경이 여기 있다 | `[인증필요]` · `[선택]` | 로컬 `git log`만. 코드 변경은 보이지만 **논의는 안 보인다** |

> **조회 전용이다.** PR·이슈를 **만들거나 고치지 않는다.** push·merge는 사람이 외부 툴로 한다(`CLAUDE.md` 가드레일).
> 대신 `/flow:sync`가 **PR 초안 텍스트**(제목·본문·`gh` 명령)를 제시한다 — 올리는 건 사람이다.

### 최소 구현 — `/flow:build`·`/flow:review`·`/flow:prd legacy`

AI는 코드를 필요 이상으로 만든다 — 랩퍼·안 쓸 유연성·추상화 계층. **코드 쓰기 전에 판단 순서를 강제**한다.

```
1. 안 만들어도 되나?  2. 있는 걸 쓸 수 있나?  3. 언어·프레임워크 기본 기능인가?  4. 그래도 안 되면 만든다
```

| 도구 | 종류 | 무엇을 | 마커 | 없을 때 |
|:---|:---|:---|:---|:---|
| **ponytail** ⭐ | **플러그인** | ① 코드 쓸 때 판단 순서 자동 주입 ② `/ponytail-review` — **삭제 목록** ③ `/ponytail-audit` — 저장소 전체 과설계 지도 | **`[필수]`** `[사용자 설치]` | `code-audit`·`builder` 규칙으로 대체 — **문장 지침이라 강제력이 약하고 삭제 목록·전체 감사는 못 한다** |

```
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
/ponytail full
```

**★ `builder`까지 들어가야 한다.** 우리는 코드를 `builder` 서브에이전트가 쓴다. 메인 세션에만 주입되면 **코드 쓰는 쪽이 못 본다.**

```
PONYTAIL_SUBAGENT_MATCHER=builder
```

**강도 4단** — 사용자가 `/ponytail {모드}`로 정한다. **커맨드가 자동으로 바꿀 수 없다**(슬래시 명령이라).

| 모드 | 언제 |
|:--|:--|
| `ultra` | `/flow:spike` — 버릴 코드다 |
| **`full`** | **기본** — 프로덕션 코드 |
| `lite` | 원형 복제 직후 — 남의 코드 구조를 존중할 때 |
| `off` | — |

- **차단하지 않는다** — 코드 쓰기 전에 지침을 주고 빠진다. `/flow:build`의 3회 루프를 방해하지 않는다.

> **⚠ 아직 검증 안 됨 — 실측 후 이 블록을 지운다.**
>
> | # | 확인할 것 | 안 되면 |
> |:--|:--|:--|
> | ① | **`builder` 서브에이전트에 지침이 실제로 주입되나** (`PONYTAIL_SUBAGENT_MATCHER=builder`) | 코드 쓰는 쪽이 못 보니 **값이 거의 없다 → 제외 재검토** |
> | ② | **주입 토큰 vs 절약 토큰** — 순이득인가. **`session-report`로 켜고 끄며 실측한다** | 순손실이면 `lite`로 내리거나 제외 |
>
> 자체 측정치는 **코드 46% · 토큰 78% · 비용 80% · 시간 73%**(baseline 대비)인데 **n=4 · repo 1개 · Haiku 4.5**로 얇다. 단발 벤치마크(80~94%)는 저자들도 부풀려졌다고 인정한다. **우리 환경에서 재보기 전까지 이 수치를 근거로 쓰지 않는다.**

### 코드리뷰 — `/flow:review`

`/flow:review`는 **층을 쌓아** 본다. 각 도구가 다른 종류의 오류를 잡는다.

| 층 | 도구 | 종류 | 무엇을 잡나 | 마커 | 없을 때 |
|:--|:---|:---|:---|:---|:---|
| 1 | `contract-gate` | 내장 | 타입·컴파일 | — | — |
| 2 | **open-code-review (OCR)** ⭐ | **CLI** | NPE·스레드 안전·XSS·SQLi — **알려진 패턴**. 줄 단위 코멘트 | **`[필수]`** `[자동]` | 룰 기반 검출이 빠지고 LLM 판단만 남는다(오탐 증가) |
| 3 | **Joern (CPG)** ⭐ | CLI | **어디까지 번지나 · 값이 어디로 흐르나** — 전이 영향·taint | **`[필수]`** `[자동]` | 축소 모드(LSP+grep, 1~2홉) — **흐름 추적은 못 한다** |
| 4 | `code-audit` + **ponytail** | 내장 스킬 + 플러그인 | **우리 규약**(계약·명명·범위·테스트) + **과설계 삭제 목록** | ponytail은 위 절 | 체크리스트만 — 삭제 목록 없음 |
| 5 | **claude-security** ⭐ | 플러그인 | 취약점 25종 — **발견을 반박한 뒤 보고**, 패치 제안까지 | **`[필수]`** `[사용자 설치]` | `code-audit` 체크리스트 + LLM 판단만 (오탐 증가) |
| 6 | **codex** | 플러그인 | **`deep`일 때만** — 다른 모델이 설계 선택을 의심 | `[선택]` `[사용자 설치]` | **`deep`이 1~5만 돌고 그렇게 알린다** |
| 7 | `verifier` | 내장 에이전트 | critical·high **반증** | — | — |

**open-code-review** — alibaba, Apache-2.0. 결정론 파이프라인 + LLM 하이브리드.

```
npm i -g @alibaba-group/open-code-review
```

- **위임 모드로 쓴다** — 코딩 에이전트가 **자기 모델로** 리뷰를 돌린다. 별도 LLM 키·비용이 없다.
- 입력은 git diff·staged·커밋 범위·파일 전체. 출력은 줄 단위 코멘트.

**codex** — OpenAI, 별도 마켓. **`/flow:review deep`에서만** 쓴다.

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/codex:setup
```

| 주의 | |
|:--|:--|
| **비용** | ChatGPT 구독 또는 OpenAI API 키가 **따로 든다** — 우리 도구 중 유일하게 유료 |
| **외부 전송** | 코드가 **OpenAI로 나간다.** 사내 프로젝트면 먼저 판단할 것 |
| **없어도 된다** | `deep`이 1~5만 돌고 "codex 없음"을 리포트에 적는다. 멈추지 않는다 |
| **쓰지 않을 것** | `/codex:rescue`(코드를 고친다 — 쓰기는 `builder`만) · `/codex:review`(2·5층과 중복) |

> **`/codex:adversarial-review`만 쓴다.** 값은 *다른 모델이라 우리가 구조적으로 못 보는 것을 본다*는 데 있다. 일반 리뷰는 우리 층이 이미 한다.

**claude-security** — Anthropic 공식. 세션 안에서 로컬 실행.

```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install claude-security@claude-plugins-official
```

- **`code-audit`과 역할이 다르다** — `code-audit`은 *우리 규약을 지켰나*(계약·명명·범위), 이건 *위험한 값·패턴이 있나*.
- **발견을 보고 전에 스스로 반박**한다 — 우리 `verifier`와 같은 사상이라 오탐이 적다.
- **기존 코드도 본다** — `/flow:prd sys legacy`로 받은 남의 코드에도 쓸 수 있다.
- 보안은 **`/flow:review`에서 한 번** 본다. `/flow:commit`은 파일 이름(`.env`·`*.key`)만 확인한다 — 우리 흐름이 `review → sync → commit`이라 커밋 전에 이미 지난다.

## CPG (코드 속성 그래프) — code-graph 스킬의 엔진

`code-graph` 스킬은 코드를 **노드·엣지 그래프**로 만들어 질의한다. 파일을 읽는 게 아니라 **관계를 묻는다.**

**Joern이 본체다.** 이 셋은 그래프 없이는 못 한다.

| 질의 | 그래프로 | LSP·grep으로 |
|:--|:--|:--|
| **외부 입력이 SQL·셸까지 닿나** | 엣지 도달성 계산 | **불가능** |
| **N홉 뒤에 무엇이 깨지나** | 전이 한 번에 | 홉마다 폭발 → 2홉에서 끊어야 함 |
| **인증 없이 DB 쓰는 엔드포인트 전부** | 노드 속성 질의 | **불가능** |

| 도구 | 종류 | 역할 | 마커 |
|:--|:--|:--|:--|
| **Joern** ⭐ | **CLI** | CPG 생성·질의 — 전이 영향·데이터 흐름·속성 검색 | **`[필수]`** `[자동]` |
| LSP (위 표) | 플러그인/CLI | 축소 모드의 심볼 추적 | 위와 같음 |
| grep | 내장 | **CPG 밖** — 설정(yml)·마이그레이션(sql)·템플릿·i18n | — |

**전제: JDK 21.** 없으면 그 설치부터 안내한다.

| OS | 설치 |
|:--|:--|
| **macOS · Linux** | `wget https://github.com/joernio/joern/releases/latest/download/joern-install.sh && chmod +x joern-install.sh && sudo ./joern-install.sh` |
| Windows | [releases](https://github.com/joernio/joern/releases/latest)에서 `joern-cli-windows-{x86_64\|arm64}.zip` 내려 압축 해제 — **`[사용자 설치]`** |
| Docker (설치 대신) | `docker run --rm -it -v $(pwd):/app:rw -w /app ghcr.io/joernio/joern joern` |

- 스크립트가 플랫폼을 감지해 맞는 배포판을 받는다. 실패하면 `./joern-install.sh --interactive`.
- C/C++ 프로젝트면 `gcc`·`g++`가 있어야 시스템 헤더를 찾는다.

- **`[필수]`다.** 스킬 이름이 `code-graph`인 이유가 그래프 질의이고, 그게 없으면 이 스킬의 목적이 사라진다.
- **compute-on-demand** — 상시 인덱스를 두지 않는다. 부를 때 스코프만 계산하고 버린다.
- **언어 프론트엔드는 넓다** — C/C++·Java·JVM 바이트코드·Python·JS/TS·Go·Kotlin·PHP·Ruby·Swift·C#. 다만 **언어마다 정확도가 다르다.**
- **돌려보고 판단한다** — 파싱이 실패하거나 그래프가 빈약하면 **축소 모드**(LSP+grep, 1~2홉)로 내려간다. 그때는 **데이터 흐름·속성 질의를 아예 못 한다**(정확도 `보통`으로 표기하고 "안 함"을 명시).
- **JVM 기반이라 무겁다** — 메모리를 쓴다. 스코프를 좁게 잡는 게 중요하다.
- **그래프 모드에서도 grep은 따로 돈다** — `joern-parse`는 **소스 코드만** 그래프로 만든다. `application.yml`·`.sql`·템플릿은 프론트엔드가 없어 CPG에 안 들어간다. (코드 안 문자열은 Joern이 리터럴 노드로 갖고 있어 겹친다.)

## 스킬 (플러그인) — 선택 설치

**flow 커맨드가 부르지 않는다.** 설치하면 **Claude가 `description`을 보고 스스로 걸거나, 사용자가 직접 부른다.**

```
사용자: 이 프로젝트에서 매번 하는 배포 점검을 스킬로 만들자
        → skill-creator가 걸린다 (의도 정리 → 초안 → 테스트 → 개선)

사용자: 이번 세션 토큰 얼마 썼어?
        → session-report가 걸린다
```

`/flow:` 커맨드 안에서 도는 게 아니라 **평소 대화에서** 쓰는 것이다.

| 도구 | 종류 | 용도 | 마커 | 설치 |
|:---|:---|:---|:---|:---|
| **skill-creator** (Anthropic 공식) | **플러그인** | 프로젝트 고유 반복작업을 스킬로 저작·개선 | `[선택]` `[사용자 설치]` | `/plugin install skill-creator@claude-plugins-official` |
| **session-report** (Anthropic 공식) | **플러그인** | 세션의 **토큰·캐시 효율**을 HTML 리포트로 — 도구를 넣고 빼며 **실측**할 때 | `[선택]` `[사용자 설치]` | `/plugin install session-report@claude-plugins-official` |

### 스택·원형에 맞는 스킬은 그때 찾는다

마켓에는 **벤더가 만든 공식 스킬이 100개 넘게** 있고 계속 늘어난다. **flow가 목록을 들고 있지 않는다** — 금방 낡는다.

**`/flow:setup`이 스택·원형을 감지하면 그때 마켓을 확인해 안내한다.**

| 감지한 것 | 안내할 스킬 |
|:--|:--|
| 원형 `mcp-server` | `mcp-server-dev` — MCP 서버 설계·구축 규약 |
| 원형 `agent-app` | `agent-sdk-dev` — Claude Agent SDK |
| Convex · Cloudflare · Databricks · Auth0 · Appwrite … | 같은 이름의 공식 플러그인 |

- **추천만 한다.** `[선택]` `[사용자 설치]` — 설치는 사용자가.
- **우리 규약과 충돌하지 않는다** — 이 스킬들은 *"그 기술을 어떻게 제대로 쓰나"* 를 준다. *무엇을 만드나* 는 여전히 `2.task`·`3.contract`가 정한다.
- **MCP 서버 프로젝트에서는 도구 스키마가 곧 계약**이다 — `3.contract/{도메인}.ts`에 담으면 `contract-gate`가 그대로 검증한다.
- **없는 것을 지어내 추천하지 않는다.** 마켓에 없으면 없다고 한다.

> **종류가 설치 방법을 가른다.** `npx skills add <repo>`(CLI)는 셸이라 **`[자동]`**, `/plugin install`(플러그인)은 대화형이라 **`[사용자 설치]`** — Claude가 명령만 안내한다.

> 커뮤니티 스킬은 실존·소속이 확인되지 않아 flow가 보증하지 않는다 — 필요하면 사용자가 판단해 개별 설치. flow 카탈로그엔 **공식만** 싣는다.

## 다이어그램 렌더 — 모든 문서 (선택)

**우리 그림은 전부 PlantUML이다**(`doc-template` 다이어그램 절). **텍스트만으로도 읽히므로 렌더는 선택**이다 — 그림을 보고 싶을 때만 깐다.

| 도구 | 종류 | 용도 | 마커 | 설치 |
|:---|:---|:---|:---|:---|
| **plantuml.jar** | **CLI** | 로컬 렌더 — **외부 전송 없음** | `[선택]` `[자동]` | 아래 |
| **PlantUML 확장** | **확장** | 편집기 미리보기 (`Option+D`) | `[선택]` `[자동]`* | 아래 |

**jar** — `brew install plantuml`은 **`graphviz`를 의존성으로 끌어** 100MB 넘게 더 깔린다. jar만 받는 게 가볍다.

```
V=$(curl -sL https://api.github.com/repos/plantuml/plantuml/releases/latest | grep -o '"tag_name": *"[^"]*"' | cut -d'"' -f4)
mkdir -p ~/.local/share/plantuml
curl -sL -o ~/.local/share/plantuml/plantuml.jar \
  "https://github.com/plantuml/plantuml/releases/download/$V/plantuml-${V#v}.jar"
```

**확장** — 여기가 종류 표의 **유일한 예외**다(`*`). 확장은 보통 웹스토어라 사람이 깔지만, **VS Code·Cursor 계열은 편집기 CLI가 있어 셸로 깔린다.**

- **`cursor`·`code` 명령이 있으면 `[자동]`**, 없으면 `[사용자 설치]`로 안내한다 — `/flow:setup`이 명령 존재를 먼저 본다.
- 다른 편집기(JetBrains 등)는 사람이 깐다.

```
cursor --install-extension jebbs.plantuml      # 또는 code / VS Code 계열
```

**설정** (편집기 `settings.json`)

```jsonc
"plantuml.render": "Local",                    // 서버로 보내지 않는다
"plantuml.jar": "~/.local/share/plantuml/plantuml.jar",   // 절대경로로
"plantuml.commandArgs": ["-Playout=smetana"]
```

- **확장 번들 jar를 쓰지 않는다.** `jebbs.plantuml` v2.18.1의 번들은 **PlantUML 1.2021.00**이고, 그 버전은 Smetana가 유스케이스를 못 그려 `Cannot find Graphviz` 에러 이미지가 나온다. **최신 jar를 지정해야** 한다.
- **`-Playout=smetana`로 Graphviz가 불필요해진다.** Smetana는 PlantUML 내장 Java 포팅이라 `dot` 설치가 없어도 유스케이스·클래스·객체·컴포넌트·상태를 그린다. 시퀀스·활동은 애초에 자체 렌더다.
- **Java가 필요하다** — 대개 이미 있다. 없으면 `brew install openjdk`.
- **`PlantUMLServer` 모드는 쓰지 않는다** — 다이어그램 텍스트(액터·기능 이름)가 외부로 나간다. 쓸 이유가 있으면 **먼저 알린다**.
- **없으면**: 그림이 텍스트로만 보인다. **문서 작성·검증은 그대로 된다** — 표↔그림 대조도 텍스트 파싱이다.
- GitHub 웹은 PlantUML을 렌더하지 않는다(mermaid만). 웹에서 봐야 하면 `.svg`를 함께 내보내 커밋한다.

## 성능·원가 측정 — `/flow:verify project`

**요구의 `측정 방법`에 적은 도구는 실제로 있어야 한다.** 없는 도구를 적으면 그 요구는 영구 gap이다 — 잴 방법이 없으니 영원히 검증 안 된다.

| 도구 | 종류 | 용도 | 마커 | 설정 |
|:---|:---|:---|:---|:---|
| **k6** | **CLI** | HTTP 부하 → p95·p99·처리량. 스크립트가 JS라 계약과 같이 관리된다 | `[선택]` `[자동]` | `brew install k6` |
| Lighthouse | **CLI** | 화면 로딩·LCP·번들 크기 | `[선택]` `[자동]` | `npm i -g lighthouse` |
| 원가 합산 | — | **도구가 아니다.** LLM 토큰 로그·스토리지 용량·전송량을 **우리가 코드로 합산**한다 | — | 프로젝트가 만든다 |

- **성능 요구가 없으면 설치하지 않는다.** 대부분의 내부 시스템은 성능 요구가 없다.
- **`/flow:prd`가 측정 방법을 받을 때 도구 존재를 확인한다** — 없으면 그 자리에서 설치를 안내하거나 있는 도구로 방법을 바꾼다.
- **원가는 도구로 안 잰다.** 편당 얼마를 알려면 **우리가 로그를 남겨야** 한다 — 그 로깅이 설계 요소로 나와야 한다.

## 계약 기반 Mock — FE/BE 병행 개발 (선택)

계약(`api-contract`)을 OpenAPI로 변환하면 **Mock 서버가 자동 생성**된다(코딩 없음). BE 구현 전에 FE가 Mock URL로 화면을 먼저 만들고, BE 완성 후 URL만 실제 주소로 바꾸면 된다 — **FE가 BE를 기다리지 않는다.**

- 도구는 무엇이든: Prism·MSW·json-server·Mockoon·Apidog 등. **특정 UI에서 계약을 직접 그리지 말 것** — 정본은 항상 `api-contract`(코드), Mock은 그 산출물이다(lock-in 방지).
- 방향: `api-contract` → OpenAPI 변환 → Mock. 초기 1회 수동 import, 운영 단계에선 CI로 자동 동기화.

## 발행·통합 (마무리 단계 — `/flow:publish`)

개발 결과를 외부로 내보낼 때.

| 도구 | 종류 | 용도 | 마커 | 설정 |
|:---|:---|:---|:---|:---|
| **Notion** ⭐ | **MCP** | 설계·개발 결과를 Notion 페이지로 발행 | `[인증필요]` | `claude mcp add --transport http notion https://mcp.notion.com/mcp` 또는 설정→커넥터→Notion(OAuth) |
| docx·pdf | **스킬** | 설계서·결과 문서(Word/PDF) 생성 | `[선택]` | Claude Code 내장 |
| Google Drive | **MCP** | 산출물 저장·공유 | `[인증필요]` `[선택]` | claude.ai 커넥터 경유 권장 |

> 커뮤니티 스킬(content-repurposing 등)은 실존·소속이 확인되지 않아, 이 워크플로우는 **공식 커넥터·문서 스킬만** 채택한다. 발행처·크리덴셜은 사용자가 설정.

### Notion 연결 (한 번, 수동)

`/flow:publish`를 쓰려면 Notion MCP가 연결돼 있어야 한다. **인증은 AI가 대신 못 한다**(당신 워크스페이스 접근 허가 = 보안).

1. **연결**: OAuth(설정→커넥터→Notion) 또는 `claude mcp add --transport http notion https://mcp.notion.com/mcp`. 야간 자동 발행(헤드리스)이면 **API 토큰 방식** 필요.
2. **공유(닻)**: 통합은 **공유된 부모(DB/페이지) 안에서만** 쓸 수 있다. 발행할 부모를 통합에 공유하고, 그 ID를 `workflow.config.json`의 `publish.notionParent`에 둔다(없으면 첫 발행 때 물어보고 저장).
3. 이후 `/flow:publish`는 그 부모 아래에 **도메인/기능별 페이지를 없으면 생성·있으면 갱신**한다(지정 불필요).

## 원칙

- **선택 후 설치 실행.** `[자동]`은 사용자 확인(권한 승인) 후 `/flow:setup`이 설치, `[인증필요]`는 인증만 사용자. 강요 없음 — 체크 해제하면 건너뛴다.
- **비밀정보는 항상 사람이.** AI가 크리덴셜·토큰·OAuth를 입력·저장하지 않는다.
- MCP는 **세션당 컨텍스트 토큰을 먹는다** — 실제로 쓸 것만 켠다.
- eGov 기본 추천: **LSP=jdtls**, **MCP=`db-dev`(전권)** + (선택)`db-prod`(읽기 전용)·Git.
