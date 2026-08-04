---
paths:
  - "**/*.{ts,tsx,js,jsx,mjs,cjs}"
  - "**/*.{vue,svelte,astro}"
  - "**/*.{java,kt,kts,groovy,scala}"
  - "**/*.{py,go,rb,rs,cs,php,swift,dart}"
  - "**/*.{sql,tf}"
---

# 코드 스타일 (이 프로젝트 고유만)

**소스 파일을 읽을 때만 실린다.** 그래서 `CLAUDE.md`가 아니라 여기 있다 — 매 턴 실리면 코드를 안 건드리는 턴에도 값을 낸다.

- 네이밍: {{예: BE PascalCase 클래스+camelCase 메서드, FE PascalCase 컴포넌트+kebab-case 파일}}
- 폴더 구조: {{예: `kr.co.{회사}.{도메인}.controller/service/mapper`}}
- 테스트: {{예: BE JUnit 5, FE Vitest}}
- {{그 외 이 프로젝트에서만 통하는 규칙}}

**언어 표준을 여기 적지 않는다** — Claude가 이미 아는 것(들여쓰기 관례·표준 라이브러리 용법)은 값을 안 낸다. **기본값과 다른 것만** 적는다.

`paths`는 흔한 확장자를 미리 깔아 둔 것이다. **이 프로젝트에 없는 언어는 지운다** — 남겨도 안 깨지지만 목록이 사실과 어긋난다. 소스가 특정 폴더에만 있으면 `"src/**/*.ts"` 처럼 좁힌다.

브랜치·커밋 메시지 규약은 코드 파일과 무관해 `CLAUDE.md`의 `Git 규약`에 있다.
