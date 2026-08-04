---
colors:     { primary: "{{#0066cc}}", ink: "{{#1d1d1f}}", canvas: "{{#ffffff}}", danger: "{{#d93025}}" }
typography: { display: {fontFamily: "{{Inter}}", fontSize: "{{40px}}", fontWeight: {{700}}, lineHeight: "{{1.1}}", letterSpacing: "{{-0.02em}}"},
              body:    {fontFamily: "{{Inter}}", fontSize: "{{16px}}", fontWeight: {{400}}, lineHeight: "{{1.5}}"} }
rounded:    { sm: "{{8px}}", lg: "{{18px}}", pill: "{{9999px}}" }
spacing:    { xs: "{{8px}}", md: "{{16px}}", lg: "{{24px}}", section: "{{80px}}" }
components: { button-primary: { backgroundColor: "{colors.primary}", color: "{{#fff}}", rounded: "{rounded.pill}", padding: "{spacing.md}" },
              card:           { backgroundColor: "{colors.canvas}", rounded: "{rounded.lg}", padding: "{spacing.lg}" } }
---

# {{테마 이름}} — 테마 정본

> `doc/00.ref/04.theme/` · `/flow:theme` 입력
> **출처**: {{getdesign.md · 사내 디자인시스템 · 피그마 · **AI 초안**}}
> **상태**: {{확정 | 승인 대기}}
> **위 frontmatter가 값의 정본**이다. `{colors.primary}` 같은 참조는 실제 값으로 이어 쓴다.
> 형식이 다른 스펙을 받았으면 **색·타이포·radii·spacing 네 범주로 정규화**해 위에 채운다.

> **출처가 `AI 초안`이면** 사람이 값을 보고 확인해야 `확정`이 된다. 확정 전에는 코드에 적용하지 않는다.
> 확정된 뒤에는 출처가 무엇이든 **똑같이 다룬다** — 임의로 값을 바꾸지 않는다.

## 적용 범위

| Tier | 무엇 | 하는가 |
|:--|:--|:--|
| 1. 토큰 | 색·타이포·radii·spacing | ✅ 전면 |
| 2. 컴포넌트 | button·card·input·nav 룩 | 🟡 프로젝트에 있는 것만 |
| 3. 구조 | 레이아웃·화면 배치 | ❌ 안 함 — 아래 원칙에 기록만 |

## 대상

| 항목 | 값 |
|:--|:--|
| 프론트 경로 | {{frontend/}} |
| 스택 | {{Next.js + MUI · Tailwind · CSS 변수}} |
| 토큰 산출 파일 | {{frontend/theme.ts}} |

## 매핑 기록

스펙 컴포넌트가 **실제 어느 파일에 붙었나**. 다음 적용 때 이 표로 추적한다.

| 스펙 컴포넌트 | 실제 파일 | 상태 |
|:--|:--|:--|
| {{button-primary}} | {{src/components/Button.tsx}} | {{적용}} |
| {{nav}} | — | {{건너뜀 — 프로젝트에 없음}} |

## 원칙 (참고만 — 자동 적용하지 않음)

스펙의 Do/Don't·레이아웃 철학. **여기 적힌 걸 코드에 반영하지 않는다** — Tier3다.

- {{여백을 넉넉히 · 강조색은 화면당 한 곳}}

## 빠진 값

스펙에 없어서 기본값으로 둔 것. 지어내지 않는다.

- {{danger 색 — 스펙에 없음, 기존 값 유지}}

## 폰트

- 독점 폰트({{SF Pro}})는 **embed하지 않는다** — 대체 폰트({{Inter}}) + letter-spacing 미세조정.

## History

- {{YYYYMMDD}} {{변경 내용 / 사유}}
