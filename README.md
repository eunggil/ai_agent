# AI Agent — 개인화 피드 생성형 SNS

> User-State Driven Media Generation Platform

사용자 상태를 실시간으로 추론하여 이미지·영상을 즉석에서 생성하고, 광고를 자연스럽게 녹여낸 SNS 피드를 만드는 AI 에이전트 플랫폼입니다.

---

## 핵심 차별점

```
기존 SNS:  콘텐츠 생성 → 사용자 매칭 → 피드 노출
우리 시스템: 사용자 상태 추론 → 전략 결정 → 콘텐츠 생성 → 광고 결합 → 피드 노출
```

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| API 서버 | Python 3.11, FastAPI, Uvicorn |
| AI / LLM | Vertex AI Gemini 2.0 Flash |
| 이미지 생성 | Vertex AI Imagen 4 (`imagen-4.0-fast-generate-001`) |
| 영상 생성 | Vertex AI Veo 3.1 (`veo-3.1-fast-generate-001`) |
| 에이전트 프레임워크 | LangGraph 6-노드 파이프라인 |
| 벡터 DB | PostgreSQL + pgvector |
| 캐시 | Redis |
| 스토리지 | Google Cloud Storage (이미지·영상 public URL) |
| 트레이싱 | Langfuse (셀프 호스팅) |
| 컨테이너 | Docker Compose |
| 배포 | Google Cloud Run (Cloud Build) |

---

## LangGraph 파이프라인 (6단계)

```
load_context → state_interpreter → retrieve_candidates
    → strategy_planner → creative_generator → media_generator
```

1. **load_context** — 사용자 프로필 + 벡터 로드 (DB)
2. **state_interpreter** — 의도·감정·니즈 분석 (LLM)
3. **retrieve_candidates** — 광고·상품·콘텐츠 후보 검색 (pgvector)
4. **strategy_planner** — 광고 선택 및 결합 전략 수립 (LLM)
5. **creative_generator** — SNS 텍스트 + 이미지 프롬프트 생성 (LLM)
6. **media_generator** — 이미지(Imagen 4) 또는 영상(Veo 3.1) 생성

---

## 사전 준비

### 1. GCP 서비스 계정 생성 및 권한 부여

```bash
# 서비스 계정 생성
gcloud iam service-accounts create ai-agent-sa \
  --display-name="AI Agent Service Account"

# 필요한 IAM 역할 부여
PROJECT_ID=your-gcp-project-id
SA_EMAIL=ai-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

# 키 파일 다운로드
gcloud iam service-accounts keys create ~/sa-key.json \
  --iam-account=$SA_EMAIL
```

### 2. GCS 버킷 생성 (이미지·영상 저장용)

> Imagen 4 / Veo 3.1은 **us-central1** 리전만 지원합니다.

```bash
BUCKET_NAME=your-media-bucket-name

# 버킷 생성
gsutil mb -l us-central1 gs://${BUCKET_NAME}

# public 읽기 권한 설정 (Uniform bucket-level access)
gsutil iam ch allUsers:objectViewer gs://${BUCKET_NAME}
```

---

## 빠른 시작 (Docker)

```bash
# 1. 저장소 클론
git clone https://github.com/eunggil/ai_agent.git
cd ai_agent

# 2. 환경 변수 설정
cp .env.example .env
# .env 편집: GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS, GCS_MEDIA_BUCKET 등
```

### 텍스트 전용 모드 (GCP 인증 없이 빠른 확인)

```bash
# .env에서 AI_PROVIDER=local, MEDIA_PROVIDER=none 설정 후

# 최초 실행 시 이미지 빌드
docker-compose build

# 컨테이너 시작
docker-compose up -d

# 첫 실행 시 자동 처리:
#   - PostgreSQL 테이블 생성 + pgvector 확장
#   - 데모 데이터 자동 시드 (사용자 15명, 상품·광고·콘텐츠 각 100개)
docker-compose logs -f ai-agent
```

### 이미지 생성 모드 (Vertex AI Imagen 4)

```bash
# .env 설정
# AI_PROVIDER=vertex
# MEDIA_PROVIDER=vertex_imagen
# GCS_MEDIA_BUCKET=your-media-bucket-name
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json

docker-compose build
docker-compose up -d
```

### 영상 생성 모드 (Vertex AI Veo 3.1)

