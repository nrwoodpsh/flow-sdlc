# {{프로젝트명}}

{{한 줄 소개}} · 스택: {{예: Spring Boot 3 + Vue 3 + TS}}

> 이 프로젝트는 **flow 워크플로우**로 개발한다.

## 구조 (프로젝트 루트)

```
{{프로젝트}}/
├── README.md              이 파일 (프로젝트 소개)
├── CLAUDE.md              AI 정체성·가드레일 (매턴 자동 로드 → 작게)
├── workflow.config.json   스택·계약 게이트·테스트·drift·review 설정
├── .gitignore · .claude/settings.json · .github/…
├── src/ · tests/scenarios/   실제 코드 · 테스트 코드
├── spike/                 버릴 검증 코드 (내용물 gitignore)
└── doc/                   설계·기록  →  구조·규칙은 doc/README.md
```

> **doc 폴더 전체 구조(최하단까지)와 규칙은 [`doc/README.md`](doc/README.md)** 에 있다. (여기 중복해 두지 않는다.)

## 개발 흐름 (flow)

```
/flow:ask        무엇부터 할지 모르겠으면 — 문장으로 쓰면 알맞은 커맨드로 보낸다
/flow:theme      프론트 테마 적용 (FE 프로젝트만 · setup 이후 1회)
/flow:prd        요구 정의 (sys|domain|func · legacy) → 0.requirement (ID 발급)
/flow:spike      버릴 코드로 가설 검증 → ADR·ref 승격
/flow:design     분석 → 설계도 (단일 정문) → 1.design
/flow:spec       task 분할 + 계약 → 2.task·3.contract
/flow:build      구현 ⇄ 테스트 루프 (최대 3회)
/flow:verify     테스트 실행 (unit|branch|project — project는 전체 통합테스트)
/flow:review     OCR+CPG 코드리뷰 (critical 차단)
/flow:sync       코드↔문서 동기화 + summary + README 색인
/flow:commit     커밋 (main이면 새 브랜치 · push는 사람)
/flow:run        위를 자동 연결 (full|fix|design|build · 커밋 직전 정지)
/flow:publish    끝난 결과를 Notion 등으로 발행 (선택)
```

- 정석: `prd → design → spec → build → verify → review → sync → commit`
- 버그는 `/flow:design`부터(요구 자동 발급) · 시스템·도메인 레벨은 `/flow:design`에서 정지(ref 착지)

## 처음 왔으면

**[`doc/README.md`의 "처음 왔으면 이 순서로"](doc/README.md)** 를 따른다 — 용어 → 시스템 구조 → 결정 → 담당 도메인 순이다.

- doc 구조·규칙: [`doc/README.md`](doc/README.md)
- AI 가드레일·참조통제: [`CLAUDE.md`](CLAUDE.md)
