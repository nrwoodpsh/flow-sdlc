# T2 — `setup` 소스 경로 확정 (D1)

## 무엇을 고쳤나

| 파일 | 무엇 |
|:--|:--|
| `project-template/workflow.config.json` | `drift.sourceGlobs` 기본을 `["src/**","app/**"]` → **`[]`**. `drift.ignore` 에 3줄 추가(`workflow.config.json`·`**/*.lock`·`**/*-lock.json`). `$note` 로 왜 비우나를 파일 안에 남김 |
| `commands/setup.md` | `### 소스 경로 확정` 신설(스택 스캔 뒤·실행 키 앞) · 실행 키 표에 `drift.sourceGlobs` 행 · 게이트 직접 실행 확인 · 요약 블록에 `소스 범위` 줄 |

새 절차 조각을 만들지 않았다 — `setup.md` 본문 안에서 끝났으므로 **`topology.commands.setup.procedures` 배선이 필요 없다.**
`+22` 줄(setup.md 171 → 193). topology·scripts·skills·다른 커맨드는 손대지 않았다.

## 설계 판단과 근거

### 1. 화이트리스트 기본값을 없앤다 — 빈 값이 틀린 값보다 안전하다

`sourceGlobs` 는 **값이 있으면 그 안만 소스**로 치는 화이트리스트다(`gate-source-write.sh:218-220`,
`drift-hook.sh:84-88`). 그래서 **틀린 값의 실패 방향이 fail-open 하나뿐이다** — 안 막고, 아무 말도 안 한다.

빈 값이면 규칙 ③ (`doc/`·`spike/`·`.claude/`·`.github/` 밖이고 `.md` 아님)이 도는 블랙리스트다.
틀리면 **과차단**으로 나온다 — 화면에 이유가 뜨고 고쳐진다.

> 좁으면 안 막혀서 안 보이고, 넓으면 막혀서 보인다. 그래서 **모르면 넓게** 가 이 키의 기본값이다.

레거시에서 특히 그렇다. 신규 JS 프로젝트는 `src/**` 가 맞을 확률이 높지만, 주 사용 상황은 레거시 변형이고
(`00.concept.md`) 거기서 `src/**` 는 **틀릴 확률이 더 높은 추측**이다. 추측을 기본값으로 배포하지 않는다.

과차단 비용은 이미 있는 면제가 받친다 — `no-units`(도입 첫날 전부 통과) · `spike/**` ·
`drift.ignore` · `gate.legacyExempt`(T3) · `any-unit-has-task` 폴백. **켜지고 나서 좁히는 길은 있고,
꺼진 것을 알아채는 길은 없다.**

### 2. 감지 실패 시 — 비워 두고, 비웠다고 말한다

절차의 3번 항목이 이것이다. **지어내서 채우지 않는다.** 감지 실패의 결과가 "게이트 없음"이 되지 않게,
실패 경로가 곧 넓은 기본 규칙으로 떨어지도록 기본값을 비운 것이 1번 판단과 같은 결정이다.
요약 블록에 `소스 범위 {globs 또는 "비움 — 기본 규칙"}` 을 넣어 **비운 상태가 화면에 남게** 했다 —
v1 이 낡은 방식이 정확히 "아무 말 없이"였다.

넓어서 막히면 `drift.ignore`·`gate.legacyExempt` 로 좁히라고 적었다. **`sourceGlobs` 를 좁혀서 푸는 것은
게이트를 통째로 끄는 쪽**이라 명시로 막았다.

### 3. 빈 기본값의 부작용 두 개만 `drift.ignore` 로 막았다

빈 `sourceGlobs` 에서는 설정·생성물도 소스가 된다. 그중 둘은 그냥 두면 안 된다.

- **`workflow.config.json`** — 게이트가 **자기 판정 근거를 못 고치게 잠근다.** topology 가 `flow-own-docs`
  면제에 적어 둔 것과 같은 이유다(*"게이트가 자기 근거 문서를 막으면 고칠 길이 없다"*). 실측으로 확인함.
- **잠금 파일**(`*.lock`·`*-lock.json`) — 생성물이라 설계 문서와 짝지을 것이 없는데 커밋은 잦다.
  드리프트로 잡히면 의존성 갱신마다 커밋이 막힌다.

`package.json`·`Dockerfile` 같은 나머지 빌드 파일은 **넣지 않았다.** 프로젝트마다 다르고, 열거하면
목록이 정본을 자처하게 된다 — 막히면 사람이 그때 `drift.ignore` 에 더하는 쪽이 맞다.

### 4. 남의 관례와 공존 (능력 11)

- 스캔이 최상위 디렉터리별 소스 파일 **개수**를 세게 했다 — 이름을 아는 것이 아니라 세는 것이라
  `cmd/`·`internal/`·`src/main/java/` 같은 못 보던 관례도 잡힌다. `node_modules`·`vendor`·`dist`·`build`·`target` 제외.
