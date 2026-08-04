---
paths:
  - "plugins/flow/**"
  - "guide/*.md"
  - "README.md"
---

# 플러그인 파일을 고칠 때

`plugins/flow/**` 를 읽으면 실린다. 매 턴 실리지 않으므로 **여기 있는 것은 그 파일을 고칠 때만 필요한 것**이다.

## 작성 스타일

**문장·구조 규칙은 `plain-writing` 스킬이 정본이다.** 우리 파일에도 그대로 쓴다.

**절 순서와 골격은 본보기를 열어 맞춘다.**

| 대상 | 본보기 |
|:--|:--|
| 커맨드 | `commands/setup.md` |
| 에이전트 | `agents/gatekeeper.md` |
| 스킬 | `skills/traceability/SKILL.md` |

- **마지막 절은 고정** — 커맨드·에이전트는 `가드레일`, **스킬은 `경계`**.
- **스킬에 `목적`·`적용 시점`·`가드레일`·`함정`·`검증`·`참조` 절을 두지 않는다** — 목적은 첫 문단, 적용 시점은 `description`, 실수는 `경계`, 확인은 그 단계 본문, 다른 스킬은 이름으로.
- **다른 스킬의 문장을 옮겨 적지 않는다** — 정본 하나를 정하고 이름으로 가리킨다. `lint-docs.py`가 유사도로 잡는다.
- **절에 번호·라벨을 붙이지 않는다**(숫자·`①`·`절차 D`) — `### N단계`만 예외. **`project-template/CLAUDE.md`도 예외가 아니다** — 밖에서 절 **이름**으로 가리킨다. 번호를 붙이면 **사용자가 절을 하나 더할 때 밖의 참조가 조용히 어긋난다.**
- **`description`은 한 논리 줄** — 무엇을 하나 + 누가 쓰나. 길면 folded(`>-`). **매 턴 실린다** — 커맨드가 `## 연결`에 이름을 적으니 이걸로 추론하지 않는다.

**스킬은 두 등급이다.** 16개 전부 어떤 커맨드의 `## 연결`에 이름이 있지만, **커맨드 없이도 발동해야 하는 것**과 **불릴 때만 도는 부품**은 `description`을 다르게 쓴다.

| 등급 | 어느 것 | `description`을 어떻게 |
|:--|:--|:--|
| **자율** — 사용자가 커맨드 없이 그 일을 시켜도 발동해야 한다 | `impact-analysis` · `plain-writing` · `tdd-verify` · `drift-check` · `code-audit` · `code-review` · `ops-doc` | **발동 조건을 쓴다** — 어떤 상황에서 필요한지. 이게 없으면 커맨드 밖에서 안 뜬다 |
| **호출 전용** — 커맨드가 맥락·설정을 주입해야 돈다 | `default-reference` · `doc-template` · `doc-verify` · `traceability` · `contract-gate` · `code-graph` · `test-spec` · `theme-apply` · `usecase` | **소관을 못 박고 늘리지 않는다.** `/flow:X 가 쓴다`를 **지우지 않는다** — 그 절이 오발동을 막는 신호다 |

- **`disable-model-invocation: true`를 쓰지 않는다** — 커맨드가 스킬을 부르는 것이 곧 모델 발동이다. 붙이면 **체인이 끊긴다.**
- 등급을 옮기면 이 표와 그 스킬 `description`을 함께 고친다.
- **소관은 대상을 정의해 가른다** — *"X에는 안 쓴다"* 를 나열하지 않는다. *"대상은 읽히는 글이다"* 라고 정하면 계약은 정의상 빠진다.
- **`tools`는 최소 권한** — 읽기로 되면 읽기만. **코드 쓰기는 `builder`만.** `model:`은 넣지 않는다.

**절을 더하는 조건은 아래가 전부다.** 이름은 내용에 맞게.

| 조건 | 무엇을 두나 | 실제 이름 |
|:--|:--|:--|
| **전제가 없으면 잘못된 결과를 낸다** | 전제를 **앞에.** "멈춘다"와 "적고 진행한다"를 가른다 | `시작 전 확인` · `두 모드` · `스택 무관 원칙` |
| **정해진 자리에 산출물을 쓴다** | **실제 출력 문자열**을 코드블록으로 | `출력 형식` · `반환 형식` · `실패 시 동작` |

- **출력 형식을 "템플릿을 따른다"로 대신하지 않는다** — 형식이 매번 달라져 `gatekeeper`가 읽을 자리가 흔들린다.

**frontmatter를 잘못 쓰면 파일이 통째로 안 뜬다.**

| 실수 | 무슨 일이 나나 |
|:--|:--|
| `argument-hint: [기능명] [옵션]` | **닫는 `]` 뒤에 값이 이어지면 파일 전체가 안 뜬다**(공백·주석은 괜찮다). **언제나 작은따옴표로 감싼다** |
| `Name`·`Description` 대문자 | Claude Code가 못 읽어 **커맨드·스킬이 안 뜬다.** 소문자로 |

## 참조 통제

**플러그인 파일끼리는 절을 가리키지 않는다. 이름만 쓴다.**

```
규약은 `code-review`.            ← 이렇게
규약은 `code-review`의 `층`.      ← 이렇게 말고
```

발동되면 파일 전체가 실린다 — **절 이름은 정보를 안 주고 깨질 자리만 만든다.**

