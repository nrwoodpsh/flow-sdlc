# {{프로젝트명}}

{{한 줄 소개}} · 스택: {{예: Spring Boot 3 + Vue 3 + TS}}

> 이 프로젝트는 **flow 워크플로우**로 개발한다.

## 구조 (프로젝트 루트)

```
{{프로젝트}}/
├── README.md              이 파일 (프로젝트 소개)
├── CLAUDE.md              AI 정체성·가드레일 (매턴 자동 로드 → 작게)
├── workflow.config.json   스택·계약 게이트·테스트·drift·review·템플릿 버전 설정
├── .gitignore · .claude/settings.json · .github/…
├── src/ · tests/scenarios/   실제 코드 · 테스트 코드
├── spike/                 버릴 검증 코드 (내용물 gitignore)
└── doc/                   설계·기록  →  구조·규칙은 doc/README.md
```

> **doc 폴더 전체 구조(최하단까지)와 규칙은 [`doc/README.md`](doc/README.md)** 에 있다. (여기 중복해 두지 않는다.)

## 개발 흐름 (flow)

```
/flow:setup      프로젝트에 flow 층을 심는다 (처음 한 번)
/flow:next       지금 무엇을 할 차례인지 답하고, 원하면 이어서 돌린다
/flow:prd        요구 발급 — 시스템·도메인 → ID 발급
/flow:design     설계 — 시스템·도메인에서 기능(task·계약)까지
/flow:build      구현 + 단위 검증 (루프 최대 3회)
/flow:verify     테스트 실행 (unit|branch|project) · 요구 커버리지 감사 (coverage)
/flow:review     리뷰 — 코드(층으로 쌓아 등급) 또는 문서(doc)
/flow:sync       코드↔문서 수렴 + 요약 + 색인
/flow:commit     커밋 (기본 브랜치면 새 브랜치 · push는 사람)
/flow:spike      버릴 코드로 가설 검증 → 남기는 것은 ADR·ref
/flow:publish    끝난 결과를 외부로 발행 (선택)
```

- 정석: `prd → design → build → verify → review → sync → commit`
- 어디서 시작할지 모르면 `/flow:next`
- 버그·작은 변경은 `/flow:design`부터(요구 자동 발급) · 시스템·도메인 레벨은 설계에서 정지(ref 착지)
- 프론트 테마 적용은 커맨드가 아니라 **`theme-apply` 스킬**이다 — 필요할 때 부른다

## 처음 왔으면

**[`doc/README.md`의 "처음 왔으면 이 순서로"](doc/README.md)** 를 따른다 — 용어 → 시스템 구조 → 결정 → 담당 도메인 순이다.

- doc 구조·규칙: [`doc/README.md`](doc/README.md)
- AI 가드레일·참조통제: [`CLAUDE.md`](CLAUDE.md)
