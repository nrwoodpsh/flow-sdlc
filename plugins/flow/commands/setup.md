---
description: 프로젝트 초기 세팅
argument-hint: '[list | {원형키:egov-msa-cc…} | {git-url} | (비움=대화형)]'
---

# /flow:setup — 프로젝트 초기 세팅

프로젝트 고유층(`CLAUDE.md`·`workflow.config.json`·`doc/`)을 만든다.
골격은 자동, 추론값은 자동, **결정·정책은 질문**. 없으면 스캐폴딩하므로 clone·cp 불필요.

## 연결

- **에이전트**: `explorer` (광범위 스캔 시)
- **스킬**: `plain-writing`(생성 문서 문장) · `traceability`(도메인 후보·경로 규약)
- **템플릿**: 없음 — **`project-template/` 전체를 그대로 복사**한다. 읽어서 쓰는 것이 아니다
- **참조**: `${CLAUDE_PLUGIN_ROOT}/project-template/` (**복사 원본**) · `${CLAUDE_PLUGIN_ROOT}/presets/architectures/README.md` (원형 정본) · `${CLAUDE_PLUGIN_ROOT}/presets/tools/README.md` (LSP·MCP 카탈로그) · `${CLAUDE_PLUGIN_ROOT}/presets/template-sync.md` (**업데이트 모드에서만**)

## 입력 (`$ARGUMENTS`)

| 인자 | 동작 |
|:--|:--|
| (비움) | 대화형. 빈/신규면 카탈로그 메뉴, 진행중이면 목록만 보여주고 진행 |
| `list` | 원형 목록만 출력·정지 (`${CLAUDE_PLUGIN_ROOT}/presets/architectures/README.md` 읽어 렌더) |
| 원형키 | 바로 복제 — `egov-msa-cc` … `agent-app` · `mcp-server` · `custom` · `none` |
| git URL | 그 repo를 커스텀 원형으로 복제 |

**넷 중 하나만 받는다.** 문장으로 설명하는 입력은 받지 않는다 — 세팅에 필요한 값은 전부 감지하거나 목록에서 고른다.

## 절차

**0. 대상 선언** (작업 전 필수)

```
[/flow:setup] 대상: {경로} · 상태: {빈 프로젝트 | 기존 코드 있음 | 이미 세팅됨(업데이트 모드)}
              원형: {키 또는 "없음"}   스택: {감지값 또는 "질문 필요"}
              만들 것: CLAUDE.md · .claude/rules/ · workflow.config.json · doc/ 골격 · .claude/settings.json
              건드리지 않을 것: 기존 코드 · 이미 있는 파일
              → 진행할까요?
```

- **파일을 만들기 전에 무엇을 만드는지 먼저 보여준다.** 이 커맨드는 파일 생성·repo 복제·도구 설치를 한다 — 되돌리기 번거롭다.

**1. 골격** — 없으면 생성

> **지어내지 말고 복사한다.** 원본은 `${CLAUDE_PLUGIN_ROOT}/project-template/`다. 이 폴더의 파일을 그대로 복사한 뒤 프로젝트 값(이름·스택)만 치환한다. 특히 **`doc/00.ref/03.templates/` 전체**를 빠짐없이 복사한다 — 이게 이후 모든 산출물의 골격이자 `doc-verify`의 채점 기준이다.

- **`03.templates/VERSION`을 채운다** — `flow:` 에 플러그인 버전(`plugin.json`), `복사:` 에 날짜. **업데이트 모드가 이 값으로 동기화 필요를 판정**한다.

