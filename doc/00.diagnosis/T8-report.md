# T8 — 문서를 T4 의 구조(`entry`/`exit`)에 맞추고, CI 에 공식 검증기를 넣었다

네 관문 초록 — `lint.py` 34 통과 · 실패 0 · 고장 0 · 대상 0건 0 · `gen_docs --check` 4곳 일치.
`ci.yml` 은 YAML 파싱과 넣은 명령의 로컬 실행(exit 0)까지 확인했다. `plugins/**`·`scripts/**` 는 안 건드렸다.

## 전제를 직접 확인했다

T4 의 목록을 믿지 않고 topology 를 읽었다 — **`entry.content` 는 11개 커맨드 전부 비어 있고**,
내용 조건 5개(`prd.level-decision`·`design.requirement-covered`·`build.contract-followed`·
`verify.coverage-gap`·`review.finding-severity`)는 전부 `exit.content` 에 있다. T4 의 서술과 일치한다.

## 고친 자리 전수

### T4 가 넘긴 것 — `entry`/`exit` 반영

| 자리 | 무엇 |
|:--|:--|
| `doc/01.architecture.md:33-41` | **`### 내용 게이트에는 시점 축이 있다 — 대개 퇴장 조건이다`** 절 신설 — 진입/퇴장 정의 · 5개가 퇴장인 이유(진입 시점에는 판정할 대상이 없다, D5) · `producedBy`/`gate-timing` · `next` 전환 게이트는 직전 커맨드의 퇴장 조건 · 시점 축이 `content` 에만 있는 이유 |
| `doc/01.architecture.md:268` | `gatekeeper` 행 *"진입 게이트의 내용 판정"* → *"게이트의 내용 판정 — 대개 퇴장 게이트다"* |
| `doc/02.skills-map.md:246-248` | *"진입 조건만 읽는다"* → 게이트 조건(`exit.content`·`entry.content`) + 5개 전부 퇴장·entry 11개 공백과 그 이유 |
| `README.md:29` | 내용 판정 시점을 명시 — *"그 커맨드가 끝낼 때"* + 이유 한 줄 |
| `README.md:35` | *"진입 조건(등급별)"* → *"게이트 조건(진입·퇴장, 등급별)"* |
| `CLAUDE.md:14` | 정본 표 *"위상·진입 조건·게이트 면제"* → *"위상·게이트 조건(진입·퇴장)·게이트 면제"* (마커 밖) |
| `guide/getting-started.md:14` | 같은 문구 교정 |

### 지도 오류 2건 (W2) — **둘 다 아직 살아 있었다.** topology 에 맞췄다

| 자리 | 실제 상태 → 조치 |
|:--|:--|
| `doc/02.skills-map.md:236` | `build` 의 `doc-template` 이 여전히 `(조건)` 칸에 있었다. topology `commands.build.loads.skills` 와 `build.md:19` 는 무조건 → 무조건 칸으로 옮김. 조건인 것은 `task-doc` **조각**뿐이라는 문장을 `:251-253` 에 명시 |
| `doc/02.skills-map.md:137` | `canon-map` 싣는 쪽에 `build` 가 여전히 있었다. topology 소비자는 `sync`·`design`(기능)·`review`(문서)뿐 → `build` 삭제, `design`(기능) 으로 정밀화 |

### T4·W2 목록에 없었는데 내가 찾은 것 — 지도↔topology 드리프트 7건 (전부 topology 에 맞춤)

| 자리 | 무엇이 어긋났나 |
|:--|:--|
| `:235` `design`(기능) 행 | `default-reference/delegation` 누락 · 조건 조각 `code-graph/service-boundary` 누락 |
| `:236` `build` 행 | 조건 조각 `code-graph/service-boundary`(계약·MSA) 누락 |
| `:241` `sync` 행 | `drift-check/rule` 조각 누락 (스킬 열에는 있었다) |
| `:77` `coverage.md` 소비자 | `prd` 누락 — 같은 지도의 `:233` 과 topology 엔 있다 |
| `:107` `integration.md` 소비자 | `verify`(`branch`·`project`) — topology 모드명은 `통합·커버리지` |
| `:108` `llm-cost.md` 소비자 | `verify` 가 있었으나 topology 의 어느 verify 모드도 안 싣는다 → `build` 만 |
| `:127`·`:146`·`:182`·`:192` | `service-boundary` 에 `design`(기능—조건) 추가 · `task-doc` 의 `build` 조건 표기 · `rule.md` 에 `sync` 추가 · `delegation.md` 에 `prd` 추가 |

## CI — 공식 검증기 (`.github/workflows/ci.yml:73-80`)

- **넣은 것**: `npm install -g @anthropic-ai/claude-code` 설치 단계 + `claude plugin validate ./plugins/flow` · `claude plugin validate .` 실행 단계. 머리말 목록(`:18-19`)과 `README.md:153` 의 검사표에도 한 줄씩.
- **`claude` 부재 시**: 조용히 건너뛰지 않는다 — `command -v claude || exit 1` 이 `::error::` 와 함께 실패시킨다. 기존 `도구 확인 (건너뜀을 통과로 세지 않기 위해)` 단계와 같은 원칙.
- **실측한 것**: 두 명령 로컬 exit 0 · **빈 HOME + API 키 없이도 exit 0**(인증 불요) · 깨진 매니페스트에 exit 1(검증기가 실제로 실패할 수 있음을 확인) · npm 패키지 `@anthropic-ai/claude-code@2.1.226` 실재(로컬 `claude 2.1.226` 과 동일 버전) · YAML 파싱 통과.

## 확인 못 해 남긴 것

- **ubuntu 러너에서의 첫 실행은 실측 못 했다** — 인증 불요·exit code 는 macOS 로컬(claude 2.1.226) 실측이고, Linux 러너에서 같으리라는 것은 **추측**이다. 다르면 `command -v` 가 아니라 validate 단계가 실패하므로 조용히 통과할 길은 없다.
- `npm install -g` 가 러너에서 도는 것도 실행 전이다(setup-node 22 가 이미 있어 전제는 갖춰져 있다).

## 안 고친 것

- `doc/03.style-proposals.md:48` 의 *"진입 조건"* — H1 수리 당시의 **과거 서술**이라 사실이 맞다.
- `README.md`·`CLAUDE.md` 의 `<!-- flow:gen -->` 마커 안 — 전부 마커 밖만 고쳤고 `gen_docs --check` 4곳 일치로 확인.
- `plugins/**`·`scripts/**`·금지 목록의 doc — 그대로다. lint 가 빨간 적도 없어 `--only` 분리는 필요 없었다.
