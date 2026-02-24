# 문서 인덱스

AI Agent 프로젝트의 전체 문서 구조와 읽는 순서를 안내합니다.

---

## 📚 문서 읽는 순서

### 1단계: 개요 파악 (30분)

**시작점:**
- [README.md](../README.md) - 프로젝트 개요 및 빠른 시작

**목적:** 프로젝트가 무엇을 하는지, 왜 만드는지 이해

---

### 2단계: 전체 아키텍처 (1시간)

**핵심 문서:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 전체 아키텍처

**내용:**
- User-State Driven Platform 철학
- 전체 시스템 구성도
- 데이터 레이어 (BigQuery, Pub/Sub, Firestore, Vector DB)
- 피드 생성 파이프라인
- 확장 전략

**목적:** 시스템 전체를 조감하고 각 컴포넌트의 역할 이해

---

### 3단계: AI Agent 상세 (2시간)

**필독 문서:**
- [AGENT_DESIGN.md](AGENT_DESIGN.md) - AI Agent 상세 설계

**내용:**
- 에이전트 개발 트렌드 (LangGraph, Agent Ops, Tool Governance)
- 광고결합 콘텐츠 생성 에이전트 9단계 파이프라인
- LangGraph 기반 노드/상태/엣지 설계
- 하이브리드 검색 (Vector + Graph)
- 광고 랭킹 4단계 프로세스
- 브랜드 안전 장치 3중 방어
- Vertex AI 활용 전략

**목적:** 에이전트 구현 방법과 핵심 로직 이해

---

### 4단계: PiMS와 온톨로지 (1.5시간)

**필독 문서:**
- [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) - 상품 정보 관리 및 온톨로지

**내용:**
- 온톨로지가 왜 필요한가
- PiMS 아키텍처 (운영 스키마 vs AI 스키마)
- 패션/주얼리/코스메틱 온톨로지 v0
- 그래프 DB 설계 (노드/엣지/Cypher 쿼리)
- LLM 자동화 파이프라인 (추출→정규화→검증→토큰 생성)
- VTO (Virtual Try-On) 설계

**목적:** 상품 데이터를 AI가 이해하는 형태로 변환하는 방법 이해

---

### 5단계: 데이터 스키마 (1시간)

**참조 문서:**
- [DATA_SCHEMA.md](DATA_SCHEMA.md) - 데이터베이스 스키마 상세

**내용:**
- BigQuery 테이블 (행동 로그, AI 생성 로그, 광고 로그)
- Vector DB 스키마 (PostgreSQL + pgvector)
- Firestore 컬렉션 구조
- Pub/Sub 메시지 스키마
- 데이터 파이프라인

**목적:** 실제 데이터 저장 구조 이해

---

### 6단계: API 명세 (30분)

**참조 문서:**
- [API_SPEC.md](API_SPEC.md) - REST API 명세

**내용:**
- 인증
- 피드 API (기본/AI)
- AI 생성 API
- 사용자 API
- 광고 API (내부)
- 에러 코드

**목적:** 클라이언트-서버 통신 이해

---

### 7단계: 구현 가이드 (1시간)

**개발자 필독:**
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - 구현 가이드

**내용:**
- 개발 환경 설정
- 프로젝트 구조
- 핵심 컴포넌트 구현 예시 (Python 코드)
- Terraform 배포
- 모니터링 및 운영

**목적:** 실제 개발 시작하기

---

## 📖 역할별 추천 읽기 순서

### PM/기획자

```
README → ARCHITECTURE → AGENT_DESIGN → PIMS_ONTOLOGY
```

**이유:**
- 시스템 전체 흐름 이해
- 에이전트 로직과 의사결정 이해
- 상품/브랜드 정책 관리 이해

**시간:** 약 5시간

---

### Backend 개발자

```
README → ARCHITECTURE → DATA_SCHEMA → AGENT_DESIGN → IMPLEMENTATION_GUIDE
```

**이유:**
- 데이터 구조부터 파악
- 에이전트 구현 로직 이해
- 실제 코드 작성 준비

**시간:** 약 5.5시간

---

### AI/ML 엔지니어

```
README → ARCHITECTURE → AGENT_DESIGN → PIMS_ONTOLOGY → IMPLEMENTATION_GUIDE
```

**이유:**
- 에이전트 설계에 집중
- 온톨로지/벡터/그래프 이해
- LLM 활용 방법 학습

**시간:** 약 6시간

---

### Frontend 개발자

```
README → ARCHITECTURE → API_SPEC → IMPLEMENTATION_GUIDE
```

**이유:**
- 전체 시스템 개요 파악
- API 통신 방법 이해
- 클라이언트 연동 준비

**시간:** 약 3시간

---

### DevOps 엔지니어

```
README → ARCHITECTURE → DATA_SCHEMA → IMPLEMENTATION_GUIDE
```

