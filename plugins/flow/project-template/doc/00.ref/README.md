# 00.ref — 기반 지식 색인

프로젝트 확정 지식의 정본. 범주별로 나뉜다. 하위 폴더엔 README를 두지 않고 **여기서 색인**한다.

**폴더마다 고치는 주체가 다르다** — `00.architecture`·`01.domain`은 `/flow:prd`·`/flow:design`이, `02.db-schema`는 마이그레이션과 같은 커밋에 사람이, `03.templates`는 `/flow:setup`이 동기화한다. 손으로 직접 고치는 것은 규약 위반이다.

| 폴더 | 범주 | 무엇을 담나 | 현재 파일 |
|:--|:--|:--|:--|
| `00.architecture` | **시스템 레벨** 요구 + 기술 구조 + **크로스 도메인 업무 흐름** | `00.requirement.md`(`SYS-*`, `/flow:prd sys`) · `01.design.md`(구성·의존 방향·업무 흐름·크로스커팅 규칙, `/flow:design sys`) — 템플릿 `13.architecture` | _(비어 있음 — 채우기)_ |
| `01.domain` | **도메인 레벨** 요구 + 경계·용어 | `00.common.md`(공통 용어집) · `NN.{도메인}.md`(§요구 `{도메인}-*` · §경계·용어) | [00.common.md](01.domain/00.common.md) |
| `02.db-schema` | 데이터 저장소 스키마 (관계형·그래프·문서·검색) | 저장소가 하나면 파일만, 여럿이면 `{저장소}/` 폴더로 나눈다 (**번호 없음**) | _(없음)_ |
| `03.templates` | 산출물별 표준 템플릿 | 유닛 사슬 `00.requirement`~`07.summary` · 그 밖 `08.adr`·`09.domain`·`10.explainer`·`11.postmortem`·`12.sop-runbook`·`13.architecture`·`14.integration`·`15.theme` | [03.templates/](03.templates/) — **`doc-verify`의 채점 기준** |
| `04.theme` | **테마 스펙 정본** | 테마 적용(`theme-apply`) 입력 (토큰·컴포넌트) | 없으면 빈 폴더 |
| `05.explainer` | 신규 인력용 설명 노트 | `NN.{주제}.md` (템플릿 `10.explainer`) | 없으면 빈 폴더 |

> **템플릿이 복사된 시점은 `workflow.config.json` 의 `templates` 절에 있다** — `flowVersion`·`copiedAt`·`localEdits`. `/flow:setup` 업데이트 모드가 `flowVersion` 을 플러그인 버전과 비교해 **바뀐 템플릿을 파일별로 제시**한다. **손으로 고치지 않는다** — 고치면 동기화 판정이 틀어진다. 일부러 고친 템플릿을 `localEdits` 에 적으면 업데이트에서 건너뛴다.
> 앞선 판은 이 값을 `03.templates/VERSION` 이라는 자체 형식 파일에 뒀다. JSON 파서가 이미 있는데 정규식으로 읽을 형식을 하나 더 둘 이유가 없다.

**`02.db-schema` 파일 나누기** — 관계형만 있는 게 아니다. **엔진이 그대로 실행할 수 있는 형식**으로, 그 저장소에서 자연스러운 단위로 쪼갠다.

| 저장소 | 단위 | 예 |
|:--|:--|:--|
| 관계형 (Postgres·MySQL) | **테이블당 한 파일** | `user.sql` · `reset_token.sql` |
| 그래프 (Neo4j) | **한 파일에 모아서** — 노드·관계·제약은 따로 보면 뜻이 안 통한다 | `graph.cypher` |
| 문서 (MongoDB) | 컬렉션당 | `report.json`(스키마) |
| 검색 (Elasticsearch) | 인덱스당 | `article.mapping.json` |

- **저장소가 여럿이면 폴더로 나눈다** — `02.db-schema/postgres/` · `02.db-schema/neo4j/`. MSA에서 서비스마다 DB가 다르면 서비스명으로: `02.db-schema/collect-svc/`.

**마이그레이션은 여기 두지 않는다.** 둘의 성격이 다르다.

| | 무엇 | 어디 |
|:--|:--|:--|
| **스키마 정본** | **지금 상태** — `CREATE TABLE`·인덱스·제약 | **`02.db-schema/`** (여기) |
| **마이그레이션** | **변경 스크립트** — `ALTER TABLE …`·순서·되돌리기 | **소스 트리** — 프로젝트 관례를 따른다 |

- 마이그레이션은 **실행되는 코드**다. Flyway `db/migration/`·Prisma `prisma/migrations/`·Alembic `alembic/versions/` 등 **그 도구가 정한 자리**에 둔다.
- **마이그레이션을 만들면 `02.db-schema/`의 정본도 같은 커밋에 갱신한다.** 안 하면 정본이 낡아 AI가 없는 컬럼을 믿는다.
- **개발 DB에서 실제로 돌려 검증한다**(`CLAUDE.md`의 `가드레일`). 운영 적용은 사람이 배포 시스템으로.
- 되돌리는 방법·되돌릴 수 없는 것은 그 유닛의 `1.design.md` `배포·롤백·마이그레이션` 절에 적는다.
- 무엇이 어디 있는지는 **이 README 표에 링크 한 줄**로 남긴다.

**절마다 등급이 붙어 있다** — `doc-verify`가 이걸로 판정 강도를 정한다.

| 등급 | 뜻 | 안 채우면 |
|:--|:--|:--|
| **`[진행 필수]`** | 다음 커맨드가 이 내용을 소비한다 | FAIL · `gatekeeper` 가 **차단** |
| **`[문서 필수]`** | 업계 표준이 요구한다(DDD·arc42·ISO 42010·UML·ISO 29119) | FAIL · **차단은 안 함** |
| 표기 없음 | 선택 | 표시만 |

- **프로젝트가 절을 더해도 된다.** 규제 근거·정산 대조처럼 그 프로젝트만의 것은 표기 없이 넣으면 채점 대상이 아니다.

> **템플릿을 고치면 그게 기준이 된다.** `doc-verify`는 플러그인 원본이 아니라 **여기 있는 것**과 대조한다 — 프로젝트에 맞게 칸을 빼거나 더해도 된다.

- **파일 추가 시 이 표에 링크 한 줄** 추가. 범주 폴더(`00.architecture`·`02.db-schema` 등)는 셋업 때 만들어지고, 파일은 `/flow:prd`·`/flow:design`(시스템·도메인 레벨)이 초안을 쓰고 **사람이 확정**한다.
- 도메인 파일은 그 도메인의 **단일 뷰** — 요구·경계·용어에 더해 하위 기능 목록을 `/flow:sync`가 색인한다.
- 상시 참조는 **인덱스만** — 큰 본문은 `@`·`explorer`로 선택 로드.
- 전체 doc 구조·규칙은 상위 [`doc/README.md`](../README.md).