- `README.md`(루트) : **프로젝트 소개 + flow 흐름 + `doc/README` 링크**. **없을 때만 생성** — 기존 README 안 건드림. 전체 구조 트리는 넣지 않음(중복 방지).
- `doc/README.md` : **doc 구조 정본** — 전체 트리(최하단) + 규칙 + README 체계. (트리는 여기 한 곳만.)
- `doc/00.ref/README.md` : ref 색인. `00.ref/01.domain/00.common.md` · `03.templates/`(산출물 템플릿 — `doc-verify`의 채점 기준) · `04.theme/`·`05.explainer/`(빈 폴더) 함께.
- `spike/README.md` · `CLAUDE.md` · `workflow.config.json`
- **`.gitignore`·`.claude/settings.json`은 덮지도 건너뛰지도 않는다 — 합친다.** 기존 파일이 있으면 빠진 줄·키만 더한다.
  - `.gitignore` — 없으면 만들고, 있으면 **빠진 줄만 추가**한다. **두 줄을 반드시 확인한다.**
    - `spike/*` — 건너뛰면 실험 코드가 커밋된다.
    - **`!.claude/` + `.claude/*` + `!.claude/settings.json` + `!.claude/rules/`** — **전역 gitignore가 `.claude/`를 무시하는 기계가 많다.** 이 예외가 없으면 `settings.json`과 `rules/`가 **에러 없이 조용히 미추적**되어 팀에 안 나간다. `git check-ignore -v .claude/rules/code-style.md`로 확인한다.
  - `.claude/settings.json` — 없으면 만들고(마켓 + flow 활성화), 있으면 **`enabledPlugins`에 flow만 더한다.** 다른 키는 손대지 않는다 — 건너뛰면 팀원에게 flow가 안 붙는다.
  - `.claude/rules/code-style.md` — 없으면 복사한다. **있으면 건드리지 않는다** — 프로젝트가 채운 규칙이다. `paths`에서 이 프로젝트에 없는 확장자를 지울지 묻는다.
- **전체 폴더 골격 일괄 생성**: `01.work`·`02.decisions`·`03.integration`(`00.branch`·`01.project`)·`04.ops`·`00.ref/00.architecture`·`02.db-schema`·`04.theme`·`05.explainer` 폴더 + **영역 인덱스 README**(`01.work`·`02.decisions`·`03.integration`·`04.ops` — 플레이스홀더). 내용(요구·설계·유닛 산출물)은 `/flow:prd`·`/flow:design`·`/flow:spec`·`/flow:sync`가 채운다.
  - **빈 폴더에는 원본에 `.gitkeep`이 들어 있다** — git이 빈 폴더를 추적하지 않아 복사만으로는 안 생기기 때문이다. 복사하면 함께 온다. **내용이 생기면 지워도 된다.**
- 규약: 생성된 `doc/README.md` (구조 정본 — 트리·번호·README 체계, 프로젝트 로컬)
- **업데이트 모드** (이미 채워진 프로젝트): 빈 항목만 제안 · 덮지 않음 · 원형 복제 안 함. **단 `03.templates/`는 아래 1-A로 동기화를 제안**한다.

**1-A. 템플릿 동기화** *(업데이트 모드에서만)*

```
03.templates/VERSION 의 flow:  값  ↔  plugin.json 의 version
   같다  → 건너뛴다
   다르다 → ${CLAUDE_PLUGIN_ROOT}/presets/template-sync.md 를 읽고 그 절차를 따른다
```

**새 프로젝트면 이 절을 건너뛴다** — `VERSION`을 새로 채우면 끝이다. 절차 본문을 여기 두지 않는 이유가 그것이다.

**1-B. repo 구성 확인** *(배포 단위가 여럿일 때만)*

**`doc/`를 어디에 둘지 정해야 한다.** 코드는 repo가 갈려도 `doc/`는 하나다 — 흩어지면 요구 ID 추적이 repo 경계를 못 넘는다(`doc/README`).

```
배포 단위가 여럿으로 보입니다. repo 구성이 어느 쪽입니까?
  1. 모노repo — repo 하나에 서비스 여럿          → doc/ 는 이 repo에
  2. 서비스마다 repo                            → doc/ 를 어디에 둘까요?
       a) 지금 이 repo (주 repo)   b) 별도 doc repo를 만든다
```

- **1이면 그냥 진행한다** — 기본 구성이다.
- **2면 `doc/`의 위치를 확정하고 `13.architecture` 구성 요소 표의 `repo` 열을 채운다.**
- **repo를 넘으면 못 하는 것을 알린다** — 드리프트가 repo 경계를 못 보고, `code-graph`가 서비스 간 호출을 못 따라간다(`doc/README`의 표).

**2. 스캔** — 스택 식별

- 지표 읽기: `package.json` · `build.gradle` · `pyproject.toml` · `go.mod` …
- 광범위하면 `explorer`에 위임
- 지표 없으면 스택을 질문

**3. 원형** *(빈 프로젝트만)*

- 인자로 받았으면 바로 / 없으면 카탈로그 메뉴
- **`원형 소스`가 `{{…}}`인 항목은 목록에서 `준비 안 됨`으로 표시하고 고를 수 없게 한다** — URL이 없어 clone이 실패한다. 골랐으면 그 사실을 알리고 `none`으로 진행할지 묻는다.
- 검증 repo 복제: `--depth 1` → `.git` 제거 → 이름 치환
- 복제 후 `workflow.config.json` · `doc/00.ref/00.architecture` 조정
- **기존 코드 있으면 복제 안 함** (목록만 참고 표시)

