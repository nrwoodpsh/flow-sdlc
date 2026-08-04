---
name: contract-gate
description: 계약 파일을 컴파일해 Exit code 로 판정하는 게이트. 스택 무관. /flow:spec·/flow:build·/flow:sync 가 쓴다.
---

# 계약 검증 게이트 (스택 무관)

계약 파일은 워크플로우의 SSOT다. 자연어가 아니라 **기계 검증 가능한 형식**으로 작성하는 이유는 컴파일러/타입체커가 환각·오타를 자동으로 잡기 때문이다. 이 스킬은 그 게이트를 **스택에 독립적으로** 적용한다.

## 스택 무관 원칙

게이트는 특정 언어(TypeScript)에 하드코딩되지 않는다. 프로젝트의 `workflow.config.json`이 검증 방식을 주입한다:

```jsonc
{
  "contract": {
    "pathGlob": "*/3.contract/*.ts",     // 계약 파일 판정 — 경로 전체로 본다
    "gate": "npx -y -p typescript tsc --noEmit --strict {file}"   // 검증 명령 (판정은 이것만)
  }
}
```

**경로로 판정한다 — 파일명으로 하지 않는다.** 계약 이름은 `3.contract/{도메인}.ts`(예: `shorts.ts`)라서 파일명이 도메인마다 다르다. 파일명 패턴을 쓰면:

| 패턴 | 결과 |
|:--|:--|
| `api-contract.ts` | **`shorts.ts`를 못 잡는다** → 훅이 조용히 통과 → 검증이 아예 안 돈다 |
| `*.ts` | **소스 코드 전체**가 게이트에 걸린다 |
| `*/3.contract/*.ts` | 계약만 잡는다 ✅ |

스택별 예시:

| 스택 | contract.pathGlob | contract.gate |
|:---|:---|:---|
| TypeScript | `*/3.contract/*.ts` | `tsc --noEmit --strict {file}` |
| Java/Spring | `*/3.contract/*.java` | `./gradlew compileJava` |
| Python | `*/3.contract/*.py` | `mypy {file}` |
| OpenAPI | `*/3.contract/*.yaml` | `npx @redocly/cli lint {file}` |

- **`.prompt.md`는 대상이 아니다** — 텍스트라 컴파일이 안 된다. 출력 형식만 `.ts`로 떼어 검증한다(`/flow:spec`).
- **레거시 폴백**: 계약이 고정 파일명 한 개인 프로젝트는 `contract.file`(basename 패턴)을 쓸 수 있다. `pathGlob`이 먼저 맞으면 그것으로 판정한다.
  - **유닛 사슬을 쓰면서 `contract.file`만 두면 계약이 검증되지 않는다** — basename이 도메인마다 달라 안 잡힌다. `/flow:setup` 업데이트 모드가 이걸 발견하면 `pathGlob`으로 이관을 제안한다.
- **둘 다 비어 있으면 `*/3.contract/*.ts`가 기본값**이다.

> **단일 파일 게이트 전제**: 계약 파일은 **self-contained**(외부 import 없이 타입·상수·enum만)로 유지한다. 그래야 단일 파일 검증(`tsc {file}`)이 cross-file import 문제 없이 성립한다. 외부 타입이 꼭 필요하면 프로젝트 인식 게이트(`tsc -p tsconfig.json` 등)로 `contract.gate`를 설정한다.

## 통과 기준

- `contract.gate` 명령 Exit code 0
- 에러·경고 없음

## 실패 원인을 먼저 가른다

**게이트가 실패했다고 계약이 틀린 것이 아니다.** 원인이 둘인데 처리가 완전히 다르다.

| 원인 | 신호 | 어디로 |
|:--|:--|:--|
| **계약이 틀렸다** | `error TS2322: Type 'string' is not assignable…` — **파일·줄을 가리키는 타입 오류** | 계약을 고친다 |
| **설정·환경이 틀렸다** | `command not found` · `Cannot find module` · **네트워크 오류** · 인자 오류 · Exit 127 | **`/flow:setup`으로 돌아간다** — 계약을 고쳐도 안 된다 |

