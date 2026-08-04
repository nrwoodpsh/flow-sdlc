/**
 * API 계약 템플릿 (TypeScript 스택 기준)
 *
 * 범위: 내부 전용 | 서비스 간 | 외부 제공        ← 반드시 적는다 (없으면 `내부 전용`으로 본다)
 *   내부 전용   이 배포 단위 안에서만        → 깨는 변경 자유
 *   서비스 간   우리 다른 서비스가 호출       → 호출 서비스를 찾아 함께 고친다
 *   외부 제공   다른 조직·팀이 호출          → 깨는 변경 불가. 경로에 버전 · 폐기 예고 필수
 *                                            바꾸면 사람이 상대에게 알린다 (게이트가 못 잡는다)
 * ─────────────────────────────────────────────
 * 이 파일은 "프로젝트 확정층" 정본이다. 실제 도메인에 맞게 이름을 치환해 사용.
 * 계약은 자연어가 아니라 타입으로 작성한다 — 컴파일러가 환각·오타를 잡는다.
 * 검증: workflow.config.json의 contract.gate (기본 `tsc --noEmit --strict`).
 *
 * TS를 쓰지 않는 스택은 이 파일을 그 스택의 골격으로 바꿔 쓴다 — /flow:setup 이 조정한다.
 * (예: Java record + Bean Validation, Python Pydantic, OpenAPI yaml)
 * 확장자와 검증 명령은 workflow.config.json 의 contract.pathGlob·contract.gate 로 맞춘다
 * (스택별 조합은 contract-gate 스킬의 표).
 *
 * ─────────────────────────────────────────────
 * 계약이 답해야 할 것 (필드명만 나열하면 FE/BE가 다르게 해석한다 — 빠지기 쉬운 것):
 *   1) 검증 규칙 — 필드별 필수/선택·최대 길이·허용값 (타입 또는 주석으로 명시)
 *   2) 에러 — 권한 없음 403 vs 대상 없음 404 등. 코드·status·message를 에러 레지스트리에
 *   3) 페이징·정렬 — page가 0-based? 1-based? 정렬 가능한 필드는?
 *   4) FE 상태 — 로딩·빈 목록·에러에 각각 어떤 응답을 주는지 (화면에 무엇을 보여줄지는
 *      1.design.md 의 `화면 구조`가 갖는다 — 여기엔 응답 형태만)
 */

// 1) 엔드포인트 — method + path를 상수로 고정
export const ExampleEndpoint = {
  method: 'GET',
  path: '/api/v1/examples',
} as const;

// 2) 요청 DTO
export interface ExampleReq {
  page: number;
  size: number;
  keyword?: string;
}

// 3) 응답 DTO
export interface ExampleItem {
  id: number;
  name: string;
  createdAt: string; // ISO 8601
}

export interface ExampleRes {
  items: ExampleItem[];
  total: number;
  page: number;
}

// 4) 에러 레지스트리 — code + HTTP status + message
export const ExampleErrors = {
  NOT_FOUND: { code: 'EX001', status: 404, message: '대상을 찾을 수 없습니다.' },
  INVALID_PARAM: { code: 'EX002', status: 400, message: '요청 파라미터가 유효하지 않습니다.' },
} as const;

export type ExampleErrorCode = (typeof ExampleErrors)[keyof typeof ExampleErrors]['code'];