**4. 초안** (추론)

- `CLAUDE.md`의 `정체성` · `.claude/rules/code-style.md`(네이밍·폴더·테스트)
- `doc/00.ref/01.domain/` — 도메인 후보 (경계는 "확인 필요")
- (선택) `03.templates` 패턴 역추출

**`workflow.config.json`의 실행 키는 실제로 돌려 확인한다.** 안 맞으면 게이트가 **조용히 안 돌거나** 매번 실패한다.

| 키 | 무엇 | 스택에 맞춰야 |
|:--|:--|:--|
| `contract.pathGlob` | 계약 파일 판정 — **경로 전체** | 확장자 (`*/3.contract/*.ts`·`*.java`·`*.py`) |
| `contract.gate` | 계약 검증 명령 | 컴파일러·타입체커 |
| `build.command` | 전체 빌드 | 빌드 도구 |
| `test.command` | 테스트 실행 | 테스트 러너 |
| `test.browser` | `playwright` 또는 `chrome` | **화면이 있으면 둘 중 하나 필수** |

- **`contract.pathGlob`을 파일명 패턴으로 두지 않는다** — 계약 이름은 `{도메인}.ts`라 도메인마다 다르다. 고정 파일명을 쓰면 훅이 못 잡고 **조용히 통과**한다(`contract-gate`).
- **업데이트 모드에서 `contract.file`을 보면 이관을 제안한다.** 구버전 config다. 그 모드로 두면 `{도메인}.ts` 계약이 **검증되지 않는다.**

  ```
  ⚠ workflow.config.json 에 구버전 키 contract.file = "api-contract.ts" 가 있습니다.
    유닛 사슬(3.contract/{도메인}.ts)을 쓰면 이 패턴은 계약을 못 잡습니다 — 게이트가 조용히 통과합니다.
    → contract.pathGlob = "*/3.contract/*.ts" 로 바꿀까요?  [바꾼다 / 그대로 (계약이 고정 파일명 하나다)]
  ```

  - **`doc/01.work/*/*/3.contract/` 에 파일이 하나라도 있으면 이관을 권한다** — 유닛 사슬을 쓰는 증거다.
  - **그대로 두기로 하면 그 사실을 절차 7 요약에 적는다** — "계약 게이트는 `api-contract.ts`만 본다".
- **`build.command`가 비면 `/flow:build` 절차 6이 건너뛴다** — 전체 컴파일 오류가 커밋까지 안 잡힌다. 빌드 도구가 없는 프로젝트(스크립트·인터프리터)만 비운다.
- `contract.gate`·`build.command`·`test.command`는 **한 번 실행해 Exit 0을 확인**한다. 못 돌리면 그 사실을 기록하고 사용자에게 알린다.
- **`gate`에 `npx`를 쓰면 네트워크에 매인다.** 기본값 `npx -y -p typescript tsc …`는 캐시가 없으면 받아온다 — **사내망·오프라인이면 게이트가 실패하고, 그걸 "계약이 틀렸다"로 오판한다**(`contract-gate`).

  | 환경 | 권장 `gate` |
  |:--|:--|
  | 온라인·개인 | `npx -y -p typescript tsc --noEmit --strict {file}` (기본) |
  | **사내망·오프라인** | **로컬 설치로 바꾼다** — `./node_modules/.bin/tsc --noEmit --strict {file}` |

  **오프라인 가능성을 물어 결정한다.** 지금 온라인이어도 나중에 오프라인일 수 있다.

**5. 도구 제안·설치**

정본은 `${CLAUDE_PLUGIN_ROOT}/presets/tools/README.md`다. 스택을 보고 **골라 제시하고, 고른 것을 설치한다.**

**5-1. 목록 제시** — **종류와 마커를 이름 앞뒤에 그대로** 보여준다. 무엇이 자동이고 무엇이 사람 몫인지 미리 알아야 한다.

