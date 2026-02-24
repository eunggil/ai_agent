# Docker 개발 & Cloud Build 배포 가이드

AI Agent 프로젝트의 Docker 기반 로컬 개발 환경 설정 및 Cloud Build를 통한 프로덕션 배포 가이드입니다.

---

## 목차

1. [로컬 개발 환경 (Docker)](#1-로컬-개발-환경-docker)
2. [프로덕션 배포 (Cloud Build)](#2-프로덕션-배포-cloud-build)
3. [트러블슈팅](#3-트러블슈팅)

---

## 1. 로컬 개발 환경 (Docker)

### 1.1 사전 요구사항

```bash
# Docker & Docker Compose 설치 확인
docker --version         # Docker version 20.10+
docker-compose --version # Docker Compose version 2.0+

# gcloud CLI 설치 확인 (Vertex AI 사용 시)
gcloud --version
```

### 1.2 빠른 시작 (Mock 데이터 사용)

**Step 1: 환경 변수 설정**

```bash
# .env 파일 생성
cp .env.docker .env

# .env 파일 편집
nano .env
```

`.env` 파일 예시:
```bash
# GCP 설정
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# Mock DB 사용 (AI Agent 개발에 집중)
USE_MOCK_VECTOR_DB=true
USE_MOCK_GRAPH_DB=true

# Vertex AI 인증
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json
```

**Step 2: Vertex AI 인증**

```bash
# Google Cloud 로그인 및 인증
gcloud auth login
gcloud auth application-default login

# 프로젝트 설정
gcloud config set project your-gcp-project-id
```

**Step 3: Docker Compose로 시작**

```bash
# 서비스 빌드 및 시작
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f ai-agent
```

**Step 4: API 테스트**

```bash
# 헬스 체크
curl http://localhost:8000/health

# 기본 피드 조회
curl "http://localhost:8000/v1/feed?user_id=user_001"

# AI 피드 생성
curl -X POST http://localhost:8000/v1/ai/generate-feed \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "prompt": "오늘 기분 좋은 패션 아이템 추천해줘"
  }'
```

### 1.3 실제 DB 사용 (PostgreSQL + pgvector)

Mock에서 실제 DB로 전환하려면:

**Step 1: 환경 변수 수정**

```bash
# .env 파일 수정
USE_MOCK_VECTOR_DB=false
USE_MOCK_GRAPH_DB=false
```

**Step 2: Docker Compose 재시작**

```bash
docker-compose down
docker-compose up -d
```

**Step 3: DB 연결 확인**

```bash
# PostgreSQL 접속
docker exec -it ai-agent-postgres psql -U postgres -d ai_agent

# 테이블 확인
\dt

# Vector 확장 확인
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Step 4: pgAdmin으로 관리 (선택사항)**

```bash
# pgAdmin 시작
docker-compose --profile tools up -d pgadmin

# 브라우저에서 접속
open http://localhost:5050

# 로그인
# Email: admin@example.com
# Password: admin

# PostgreSQL 서버 추가
# Host: postgres
# Port: 5432
# Username: postgres
# Password: postgres (from .env)
```

### 1.4 Docker 구조

```
┌─────────────────────────────────────────────┐
│         Docker Compose Network              │
│                                             │
│  ┌──────────────┐                          │
│  │  ai-agent    │ :8000                    │
│  │  (FastAPI)   │                          │
│  └──────┬───────┘                          │
│         │                                   │
│    ┌────┴────┬──────────┐                 │
│    │         │          │                  │
│  ┌─▼────┐  ┌─▼─────┐  ┌─▼──────┐         │
│  │Postgres│ │ Redis │ │pgAdmin │         │
│  │:5432   │ │ :6379 │ │ :5050  │         │
│  └────────┘ └───────┘ └────────┘         │
└─────────────────────────────────────────────┘
```

### 1.5 개발 워크플로우

**코드 변경 시 (Hot Reload)**

```bash
# src/ 디렉토리가 볼륨 마운트되어 있어 자동 재시작됨
# 파일 저장만 하면 됨
```

**의존성 추가 시**

```bash
# requirements.txt 수정 후
docker-compose build ai-agent
docker-compose up -d ai-agent
```

**새로운 마이그레이션 실행**

```bash
# PostgreSQL 컨테이너에서 SQL 실행
docker exec -i ai-agent-postgres psql -U postgres -d ai_agent < scripts/migration_001.sql
```

**테스트 실행**

```bash
# 컨테이너 내부에서 pytest 실행
docker-compose exec ai-agent pytest tests/

# 커버리지 포함
docker-compose exec ai-agent pytest --cov=src tests/
```

**로그 확인**

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스만
docker-compose logs -f ai-agent

# 최근 100줄만
docker-compose logs --tail=100 ai-agent
```

### 1.6 유용한 명령어

```bash
# 전체 서비스 중지
docker-compose down

# 볼륨까지 삭제 (DB 데이터 초기화)
docker-compose down -v

# 특정 서비스만 재시작
docker-compose restart ai-agent

# 컨테이너 셸 접속
docker-compose exec ai-agent bash

# Python 인터프리터 접속
docker-compose exec ai-agent ipython

# 리소스 사용량 확인
docker stats
```

---

## 2. 프로덕션 배포 (Cloud Build)

### 2.1 사전 준비

**Step 1: GCP 프로젝트 설정**

```bash
# 프로젝트 ID 설정
export PROJECT_ID=your-gcp-project-id

# 프로젝트 활성화
gcloud config set project $PROJECT_ID

# 필요한 API 활성화
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

**Step 2: Artifact Registry 생성**

```bash
# Docker 저장소 생성
gcloud artifacts repositories create ai-agent \
  --repository-format=docker \
  --location=us-central1 \
  --description="AI Agent Docker images"

# 인증 설정
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Step 3: Secret Manager에 인증 키 저장**

```bash
# Vertex AI 서비스 계정 키 생성
gcloud iam service-accounts create vertex-ai-agent \
  --display-name="Vertex AI Agent"

# 필요한 권한 부여
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vertex-ai-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# 키 생성 및 다운로드
gcloud iam service-accounts keys create vertex-ai-key.json \
  --iam-account=vertex-ai-agent@$PROJECT_ID.iam.gserviceaccount.com

# Secret Manager에 저장
gcloud secrets create vertex-ai-key \
  --data-file=vertex-ai-key.json

# 안전하게 로컬 키 삭제
rm vertex-ai-key.json
```

### 2.2 Cloud Build 수동 배포

**Step 1: 로컬에서 빌드 테스트**

```bash
# 프로덕션 Dockerfile로 빌드
docker build -f Dockerfile -t ai-agent:test .

# 로컬 테스트
docker run -p 8000:8000 \
  -e GCP_PROJECT_ID=$PROJECT_ID \
  -e USE_MOCK_VECTOR_DB=true \
  ai-agent:test
```

**Step 2: Cloud Build로 빌드**

```bash
# Cloud Build 실행
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_ENVIRONMENT=production
```

**Step 3: 배포 확인**

```bash
# Cloud Run 서비스 확인
gcloud run services describe ai-agent-api \
  --region=us-central1

# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe ai-agent-api \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# 헬스 체크
curl $SERVICE_URL/health
```

### 2.3 자동 배포 (Git 트리거)

**Step 1: Cloud Build 트리거 생성**

```bash
# GitHub 연동 (웹 콘솔에서 먼저 연결 필요)
gcloud builds triggers create github \
  --repo-name=addeep-ai-agent \
  --repo-owner=your-github-org \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_ENVIRONMENT=production
```

또는 Cloud Console에서:
1. Cloud Build > 트리거 > 트리거 만들기
2. GitHub 저장소 연결
3. 브랜치: `main`
4. 구성: `cloudbuild.yaml`
5. 치환 변수 설정

**Step 2: 배포 테스트**

```bash
# main 브랜치에 푸시
git add .
git commit -m "Test Cloud Build deployment"
git push origin main

# Cloud Build 로그 확인
gcloud builds list --limit=1
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```

### 2.4 Staging 환경 배포

```bash
# Staging 환경 배포
gcloud builds submit \
  --config=cloudbuild-staging.yaml \
  --substitutions=_REGION=us-central1,_ENVIRONMENT=staging
```

### 2.5 배포 전략

**Blue-Green 배포**

```bash
# 1. 새 버전 배포 (트래픽 0%)
gcloud run deploy ai-agent-api-new \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/ai-agent/ai-agent-api:latest \
  --region=us-central1 \
  --no-traffic

# 2. 테스트
curl $(gcloud run services describe ai-agent-api-new --region=us-central1 --format='value(status.url)')/health

# 3. 트래픽 전환
gcloud run services update-traffic ai-agent-api \
  --to-revisions=ai-agent-api-new=100 \
  --region=us-central1
```

**Canary 배포**

```bash
# 신규 버전에 20% 트래픽
gcloud run services update-traffic ai-agent-api \
  --to-revisions=LATEST=20,ai-agent-api-old=80 \
  --region=us-central1

# 모니터링 후 100% 전환
gcloud run services update-traffic ai-agent-api \
  --to-revisions=LATEST=100 \
  --region=us-central1
```

### 2.6 롤백

```bash
# 이전 리비전으로 롤백
gcloud run services update-traffic ai-agent-api \
  --to-revisions=ai-agent-api-old=100 \
  --region=us-central1

# 또는 특정 리비전 지정
gcloud run deploy ai-agent-api \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/ai-agent/ai-agent-api:PREVIOUS_SHA \
  --region=us-central1
```

### 2.7 모니터링

**로그 확인**

```bash
# Cloud Run 로그
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-agent-api" \
  --limit=50 \
  --format=json

# 에러 로그만
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=50
```

**메트릭 확인**

```bash
# Cloud Console에서 확인
# Cloud Run > ai-agent-api > 측정항목

# 주요 메트릭:
# - 요청 수
# - 요청 지연 시간
# - 인스턴스 수
# - CPU/메모리 사용률
```

**알림 설정**

```bash
# 에러율 알림 (Cloud Console에서 설정 권장)
# Monitoring > Alerting > Create Policy
# - Metric: Cloud Run > Request count (filtered by response_code >= 500)
# - Threshold: > 5% of total requests
# - Notification: Email/Slack
```

---

## 3. 트러블슈팅

### 3.1 로컬 Docker 문제

**문제: "Cannot connect to Docker daemon"**

```bash
# Docker 서비스 시작
sudo systemctl start docker  # Linux
open -a Docker              # macOS

# 권한 확인
sudo usermod -aG docker $USER
```

**문제: "Port already in use"**

```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8000

# 프로세스 종료
kill -9 <PID>

# 또는 docker-compose.yml에서 포트 변경
ports:
  - "8080:8000"  # 호스트:컨테이너
```

**문제: "Volume mount denied"**

```bash
# macOS: Docker Desktop > Preferences > Resources > File Sharing
# 프로젝트 디렉토리 추가

# Linux: SELinux 확인
sudo setenforce 0  # 임시
```

**문제: "GOOGLE_APPLICATION_CREDENTIALS not found"**

```bash
# 인증 재설정
gcloud auth application-default login

# 경로 확인
ls -la ~/.config/gcloud/application_default_credentials.json

# .env 파일 경로 수정
GOOGLE_APPLICATION_CREDENTIALS=/Users/yourname/.config/gcloud/application_default_credentials.json
```

### 3.2 Cloud Build 문제

**문제: "Permission denied" 에러**

```bash
# Cloud Build 서비스 계정 권한 확인
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

**문제: "Image not found"**

```bash
# Artifact Registry 이미지 확인
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/$PROJECT_ID/ai-agent

# 직접 이미지 태그 확인
gcloud artifacts docker tags list \
  us-central1-docker.pkg.dev/$PROJECT_ID/ai-agent/ai-agent-api
```

**문제: "Build timeout"**

```bash
# cloudbuild.yaml의 timeout 증가
timeout: '2400s'  # 40분

# 또는 빌드 머신 스펙 증가
options:
  machineType: 'E2_HIGHCPU_8'
```

### 3.3 Cloud Run 문제

**문제: "Container failed to start"**

```bash
# 로그 확인
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=100 \
  --format=json

# 컨테이너 로컬 테스트
docker run -p 8000:8000 \
  us-central1-docker.pkg.dev/$PROJECT_ID/ai-agent/ai-agent-api:latest
```

**문제: "Memory limit exceeded"**

```bash
# 메모리 증가
gcloud run services update ai-agent-api \
  --memory=4Gi \
  --region=us-central1

# 또는 cloudbuild.yaml 수정
_MEMORY: '4Gi'
```

**문제: "Cold start too slow"**

```bash
# 최소 인스턴스 설정
gcloud run services update ai-agent-api \
  --min-instances=1 \
  --region=us-central1

# 또는 cloudbuild.yaml 수정
_MIN_INSTANCES: '1'
```

### 3.4 데이터베이스 문제

**문제: "Connection refused to PostgreSQL"**

```bash
# 컨테이너 네트워크 확인
docker network ls
docker network inspect ai-agent_ai-agent-network

# PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# 직접 연결 테스트
docker-compose exec ai-agent \
  psql -h postgres -U postgres -d ai_agent
```

**문제: "pgvector extension not found"**

```bash
# 수동 설치
docker-compose exec postgres psql -U postgres -d ai_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 확인
docker-compose exec postgres psql -U postgres -d ai_agent -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

---

## 4. 부록

### 4.1 환경별 설정 비교

| 항목 | 로컬 (Mock) | 로컬 (PostgreSQL) | Staging | Production |
|------|-------------|-------------------|---------|------------|
| Vector DB | Mock (In-memory) | PostgreSQL + pgvector | Cloud SQL + pgvector | Vertex AI Vector Search |
| Graph DB | Mock (In-memory) | PostgreSQL | Neo4j | Neo4j + Redis |
| LLM | Vertex AI | Vertex AI | Vertex AI | Vertex AI |
| 인스턴스 | 1 (Docker) | 1 (Docker) | 1-3 (Cloud Run) | 1-10 (Cloud Run) |
| 메모리 | 2GB | 4GB | 4GB | 8GB |

### 4.2 비용 예측

**로컬 개발:**
- Docker: 무료
- Vertex AI API: ~$5-10/월 (개발용)

**Staging:**
- Cloud Run: ~$10-20/월
- Cloud SQL: ~$30/월
- Vertex AI: ~$20/월
- 총: ~$60/월

**Production (1K users):**
- Cloud Run: ~$100/월
- Vertex AI Vector Search: ~$200/월
- Cloud SQL: ~$100/월
- Vertex AI API: ~$150/월
- 총: ~$550/월

### 4.3 체크리스트

**로컬 개발 시작 전:**
- [ ] Docker & Docker Compose 설치
- [ ] gcloud CLI 설치 및 로그인
- [ ] GCP 프로젝트 생성
- [ ] .env 파일 설정
- [ ] Vertex AI API 활성화

**배포 전:**
- [ ] 모든 테스트 통과
- [ ] requirements.txt 업데이트
- [ ] 환경 변수 검증
- [ ] Secret Manager 설정
- [ ] Artifact Registry 생성
- [ ] Cloud Run 서비스 계정 권한 설정

**배포 후:**
- [ ] 헬스 체크 통과
- [ ] 주요 API 엔드포인트 테스트
- [ ] 로그 모니터링
- [ ] 메트릭 확인
- [ ] 알림 설정

---

**문서 버전:** 1.0
**최종 업데이트:** 2026-02-24
**담당자:** AI Agent DevOps Team