**이유:**
- 인프라 구성 이해
- 데이터베이스/메시징 설정
- 배포 및 모니터링 준비

**시간:** 약 3.5시간

---

## 🔍 주제별 문서 찾기

### 에이전트 관련

| 주제 | 문서 | 섹션 |
|------|------|------|
| 에이전트 트렌드 | [AGENT_DESIGN.md](AGENT_DESIGN.md) | 1. 에이전트 개발 트렌드 |
| LangGraph 설계 | [AGENT_DESIGN.md](AGENT_DESIGN.md) | 3. 에이전트 그래프 설계 |
| 하이브리드 검색 | [AGENT_DESIGN.md](AGENT_DESIGN.md) | 4. 하이브리드 검색 전략 |
| 광고 랭킹 | [AGENT_DESIGN.md](AGENT_DESIGN.md) | 5. 광고 랭킹 시스템 |
| 브랜드 안전 | [AGENT_DESIGN.md](AGENT_DESIGN.md) | 6. 브랜드 안전 장치 |

### 데이터 관련

| 주제 | 문서 | 섹션 |
|------|------|------|
| 데이터 레이어 | [ARCHITECTURE.md](ARCHITECTURE.md) | 3. 데이터 레이어 설계 |
| BigQuery 스키마 | [DATA_SCHEMA.md](DATA_SCHEMA.md) | 1. BigQuery 스키마 |
| Vector DB | [DATA_SCHEMA.md](DATA_SCHEMA.md) | 2. Vector DB 스키마 |
| Firestore | [DATA_SCHEMA.md](DATA_SCHEMA.md) | 3. Firestore 스키마 |
| Pub/Sub | [DATA_SCHEMA.md](DATA_SCHEMA.md) | 4. Pub/Sub 메시지 스키마 |

### 온톨로지 관련

| 주제 | 문서 | 섹션 |
|------|------|------|
| 온톨로지 개념 | [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) | 1. 온톨로지 개요 |
| PiMS 아키텍처 | [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) | 2. PiMS 아키텍처 |
| 카테고리 온톨로지 | [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) | 3. 패션/주얼리/코스메틱 온톨로지 |
| 그래프 DB | [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) | 4. 그래프 DB 설계 |
| LLM 자동화 | [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) | 5. LLM 자동화 파이프라인 |
| VTO | [PIMS_ONTOLOGY.md](PIMS_ONTOLOGY.md) | 6. VTO 설계 |

### API 관련

| 주제 | 문서 | 섹션 |
|------|------|------|
| 피드 API | [API_SPEC.md](API_SPEC.md) | 2. 피드 API |
| AI 생성 API | [API_SPEC.md](API_SPEC.md) | 3. AI 생성 API |
| 사용자 API | [API_SPEC.md](API_SPEC.md) | 4. 사용자 API |
| 에러 코드 | [API_SPEC.md](API_SPEC.md) | 6. 에러 코드 |

### 구현 관련

| 주제 | 문서 | 섹션 |
|------|------|------|
| 빠른 시작 (Mock) | [QUICK_START_MOCK.md](QUICK_START_MOCK.md) | Mock 데이터로 즉시 개발 |
| Docker 로컬 개발 | [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) | 1. 로컬 개발 환경 (Docker) |
| Cloud Build 배포 | [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) | 2. 프로덕션 배포 |
| 개발 환경 | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | 1. 개발 환경 설정 |
| 프로젝트 구조 | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | 2. 프로젝트 구조 |
| 핵심 구현 | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | 3. 핵심 컴포넌트 구현 |
| 배포 | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | 4. 배포 가이드 |
| 모니터링 | [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) | 5. 모니터링 및 운영 |

---

## 📝 문서 업데이트 이력

| 날짜 | 문서 | 변경 내용 |
|------|------|----------|
| 2026-02-24 | 전체 | 초기 문서 세트 작성 |
| 2026-02-24 | AGENT_DESIGN.md | LangGraph 기반 에이전트 설계 추가 |
| 2026-02-24 | PIMS_ONTOLOGY.md | 온톨로지 및 그래프 DB 설계 추가 |

---

## 🤝 문서 기여 가이드

### 문서 수정 시 체크리스트

- [ ] 다른 문서와의 링크 확인
- [ ] 코드 예시 실행 가능 여부 확인
- [ ] 다이어그램 최신 상태 유지
- [ ] 버전 정보 업데이트
- [ ] INDEX.md 업데이트

### 문서 작성 원칙

1. **명확성**: 전문 용어는 처음 사용 시 설명
2. **실용성**: 코드 예시 포함
3. **최신성**: 변경사항 즉시 반영
4. **일관성**: 용어/스타일 통일

---

## 💬 질문 및 피드백

문서에 대한 질문이나 개선 제안은:
- GitHub Issues
- Slack #ai-agent 채널
- 담당자: AI Agent Team

---

**마지막 업데이트:** 2026-02-24