```
[/flow:setup] 도구 — 감지 스택: Next.js + FastAPI

  [필수·택1] 화면 테스트 — 하나는 반드시 골라야 합니다
    ( ) Playwright        MCP    [자동]        제가 설치합니다
    ( ) Claude in Chrome  확장   [사용자 설치]  크롬 웹스토어에서 직접

  [필수] 기본 선택 — 해제할 수 있습니다
    (v) Joern (CPG)       CLI     [자동]        code-graph의 엔진 · 무겁습니다
    (v) open-code-review  CLI     [자동]        리뷰 룰 검출 (NPE·XSS·SQLi)
    (v) typescript-lsp    플러그인 [사용자 설치]  명령을 안내합니다
    (v) pyright-lsp       플러그인 [사용자 설치]
    (v) claude-security   플러그인 [사용자 설치]  취약점 스캔 (발견을 반박 후 보고)
    (v) ponytail          플러그인 [사용자 설치]  코드를 덜 만들게 · 과설계 삭제 목록
    (v) drift 훅          CLI     [자동]        커밋 전 문서 누락 차단

  [선택]
    ( ) DB (Supabase)     MCP    [인증필요]     감지 엔진에 맞춰 · 읽기 전용
    ( ) GitHub            MCP    [인증필요]     PR·이슈 논의 조회 (쓰기 안 함)
    ( ) Figma             MCP    [인증필요]     디자인에서 테마 토큰
    ( ) Notion            MCP    [인증필요]     /flow:publish 발행
    ( ) Context7          MCP    [자동]        라이브러리 최신 문서
    ( ) codex             플러그인 [사용자 설치]  ⚠ 유료 · 코드가 OpenAI로 전송
    ( ) session-report    플러그인 [사용자 설치]  토큰·캐시 실측 리포트
    ( ) CI 게이트         파일   [자동]        복사만, 켜는 건 직접

  [감지에 따라] — 스택·원형에 맞는 공식 스킬을 그때 찾아 안내
    ( ) mcp-server-dev    플러그인 [사용자 설치]  원형이 mcp-server일 때
    ( ) {스택}            플러그인 [사용자 설치]  convex·cloudflare·databricks 등

  고르세요 (번호·이름 여러 개 가능)
```

**종류가 설치 방법을 정한다** — `MCP`·`CLI`는 제가 깔고, `플러그인`·`확장`은 명령만 안내한다.

**`[감지에 따라]`** — 스택·원형을 보고 그때 마켓에서 찾는다. **카탈로그가 목록을 들고 있지 않다**(마켓이 계속 늘어난다). **없으면 없다고 한다** — 지어내지 않는다.

**5-2. 마커별 실행** — 고른 것을 하나씩 처리한다.

| 마커 | 무엇을 하나 |
|:--|:--|
| `[자동]` | **권한 승인 후 셸로 설치**하고 결과를 보고한다. 실패하면 명령과 오류를 보여준다 |
| `[인증필요]` | 서버 등록까지 하고 **인증 절차를 안내**한다 — "설정 → 커넥터 → {서비스}" 또는 토큰 발급처 |
| `[사용자 설치]` | **명령·경로를 그대로 제시**한다. 실행은 사용자가 한다 |
| `[필수·택1]` | 하나도 안 고르면 **다시 묻는다.** 건너뛰면 `/flow:verify`가 나중에 멈춘다고 알린다 |

**5-3. 안내문** — `[인증필요]`·`[사용자 설치]`는 **복사해 쓸 수 있게** 낸다.

```
직접 하셔야 하는 것

1. typescript-lsp  — 아래를 붙여넣으세요
   /plugin marketplace add anthropics/claude-plugins-official
   /plugin install typescript-lsp@claude-plugins-official

2. Claude in Chrome — 크롬 웹스토어에서 확장 설치 후 로그인
   설치되면 /flow:verify unit chrome 으로 씁니다

3. ponytail        — 설치 뒤 두 가지를 더 해주세요
   /plugin marketplace add DietrichGebert/ponytail
   /plugin install ponytail@ponytail
   /ponytail full                              ← 강도
   PONYTAIL_SUBAGENT_MATCHER=builder           ← 코드 쓰는 창까지 넣기 (환경변수)

4. GitHub MCP      — 등록은 마쳤습니다. 인증만 해주세요
   설정 → 커넥터 → GitHub (또는 토큰 발급 후 재등록)
```

