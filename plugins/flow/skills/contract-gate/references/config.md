# 게이트 설정 — 스택 무관

게이트는 특정 언어에 하드코딩되지 않는다. 프로젝트의 `workflow.config.json` 이 검증 방식을 주입한다.

```jsonc
{
  "contract": {
    "pathGlob": "*/3.contract/*.ts",     // 계약 파일 판정 — 경로 전체로 본다
    "gate": "npx -y -p typescript tsc --noEmit --strict {file}"   // 판정은 이 명령만
  }
}
```

## 경로로 판정하고 파일명으로 하지 않는다

계약 이름은 `3.contract/{도메인}.ts` 라서 파일명이 도메인마다 다르다. 파일명 패턴을 쓰면 이렇게 된다.

| 패턴 | 결과 |
|:--|:--|
| `api-contract.ts` | **`shorts.ts` 를 못 잡는다** → 훅이 조용히 통과 → 검증이 아예 안 돈다 |
| `*.ts` | **소스 코드 전체**가 게이트에 걸린다 |
| `*/3.contract/*.ts` | 계약만 잡는다 ✅ |

## 스택별 예시

| 스택 | `contract.pathGlob` | `contract.gate` |
|:--|:--|:--|
| TypeScript | `*/3.contract/*.ts` | `tsc --noEmit --strict {file}` |
| Java·Spring | `*/3.contract/*.java` | `./gradlew compileJava` |
| Python | `*/3.contract/*.py` | `mypy {file}` |
| OpenAPI | `*/3.contract/*.yaml` | `npx @redocly/cli lint {file}` |

- **`.prompt.md` 는 대상이 아니다** — 텍스트라 컴파일이 안 된다. 출력 형식만 타입 파일로 떼어 검증한다.
- **둘 다 비어 있으면 `*/3.contract/*.ts` 가 기본값**이다.

## 단일 파일 게이트 전제

계약 파일은 **self-contained** 로 유지한다 — 외부 import 없이 타입·상수·열거만 둔다. 그래야 단일 파일 검증이 교차 import 문제 없이 성립한다.

외부 타입이 꼭 필요하면 **프로젝트 인식 게이트**로 `contract.gate` 를 바꾼다 (`tsc -p tsconfig.json` 등).

## 레거시 폴백

계약이 고정 파일명 하나인 프로젝트는 `contract.file`(basename 패턴)을 쓸 수 있다. `pathGlob` 이 먼저 맞으면 그것으로 판정한다.

- **유닛 사슬을 쓰면서 `contract.file` 만 두면 계약이 검증되지 않는다** — basename 이 도메인마다 달라 안 잡힌다.
- `/flow:setup` 이 이걸 발견하면 `pathGlob` 으로 이관을 제안한다.
- **`/flow:setup` 은 `gate` 를 한 번 실행해 확인한다** — 설정만 적어 두면 나중에 조용히 실패한다.