- **모노repo·다중 모듈** — 배포 단위마다 한 줄(`packages/*/src/**`·`services/*/**`). 기존 `repo 구성 확인`
  단계가 이미 모노repo 를 묻고 있어 그 뒤에 자연히 이어진다.
- **디렉터리 이름을 우리 관례로 바꾸지 않는다**고 못 박았다 — `setup` 이 `lib/` 를 `src/` 로 옮기려 들면 안 된다.

## 실측

스크래치 repo `/tmp/flow-t2-legacy` (코드를 `lib/`·`backend/api/` 에, 유닛 1개 + `src/login.ts` 를 담은
task 문서 1개). 훅 호출은 `scripts/tests/hooks.test.sh` 방식 그대로 —
`gate-source-write.sh --path … --root … --why` · `git add` 후 `drift-hook.sh`. **끝나고 지웠다.**

### 고치기 전 — 결함 재현 (템플릿 기본값 `["src/**","app/**"]`)

| 경로 | 드리프트 훅 | 쓰기 게이트 |
|:--|:--|:--|
| `lib/x.ts` | **아님** | **allow (not-source)** — `drift.sourceGlobs 밖` |
| `backend/api/h.ts` | **아님** | **allow (not-source)** |
| `src/other.ts` | 드리프트 | deny (not-declared) |

**기계 두 개가 `lib/`·`backend/` 에서 동시에, 아무 말 없이 꺼져 있었다.** D1 그대로다.

### 고친 뒤 ① 템플릿 기본값(비움) 그대로

| 경로 | 드리프트 훅 | 쓰기 게이트 |
|:--|:--|:--|
| `lib/x.ts` | **드리프트** | **deny (not-declared)** |
| `backend/api/h.ts` | **드리프트** | **deny (not-declared)** |
| `src/other.ts` | 드리프트 | deny (not-declared) |
| `workflow.config.json` (유효 JSON 단독 스테이징) | 아님 (rc=0) | allow (`drift.ignore`) |
| `yarn.lock` | 아님 | allow (`drift.ignore`) |
| `doc/notes.md` | 아님 | allow |

**두 기계가 켜졌다.** 자기 설정 잠금·잠금 파일 과차단도 안 난다.

### 고친 뒤 ② 절차대로 채움 (`["lib/**","backend/**"]`)

`lib/`·`backend/` 는 위와 같이 두 기계 켜짐, `src/other.ts` 는 `not-source` 로 범위 밖. **의도대로 좁혀진다.**

### 절차가 지시하는 확인 명령이 실제로 판별하나

```
--path lib/x.ts              → gate: deny (not-declared)        # 안쪽
--path docs-site/index.html  → gate: allow (not-source)         # 바깥
유닛 없을 때(도입 첫날) lib/x.ts → gate: allow (no-units)
유닛 없을 때 src/other.ts        → gate: allow (not-source)
```

유닛이 없어도 **`no-units` 와 `not-source` 가 갈려서** 글로브가 맞는지 판별된다.
그래서 절차에 *"안쪽이 `not-source` 로 나오면 글로브가 틀린 것"* 이라 적을 수 있었다.

### 완료 조건

```
python3 scripts/lint.py            검사 26 · 통과 26 · 실패 0 · 검사기 고장 0
bash scripts/tests/hooks.test.sh   통과 371 · 실패 0
python3 scripts/gen_docs.py --check  생성물 4곳이 정본과 같다
```

## 남긴 것과 넘기는 것

| 무엇 | 왜 |
|:--|:--|
| **`guide/getting-started.md:227`** 예시 config 가 `"sourceGlobs": ["src/**"]` | 내 소유가 아니다. 234줄이 이미 *"구조가 다르면 그 글로브를 먼저 고친다"* 라 적어 두어 틀리진 않지만, **템플릿 기본과 어긋난다** — 비운 값으로 맞추는 편이 낫다 |
| `skills/drift-check/references/rule.md:10` 의 `(예: src/**·app/**)` | 다른 워커 소유. *예시*라 오해 소지는 낮다 |
| `topology` 배선 | **필요 없다.** 새 조각을 안 만들었다 |
| `sourceGlobs` 를 검사로 강제하는 것(예: 빈 값이 아닌데 그 경로에 파일이 없으면 실패) | 사용자 프로젝트의 값이라 이 리포의 `lint.py` 로는 못 본다. `setup` 의 실측 단계가 그 자리다 |
| `drift.ignore` 기본에 `package.json`·`Dockerfile` 류 | 위 판단 3 — 열거하면 목록이 정본을 자처한다 |

**추측** — 빈 `sourceGlobs` 의 과차단 빈도. 실측한 것은 위 표의 경로들뿐이고, 실제 레거시 리포에서
어떤 설정 파일이 얼마나 자주 걸릴지는 안 세어 봤다. T3(`legacyExempt`)가 이 비용을 받는 자리라고 본다.