| 어디서 어디로 | 무엇을 가리켜도 되나 |
|:--|:--|
| 플러그인 파일 → **템플릿 · `project-template/CLAUDE.md`** | **절·열 이름까지** 된다 — 사람이 채우는 골격이라 좌표가 필요하다 |
| 플러그인 파일 → **`guide/`** | **안 된다** — 컨텍스트에 안 실린다 |
| **`CLAUDE.md`·이 파일** → 아무 곳 | **절·표 이름까지** 된다 — 고칠 자리를 찾는 색인이다 |

- **같은 파일 안의 자기 절을 가리키는 것은 해당하지 않는다.**
- **지운 파일을 가리키는 줄을 남기지 않는다** — 이관 흔적은 옮긴 뒤 지운다.

## 바꿀 때 같이 고칠 곳

| 바꾼 것 | 같이 고칠 곳 |
|:--|:--|
| **커맨드** 추가·삭제·개명 | `getting-started` 커맨드 표 · `README` 흐름·트리 · `run.md` 체인·게이트 표 · `ask.md` 라우팅 표 · `default-reference` 커맨드별 표 · 부르는 커맨드의 `## 연결` · **`plugin.json`+`marketplace.json` 둘 다** · `lint-docs.py`의 `NO_PROSE` |
| **커맨드 인자·모드** | `argument-hint` · 그 커맨드 `## 입력` · **`default-reference`의 템플릿 열**(모드별) · `getting-started` 커맨드 표 · `run.md` 체인·게이트 표 · `ask.md` 라우팅 |
| **에이전트·스킬** 추가·삭제 | `getting-started` 표 · 쓰는 커맨드의 `## 연결` · `default-reference` · `lint-docs.py`의 `OUT_TPL`·`ROUNDTRIP` — 없으면 출력 형식 검사가 **조용히 안 돈다** |
| **훅** 추가·삭제·이름 변경 · **차단 케이스 추가** | **`hooks.test.sh`에 케이스를 먼저** — 없으면 통과 숫자가 그대로다 · `hooks.json` 등록(빠지면 안 돈다) · **훅 머리말(차단 목록 정본)** · `CLAUDE.md`의 `워크플로우`·`가드레일` · `project-template/CLAUDE.md` 표와 §4 · `agents/builder.md` · `setup.md` 훅 설치 절 · `drift-check` · `getting-started` 자동화 절 · `README` 트리와 `되돌릴 수 없는 것은…` 절 |
| **템플릿** 추가·삭제 | `doc-verify` 매핑표 · `00.ref/README`·`doc/README` 목록 · 쓰는 커맨드의 `## 연결` · `default-reference` 템플릿 열 |
| **템플릿 내용**(절·용어) | **`doc-verify`의 등급 표**(매핑표가 아니다) · **그 템플릿을 쓰는 스킬의 `출력 형식`**(짝은 `OUT_TPL`·`ROUNDTRIP`) · 기존 프로젝트는 `VERSION`으로 판정하니 **내보낼 때 버전을 올린다** · 용어를 바꿨으면 `setup` 1-A 치환 안내에도 |
| **`project-template/CLAUDE.md` 절 이름** | 그 이름으로 가리키는 커맨드·스킬·템플릿·`doc/README`·`00.ref/README`·`presets`·`guide` 전부. 확인은 `grep -rn "CLAUDE.md\`의" plugins/ guide/`. **번호(`§N`)로 되돌리지 않는다** — 사용자가 절을 더하면 어긋난다 |
| **`project-template/` 에 파일 추가·삭제** | **`setup.md` 절차 1의 복사·병합 목록**(빠지면 안 깔린다) · `project-template/.gitignore`(전역 gitignore가 `.claude/`를 무시한다) · `README` 트리 · 그 파일을 읽는 커맨드의 `## 연결` |
| **`CLAUDE.md`의 절 이름** | `README`의 `고치는 법` 행 · `lint-docs.py`의 실패 메시지 |
| **산출물 경로·번호** | **`project-template/doc/README.md`(정본)** → 템플릿 폴더 · `setup.md` · 커맨드 경로 · `getting-started` · `drift-gate.yml.example` · `drift-hook.sh` · `README` 트리 |
| **doc 폴더 구조** | 위 + `project-template/CLAUDE.md` · `00.ref/README.md` |
| **다이어그램 표기** | **`doc-template`(정본)** → 템플릿 코드블록 전부 · `prd`·`design`의 그림 언급 · `explorer` 반환 형식 · `presets/tools` 렌더 절 · `publish.md` 절차 3-1 |
| **발행 범위** | `publish.md` 절차 3의 소스 표 · `default-reference`의 `/flow:publish` 행 — 어긋나면 빠진 문서가 조용히 안 나간다 |
| **드리프트 판정** | **`drift-check`(정본)** → `drift-hook.sh` · `drift-gate.yml.example` — 어긋나면 *"로컬 통과, CI 차단"* 이다. `hooks.test.sh`가 둘을 나란히 돌린다 |
| **`presets/` 카탈로그** | 원형은 **복제하면 바로 도는 repo만**. 도구는 종류·용도·설치 명령·마커·`없을 때`를 적는다 |

지운 이름·옛 경로가 남았는지는 `grep -rn` 으로 훑는다.
