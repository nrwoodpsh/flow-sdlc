---
paths:
  - "scripts/**"
  - "plugins/flow/hooks/**"
  - "plugins/flow/git-hooks/**"
  - "plugins/flow/guard-rules.json"
---

# 훅·검사기를 만질 때

**이 경로의 파일을 읽을 때만 실린다.** 매 턴 필요한 규칙이 아니라서 `CLAUDE.md`가 아니라 여기 있다.

## 되돌려서 실패하는지도 확인한다

통과 숫자만 보면 사문화된 검사와 지키는 검사가 구별되지 않는다.

- `guard-rules.json`에서 규칙 하나를 지우면 그 케이스가 **실패해야** 한다.
- `lint.py`에 검사를 더하면 `lint.test.py`에 **위반 픽스처**도 넣어야 한다. 안 넣으면 테스트가 실패한다.
- 검사기 고장과 문서 위반은 exit code로 갈린다 (`3` 고장 · `1` 위반).

## 재작성 금지

전체 표는 `doc/01.architecture.md`의 `재작성 금지` 절이 정본 — 여기는 이 경로에서 만지는 것만.

| 무엇 | 왜 |
|:--|:--|
| `guard-danger.sh`의 인용·here-doc 토크나이저 | `"it\'s a fix"`가 가드를 통째로 껐던 사고가 케이스로 박혀 있다 |
| `drift-hook.sh`의 `set -f` | 글로브가 디스크 파일로 확장돼 하위 파일을 놓친 사고 |
| "유닛 없으면 검사를 안 켠다" | 레거시 도입 첫날 전 커밋이 막힌다 |
| `bump-version.sh`의 이중 대조 | 두 매니페스트가 어긋나면 업데이트가 전달되지 않는다 |