**구분하지 않으면 계약을 3회 고치려 시도하고 3회 다 실패한다.**

```
❌ npx: command not found            → 설정 문제. setup 으로
❌ error TS2322 at user.ts:14         → 계약 문제. 고친다
❌ ETIMEDOUT registry.npmjs.org       → 네트워크. 아래
```

**오프라인일 수 있다.** 기본 `gate`가 `npx -y -p typescript tsc …`라 **캐시가 없으면 네트워크를 쓴다.**

| 상황 | 어떻게 |
|:--|:--|
| 네트워크 오류로 실패 | **계약 문제가 아니다.** 그 사실을 알리고 멈춘다 |
| 사내망·오프라인 환경 | `gate`를 **로컬 설치 명령으로 바꾼다** — `./node_modules/.bin/tsc --noEmit --strict {file}` |

- **`/flow:setup`이 `gate`를 한 번 실행해 확인**하지만, **그때 온라인이고 나중에 오프라인일 수 있다.**
- **원인을 모르면 "계약이 틀렸다"고 적지 않는다** — `확인 필요`로 남기고 사람에게 넘긴다.

## 실패 시 동작

**차단하는 것은 커맨드다.** 훅은 없다 — `/flow:spec`은 통과 전까지 완료로 보고하지 않고, `/flow:build`는 사전 게이트에서 멈춘다.

**환경 문제를 걸러낸 뒤**(위) 남은 것이 계약 문제다. 그다음은 **어느 커맨드에서 났나**로 갈린다.

| 언제 | 무엇을 하나 |
|:--|:--|
| **`/flow:spec`** — 계약을 쓰는 중 | **그 자리에서 고친다.** 지금 만들고 있는 것이다 |
| **`/flow:build`** — 통과했던 계약이 실패 | **에러를 읽어 가른다** — 아래 |

**`build`에서는 에러가 분류를 말해 준다.** 우리가 판단하지 않는다.

| 에러가 말하는 것 | 처리 |
|:--|:--|
| **문법이 안 맞는다** (`'}' expected`) · **오타라고 컴파일러가 지목** (`Did you mean 'string'?`) | **고치고 task `History`에 이탈로 적는다.** 고쳐도 뜻이 안 바뀐다 |
| **무엇인지 모른다** (`Cannot find name 'Role'`) · **어느 쪽이 맞는지 골라야 한다** (`not assignable`) | **멈춘다** → `/flow:design`(구조가 맞나) → `/flow:spec`(계약 재작성) |

- **에러 번호로 하드코딩하지 않는다** — 게이트는 스택 무관이다. `mypy`·`gradlew`·`redocly`는 번호가 다르다. **읽어서 판단한다.**
- **모르겠으면 멈춘다.** 계약은 task와 M:N이라 **잘못 고치면 다른 task가 조용히 깨진다.**
- **코드에 맞춰 계약을 고치지 않는다** — 나쁜 구현을 SSOT로 세탁하는 것이다.

## 경계

- **게이트를 우회·완화하지 않는다.** `--noEmit`을 빼거나 `any`로 덮어 통과시키는 것은 금지 — 계약이 거짓말을 시작한다.
- **컴파일 통과가 계약이 맞다는 뜻은 아니다.** 파일별로 컴파일하니 **유닛끼리 같은 이름 타입이 다르게 정의돼도 둘 다 통과한다** — 그건 `/flow:review`가 본다.
- **`/flow:build`에서 뜻을 정해야 하는 실패는 자율 교정 금지.** 멈추고 `design`→`spec`으로 돌린다.
- **`contract.gate`를 커맨드가 임의로 바꾸지 않는다** — 프로젝트 설정이다.