```bash
# .env 추가 설정
# VERTEX_VEO_GCS_BUCKET=your-media-bucket-name

# media_type=video 로 요청 시 자동으로 Veo 사용
```

---

## API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 사용자 정보 조회
curl http://localhost:8000/v1/user/user_001

# AI 피드 생성 — 텍스트
curl -X POST http://localhost:8000/v1/ai/generate-feed \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "prompt": "오늘 기분 좋은 패션 아이템 추천해줘", "media_type": "text"}'

# AI 피드 생성 — 이미지
curl -X POST http://localhost:8000/v1/ai/generate-feed \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "prompt": "봄 신상 뷰티 제품 추천", "media_type": "image"}'

# AI 피드 생성 — 영상 (Veo, 약 60~90초 소요)
curl -X POST http://localhost:8000/v1/ai/generate-feed \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_003", "prompt": "스포츠 용품 광고", "media_type": "video"}'
```

---

## Langfuse 트레이싱 (선택)

LangGraph 파이프라인의 전체 실행 흐름, LLM 호출, 토큰 수를 대시보드에서 확인할 수 있습니다.

```bash
# Langfuse 서비스 추가 실행
docker-compose --profile langfuse up -d

# 대시보드: http://localhost:3000
# 로그인:   admin@local.dev / admin1234
```

> `.env`의 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`는 기본값(`pk-lf-local` / `sk-lf-local`)으로
> Langfuse 초기화 시 자동 생성됩니다. 별도 발급 불필요.

---

## 환경 변수 주요 항목

| 변수 | 설명 | 기본값 |
|---|---|---|
| `GCP_PROJECT_ID` | GCP 프로젝트 ID | — |
| `GCP_REGION` | Cloud Run 배포 리전 | `asia-northeast3` |
| `GOOGLE_APPLICATION_CREDENTIALS` | SA 키 파일 절대경로 | — |
| `AI_PROVIDER` | LLM 프로바이더 (`vertex` \| `local`) | `vertex` |
| `VERTEX_AI_LOCATION` | Gemini 엔드포인트 리전 | `us-central1` |
| `VERTEX_AI_MEDIA_LOCATION` | Imagen/Veo 리전 (us-central1 고정) | `us-central1` |
| `MEDIA_PROVIDER` | 미디어 프로바이더 (`none` \| `vertex_imagen`) | `none` |
| `MEDIA_TYPE` | 기본 미디어 타입 (`text` \| `image` \| `video`) | `image` |
| `GCS_MEDIA_BUCKET` | 이미지·영상 저장 GCS 버킷 | — |
| `VERTEX_VEO_GCS_BUCKET` | Veo 출력 버킷 (영상 생성 시 필수) | — |
| `LANGFUSE_PUBLIC_KEY` | Langfuse 프로젝트 공개 키 | `pk-lf-local` |
| `LANGFUSE_SECRET_KEY` | Langfuse 프로젝트 비밀 키 | `sk-lf-local` |

전체 항목은 `.env.example` 참조.

---

## 프로젝트 구조

```
ai_agent/
├── src/
│   ├── api/                  # FastAPI 엔드포인트 (main.py)
│   └── core/
│       └── ai_agent/
│           ├── agent.py      # LangGraph 6-노드 파이프라인
│           ├── state.py      # 에이전트 상태 스키마
│           ├── db_data.py    # DB 조회 (pgvector)
│           ├── providers/    # LLM 프로바이더 (Vertex AI, Ollama)
│           └── media_providers/  # 미디어 생성 (Imagen, Veo, Replicate)
├── scripts/
│   ├── init_db.sql           # PostgreSQL 초기화
│   ├── seed_demo_data.py     # 데모 데이터 시드
│   └── entrypoint.sh         # 컨테이너 시작 스크립트 (자동 시드)
├── docs/                     # 상세 문서
├── docker-compose.yml
├── Dockerfile.dev
├── requirements.txt
└── .env.example
```

---

## 문서

- [시스템 아키텍처](docs/ARCHITECTURE.md)
- [AI Agent 설계](docs/AGENT_DESIGN.md)
- [API 명세](docs/API_SPEC.md)
- [데이터 스키마](docs/DATA_SCHEMA.md)
- [Docker & 배포](docs/DOCKER_DEPLOYMENT.md)

---

## 라이선스

MIT License