**5-4. 결과 기록** — 무엇이 깔렸고 무엇이 남았는지 절차 7 요약에 넣는다. 안 깔린 것은 **"없으면 어떻게 되는지"**도 함께.
- **drift 훅**: `${CLAUDE_PLUGIN_ROOT}/git-hooks/drift-hook.sh`를 **`pre-commit`** 으로 설치한다. **커밋 전에 코드↔문서를 보고 어긋나면 막는다.**

  **`.githooks/`에 두고 `core.hooksPath`를 가리키는 것이 기본이다** — 그래야 파일이 커밋되어 clone마다 다시 깔 필요가 없고, 플러그인이 올라가도 낡지 않는다.

  | 프로젝트 상태 | 어떻게 |
  |:--|:--|
  | **훅을 안 쓴다** (대부분) | `.githooks/pre-commit`에 복사 + `git config core.hooksPath .githooks` |
  | **`core.hooksPath`가 이미 있다** (husky·lefthook) | **그 폴더에** 넣는다. 설정을 덮지 않는다 |
  | 같은 이름 훅이 이미 있다 | **덮지 않는다.** 기존 파일 끝에 호출 한 줄을 더할지 묻는다 |

  - **`git config`는 커밋되지 않는다** — clone한 사람은 파일은 있어도 설정이 없어 훅이 안 돈다. `check-drift-hook.sh`가 세션 시작에 알린다.
  - 설정 키가 없다. 끄려면 훅을 빼거나 `core.hooksPath`를 해제한다. 범위는 `drift.sourceGlobs`·`drift.ignore`로 조절한다.

  - **`core.hooksPath`를 먼저 확인한다** — 값이 있는데 `.git/hooks/`에 넣으면 **실행되지 않는다.** 확인 없이 넣고 "설치 완료"로 보고하면 거짓말이 된다.
- **CI 게이트**: `project-template/.github/workflows/drift-gate.yml.example`를 복사만 한다(기본 꺼짐). 켜는 건 사용자가 확장자를 벗긴다.
- 정본: `${CLAUDE_PLUGIN_ROOT}/presets/tools/README.md`

**6. 못 채운 것만 되묻기**

**step Q&A를 하지 않는다.** 빈 프로젝트에서는 도메인·커밋 규약을 아직 모른다 — 물어도 답이 안 나온다.

| 언제 | 묻는다 |
|:--|:--|
| 스택 지표가 없다 | `무슨 언어·프레임워크입니까?` |
| 테스트 명령을 못 찾았다 | `테스트는 어떻게 돌립니까?` |
| 기존 코드가 있다 | `감지한 도메인 후보 {user·order}가 맞습니까?` |

- 나머지는 **비워두고 어디서 채워지는지 알린다** — 도메인은 `/flow:prd domain`, **브랜치·커밋 규약은 `/flow:commit`**(처음 돌 때 한 번 물어 `CLAUDE.md`의 `Git 규약`에 저장), 가드레일은 `CLAUDE.md`의 `가드레일` 기본값.
- **추측으로 채우지 않는다.** 모르면 `{{...}}`를 그대로 남긴다.

**7. 요약**

**채운 것**과 **비워둔 것**을 나눠 보여주고 검수 요청.

```
채운 것    스택 {감지값} · 테스트 {명령} · 원형 {키}
설치됨     {도구 목록}
남은 것    {사용자가 직접 할 도구} — 위 안내 참고
비워둔 것  도메인 → /flow:prd domain · 브랜치·커밋 규약 → /flow:commit
안 깔린 것 {도구} → {없으면 어떻게 되는지}
```

## 가드레일

- **추론은 자동, 결정·정책은 질문.** 가드레일·도구 정책·도메인 경계·커밋 규약은 코드에 없다 → 추측 금지.
- **템플릿을 지어내지 않는다.** `project-template/`에서 복사한다 — 특히 `03.templates/`를 빠뜨리면 이후 산출물에 기준이 없어진다.
- 기존 코드 수정 금지 (원형 복제는 빈 프로젝트만).
- 도구는 **선택 확인 후 설치** — `[자동]`은 권한 승인 하에 실행, 체크 해제 항목은 건너뛴다. **크리덴셜·OAuth·비밀정보 입력·저장은 절대 AI가 하지 않는다**(사용자만).
- **설치했다고 거짓 보고하지 않는다.** `[사용자 설치]`·`[인증필요]`는 **남은 일로 명시**하고 명령을 그대로 준다.
- **설치 명령을 지어내지 않는다.** 카탈로그에 없는 것은 벤더 문서를 안내한다 — 틀린 명령은 사용자 시간을 버린다.
- **`[필수·택1]`을 그냥 넘기지 않는다** — 안 고르면 다시 묻고, 끝내 안 고르면 어느 커맨드가 멈추는지 알린다.
- 실제 값 덮어쓰기 금지 (있으면 확인 후 갱신).
- `/init`과 다름 — `/flow:setup`은 flow 층(config·domains 포함) 전체 세팅.
