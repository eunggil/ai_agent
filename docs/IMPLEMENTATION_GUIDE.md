# 구현 가이드

## 목차

1. [개발 환경 설정](#1-개발-환경-설정)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [핵심 컴포넌트 구현](#3-핵심-컴포넌트-구현)
4. [배포 가이드](#4-배포-가이드)
5. [모니터링 및 운영](#5-모니터링-및-운영)

---

## 1. 개발 환경 설정

### 1.1 필수 도구

```bash
# Python 3.11+
python --version

# Node.js 20+ (프론트엔드)
node --version

# Docker
docker --version

# gcloud CLI
gcloud --version

# Terraform (인프라)
terraform --version
```

### 1.2 GCP 프로젝트 설정

```bash
# GCP 프로젝트 생성
gcloud projects create addeep-ai-agent --name="AI Agent"

# 프로젝트 설정
gcloud config set project addeep-ai-agent

# 필요한 API 활성화
gcloud services enable \
  compute.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  aiplatform.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com
```

### 1.3 로컬 개발 환경

```bash
# 저장소 클론
git clone https://github.com/your-org/addeep-ai-agent.git
cd addeep-ai-agent

# Python 가상 환경
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# Docker Compose로 로컬 인프라 시작
docker-compose up -d
```

### 1.4 .env 설정

```bash
# .env
# GCP
GCP_PROJECT_ID=addeep-ai-agent
GCP_REGION=us-central1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/addeep
REDIS_URL=redis://localhost:6379

# Firestore
FIRESTORE_DATABASE=(default)

# Pub/Sub
PUBSUB_USER_EVENTS_TOPIC=user-events
PUBSUB_FEED_GENERATION_TOPIC=feed-generation
PUBSUB_VECTOR_UPDATE_TOPIC=vector-update
PUBSUB_AD_SERVING_TOPIC=ad-serving

# AI Models
GEMINI_API_KEY=your-api-key
IMAGEN_API_KEY=your-api-key

# Storage
GCS_BUCKET_MEDIA=addeep-media
GCS_BUCKET_GENERATED=addeep-generated

# Auth
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
REDIS_RATE_LIMIT_PREFIX=rate_limit:
FREE_TIER_DAILY_LIMIT=5
PREMIUM_TIER_DAILY_LIMIT=-1

# Monitoring
GOOGLE_CLOUD_MONITORING=true
```

---

## 2. 프로젝트 구조

```
addeep-ai-agent/
├── src/
│   ├── api/                      # API 엔드포인트
│   │   ├── v1/
│   │   │   ├── feed.py          # 피드 API
│   │   │   ├── ai.py            # AI 생성 API
│   │   │   ├── user.py          # 사용자 API
│   │   │   └── ads.py           # 광고 API
│   │   └── middleware/
│   │       ├── auth.py          # 인증 미들웨어
│   │       ├── rate_limit.py    # Rate limiting
│   │       └── error_handler.py # 에러 처리
│   │
│   ├── core/                     # 핵심 비즈니스 로직
│   │   ├── vector/
│   │   │   ├── generator.py     # 벡터 생성
│   │   │   ├── search.py        # 벡터 검색
│   │   │   └── combiner.py      # 벡터 결합
│   │   │
│   │   ├── ai_agent/
│   │   │   ├── state_interpreter.py    # 상태 해석기
│   │   │   ├── strategy_planner.py     # 전략 결정기
│   │   │   └── creative_generator.py   # 미디어 생성기
│   │   │
│   │   ├── feed/
│   │   │   ├── orchestrator.py  # 피드 오케스트레이션
│   │   │   ├── basic_feed.py    # 기본 피드
│   │   │   └── ai_feed.py       # AI 피드
│   │   │
│   │   └── ads/
│   │       ├── matcher.py       # 광고 매칭
│   │       ├── scorer.py        # 광고 스코어링
│   │       └── integrator.py    # 광고 통합
│   │
│   ├── data/                     # 데이터 레이어
│   │   ├── bigquery/
│   │   │   ├── client.py
│   │   │   └── schemas.py
│   │   ├── vector_db/
│   │   │   ├── postgresql.py
│   │   │   └── vertex_search.py
│   │   ├── firestore/
│   │   │   └── client.py
│   │   ├── pubsub/
│   │   │   ├── publisher.py
│   │   │   └── subscriber.py
│   │   └── storage/
│   │       └── gcs.py
│   │
│   ├── workers/                  # 백그라운드 워커
│   │   ├── feed_generator.py    # 피드 생성 워커
│   │   ├── vector_updater.py    # 벡터 업데이트 워커
│   │   └── analytics.py         # 분석 워커
│   │
│   ├── models/                   # 데이터 모델
│   │   ├── user.py
│   │   ├── content.py
│   │   ├── ad.py
│   │   └── feed.py
│   │
│   └── utils/                    # 유틸리티
│       ├── cache.py
│       ├── logging.py
│       └── metrics.py
│
├── tests/                        # 테스트
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── infrastructure/               # 인프라 코드
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── docker/
│       ├── Dockerfile.api
│       ├── Dockerfile.worker
│       └── docker-compose.yml
│
├── docs/                         # 문서
│   ├── ARCHITECTURE.md
│   ├── DATA_SCHEMA.md
│   ├── API_SPEC.md
│   └── IMPLEMENTATION_GUIDE.md
│
├── scripts/                      # 스크립트
│   ├── setup.sh
│   ├── migrate.sh
│   └── deploy.sh
│
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 3. 핵심 컴포넌트 구현

### 3.1 벡터 생성기

**파일:** `src/core/vector/generator.py`

```python
from typing import Dict, List, Optional
import numpy as np
from google.cloud import aiplatform
from datetime import datetime, timedelta

class VectorGenerator:
    """벡터 생성 및 관리"""

    def __init__(self, project_id: str, location: str):
        self.project_id = project_id
        self.location = location
        aiplatform.init(project=project_id, location=location)

    async def generate_long_term_vector(
        self,
        user_id: str,
        window_days: int = 90
    ) -> tuple[np.ndarray, Dict]:
        """사용자 장기 벡터 생성"""

        # 1. BigQuery에서 행동 데이터 수집
        behaviors = await self._fetch_user_behaviors(
            user_id=user_id,
            days=window_days
        )

        if not behaviors:
            # 신규 사용자: 기본 벡터
            return self._get_default_vector(), {"confidence": 0.0}

        # 2. 특성 추출
        features = self._extract_long_term_features(behaviors)

        # 3. 프로필 텍스트 생성
        profile_text = self._generate_profile_text(features)

        # 4. 임베딩 생성
        vector = await self._embed_text(profile_text)

        # 5. 메타데이터 구성
        metadata = {
            "profile_summary": profile_text,
            "top_categories": features["top_categories"],
            "avg_viewing_time": features["avg_viewing_time"],
            "content_length_pref": features["content_length_pref"],
            "engagement_style": features["engagement_style"],
            "confidence": features["confidence"],
            "data_window_days": window_days,
            "source_events_count": len(behaviors)
        }

        return vector, metadata

    async def generate_short_term_vector(
        self,
        user_id: str,
        session_id: str,
        window_hours: int = 24
    ) -> tuple[np.ndarray, Dict]:
        """사용자 단기 벡터 생성"""

        # 1. 최근 행동 수집
        recent_behaviors = await self._fetch_recent_behaviors(
            user_id=user_id,
            hours=window_hours
        )

        # 2. 세션 컨텍스트 분석
        session_context = await self._analyze_session_context(session_id)

        # 3. 의도 추론
        intent_text = self._infer_intent(recent_behaviors, session_context)

        # 4. 임베딩 생성
        vector = await self._embed_text(intent_text)

        # 5. 메타데이터
        metadata = {
            "intent_summary": intent_text,
            "current_mood": self._infer_mood(recent_behaviors),
            "recent_views": self._get_recent_categories(recent_behaviors),
            "time_of_day": session_context.get("time_of_day"),
            "device": session_context.get("device"),
            "location": session_context.get("location"),
            "confidence": self._calculate_confidence(recent_behaviors)
        }

        return vector, metadata

    def _extract_long_term_features(self, behaviors: List[Dict]) -> Dict:
        """장기 행동에서 특성 추출"""

        # 카테고리 분포
        category_counts = {}
        for b in behaviors:
            cat = b.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        top_categories = [cat for cat, _ in top_categories]

        # 시청 시간대
        hour_counts = {}
        for b in behaviors:
            hour = b["timestamp"].hour
            period = self._hour_to_period(hour)
            hour_counts[period] = hour_counts.get(period, 0) + 1

        avg_viewing_time = max(hour_counts, key=hour_counts.get)

        # 콘텐츠 길이 선호도
        durations = [b.get("duration_seconds", 0) for b in behaviors]
        avg_duration = np.mean(durations) if durations else 0

        if avg_duration < 30:
            content_length_pref = "short"
        elif avg_duration < 120:
            content_length_pref = "medium"
        else:
            content_length_pref = "long"

        # 인게이지먼트 스타일
        likes = sum(1 for b in behaviors if b.get("event_type") == "like")
        shares = sum(1 for b in behaviors if b.get("event_type") == "share")
        comments = sum(1 for b in behaviors if b.get("event_type") == "comment")

        total_engagement = likes + shares + comments
        view_count = sum(1 for b in behaviors if b.get("event_type") == "view")

        if view_count > 0:
            engagement_rate = total_engagement / view_count
            if engagement_rate > 0.3:
                engagement_style = "active"
            elif engagement_rate > 0.1:
                engagement_style = "moderate"
            else:
                engagement_style = "passive"
        else:
            engagement_style = "unknown"

        # 신뢰도
        confidence = min(len(behaviors) / 100, 1.0)  # 100개 이상이면 1.0

        return {
            "top_categories": top_categories,
            "avg_viewing_time": avg_viewing_time,
            "content_length_pref": content_length_pref,
            "engagement_style": engagement_style,
            "confidence": confidence
        }

    def _generate_profile_text(self, features: Dict) -> str:
        """특성을 텍스트로 변환"""

        categories = ", ".join(features["top_categories"][:3])

        text = (
            f"User with strong interest in {categories}. "
            f"Prefers {features['content_length_pref']} content. "
            f"Typically active during {features['avg_viewing_time']}. "
            f"Engagement style: {features['engagement_style']}."
        )

        return text

    async def _embed_text(self, text: str) -> np.ndarray:
        """텍스트를 벡터로 임베딩"""

        # Vertex AI Text Embeddings
        model = aiplatform.TextEmbeddingModel.from_pretrained(
            "text-embedding-004"
        )

        embeddings = model.get_embeddings([text])
        vector = np.array(embeddings[0].values)

        return vector

    @staticmethod
    def _hour_to_period(hour: int) -> str:
        """시간을 시간대로 변환"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"

    @staticmethod
    def _get_default_vector() -> np.ndarray:
        """신규 사용자용 기본 벡터"""
        return np.random.randn(768) * 0.01  # 작은 랜덤 벡터
```

### 3.2 AI Agent - State Interpreter

**파일:** `src/core/ai_agent/state_interpreter.py`

```python
from typing import Dict, Optional
from google.cloud import aiplatform
import json

class StateInterpreter:
    """사용자 상태 해석기"""

    PROMPT_TEMPLATE = """
You are a user state interpreter for a personalized content platform.

User Profile Summary:
{long_term_summary}

Recent Behavior:
{short_term_summary}

Current Context:
{session_context}

User Request:
"{user_prompt}"

{image_analysis}

Task:
Analyze the user's current emotional state, intent, and needs.
Determine the optimal persuasion strategy and ad integration approach.

Output a JSON with the following structure:
{{
  "emotional_state": {{
    "primary": "seeking_relaxation" | "seeking_excitement" | "stressed" | "curious" | "bored",
    "secondary": "string",
    "energy_level": "high" | "medium" | "low",
    "mood": "positive" | "neutral" | "negative"
  }},
  "intent": {{
    "content_type": "video" | "image" | "article",
    "content_length": "short" | "medium" | "long",
    "content_tone": "uplifting" | "calm" | "exciting" | "informative",
    "engagement_type": "active" | "passive"
  }},
  "persuasion_strategy": {{
    "approach": "direct" | "soft_recommendation" | "storytelling",
    "tone": "friendly" | "professional" | "casual",
    "directness": "high" | "medium" | "low",
    "value_proposition": "entertainment" | "education" | "mood_improvement" | "social_connection"
  }},
  "ad_integration_preference": {{
    "tolerance": "high" | "medium" | "low",
    "preferred_type": "story_blend" | "inline" | "subtle",
    "max_ads": 0 | 1 | 2,
    "timing": "before_content" | "during_content" | "after_content"
  }},
  "confidence": 0.0-1.0
}}

Be specific and actionable. Consider cultural context and time of day.
"""

    def __init__(self, model_name: str = "gemini-1.5-pro"):
        self.model = aiplatform.GenerativeModel(model_name)

    async def interpret(
        self,
        user_id: str,
        prompt: str,
        long_term_summary: str,
        short_term_summary: str,
        session_context: Dict,
        image: Optional[str] = None
    ) -> Dict:
        """사용자 상태 해석"""

        # 이미지 분석 (있는 경우)
        image_analysis = ""
        if image:
            image_analysis = await self._analyze_image(image)
            image_analysis = f"\n\nUser uploaded image analysis:\n{image_analysis}"

        # 프롬프트 구성
        full_prompt = self.PROMPT_TEMPLATE.format(
            long_term_summary=long_term_summary,
            short_term_summary=short_term_summary,
            session_context=json.dumps(session_context, indent=2),
            user_prompt=prompt,
            image_analysis=image_analysis
        )

        # LLM 호출
        response = await self.model.generate_content_async(
            full_prompt,
            generation_config={
                "temperature": 0.7,
                "response_mime_type": "application/json"
            }
        )

        # JSON 파싱
        result = json.loads(response.text)

        return result

    async def _analyze_image(self, image_path: str) -> str:
        """이미지 분석"""

        # Gemini Vision으로 이미지 분석
        from google.cloud import storage

        # GCS에서 이미지 로드
        storage_client = storage.Client()
        # ... 이미지 로드 로직

        prompt = """
        Analyze this image and describe:
        1. Main subject and context
        2. Mood and atmosphere
        3. What the user might be looking for based on this image
        """

        response = await self.model.generate_content_async(
            [prompt, image_path]
        )

        return response.text
```

### 3.3 광고 매칭 엔진

**파일:** `src/core/ads/matcher.py`

```python
from typing import List, Dict
import numpy as np
from dataclasses import dataclass

@dataclass
class AdCandidate:
    ad_id: str
    campaign_id: str
    vector: np.ndarray
    metadata: Dict
    targeting_rules: Dict
    bid_amount: float
    performance_score: float
    budget_remaining: float
    similarity: float

class AdMatcher:
    """광고 매칭 엔진"""

    def __init__(self, vector_db_client):
        self.vector_db = vector_db_client

    async def match_ads(
        self,
        user_vector: np.ndarray,
        user_profile: Dict,
        state: Dict,
        max_ads: int = 2
    ) -> List[Dict]:
        """광고 매칭 4단계 프로세스"""

        # Step 1: 벡터 유사도 검색
        candidates = await self._search_by_similarity(
            user_vector,
            limit=20
        )

        # Step 2: 캠페인 룰 필터링
        filtered = self._filter_by_rules(
            candidates,
            user_profile
        )

        # Step 3: 수익 스코어 계산
        scored = self._compute_revenue_scores(
            filtered,
            state
        )

        # Step 4: 전략 적합도 평가
        final = self._compute_strategy_fitness(
            scored,
            state
        )

        # 최종 선택
        selected = self._select_top_ads(final, max_ads)

        return selected

    async def _search_by_similarity(
        self,
        user_vector: np.ndarray,
        limit: int
    ) -> List[AdCandidate]:
        """벡터 유사도 기반 검색"""

        query = """
            SELECT
                ad_id,
                campaign_id,
                vector,
                metadata,
                targeting_rules,
                bid_amount,
                performance_score,
                budget_remaining,
                1 - (vector <=> $1::vector) AS similarity
            FROM ad_vectors
            WHERE
                status = 'active'
                AND budget_remaining > 0
            ORDER BY vector <=> $1::vector
            LIMIT $2
        """

        results = await self.vector_db.execute(
            query,
            user_vector.tolist(),
            limit
        )

        return [AdCandidate(**row) for row in results]

    def _filter_by_rules(
        self,
        candidates: List[AdCandidate],
        user_profile: Dict
    ) -> List[AdCandidate]:
        """타겟팅 룰 필터링"""

        filtered = []

        for ad in candidates:
            rules = ad.targeting_rules

            # 나이 체크
            if "age_range" in rules:
                min_age, max_age = rules["age_range"]
                if not (min_age <= user_profile.get("age", 0) <= max_age):
                    continue

            # 성별 체크
            if "genders" in rules:
                if "all" not in rules["genders"]:
                    if user_profile.get("gender") not in rules["genders"]:
                        continue

            # 국가 체크
            if "countries" in rules:
                if user_profile.get("country") not in rules["countries"]:
                    continue

            # 관심사 체크
            if "interests" in rules:
                user_interests = set(user_profile.get("interests", []))
                required_interests = set(rules["interests"])
                if not (user_interests & required_interests):
                    continue

            filtered.append(ad)

        return filtered

    def _compute_revenue_scores(
        self,
        candidates: List[AdCandidate],
        state: Dict
    ) -> List[tuple[AdCandidate, float]]:
        """수익 스코어 계산"""

        scored = []

        for ad in candidates:
            # eCPM 계산
            ecpm = (
                ad.bid_amount *
                ad.performance_score *
                self._get_time_multiplier(state)
            )

            scored.append((ad, ecpm))

        return scored

    def _compute_strategy_fitness(
        self,
        scored_ads: List[tuple[AdCandidate, float]],
        state: Dict
    ) -> List[Dict]:
        """전략 적합도 평가"""

        final_scores = []

        for ad, revenue_score in scored_ads:
            # 감정 적합도
            emotional_fit = self._check_emotional_fit(
                ad.metadata.get("emotional_tone"),
                state["emotional_state"]
            )

            # 최종 스코어 (수익 60%, 적합도 40%)
            final_score = (
                0.6 * self._normalize(revenue_score, 0, 10) +
                0.4 * emotional_fit
            )

            final_scores.append({
                "ad": ad,
                "revenue_score": revenue_score,
                "fitness_score": emotional_fit,
                "final_score": final_score
            })

        return final_scores

    def _select_top_ads(
        self,
        scored_ads: List[Dict],
        max_ads: int
    ) -> List[Dict]:
        """최종 광고 선택"""

        # 정렬
        sorted_ads = sorted(
            scored_ads,
            key=lambda x: x["final_score"],
            reverse=True
        )

        # Top-N 선택
        return sorted_ads[:max_ads]

    @staticmethod
    def _normalize(value: float, min_val: float, max_val: float) -> float:
        """값 정규화 (0-1)"""
        if max_val == min_val:
            return 0.5
        return max(0, min(1, (value - min_val) / (max_val - min_val)))

    @staticmethod
    def _check_emotional_fit(ad_tone: str, user_state: Dict) -> float:
        """감정 적합도 체크"""

        # 간단한 매칭 테이블
        compatibility = {
            ("seeking_relaxation", "calm"): 1.0,
            ("seeking_relaxation", "energetic"): 0.3,
            ("seeking_excitement", "energetic"): 1.0,
            ("seeking_excitement", "calm"): 0.4,
            ("stressed", "calm"): 0.9,
            ("stressed", "urgent"): 0.2,
        }

        user_emotion = user_state.get("primary", "neutral")
        key = (user_emotion, ad_tone)

        return compatibility.get(key, 0.5)

    @staticmethod
    def _get_time_multiplier(state: Dict) -> float:
        """시간대 가중치"""

        time_of_day = state.get("context", {}).get("time_of_day", "evening")

        multipliers = {
            "morning": 1.1,
            "afternoon": 1.0,
            "evening": 1.2,  # 프라임 타임
            "night": 0.9
        }

        return multipliers.get(time_of_day, 1.0)
```

---

## 4. 배포 가이드

### 4.1 Terraform으로 인프라 구축

**파일:** `infrastructure/terraform/main.tf`

```hcl
# GCP Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud SQL (PostgreSQL with pgvector)
resource "google_sql_database_instance" "vector_db" {
  name             = "vector-db-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-n1-standard-2"

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    backup_configuration {
      enabled            = true
      start_time         = "03:00"
      point_in_time_recovery_enabled = true
    }
  }
}

# Pub/Sub Topics
resource "google_pubsub_topic" "user_events" {
  name = "user-events"
}

resource "google_pubsub_topic" "feed_generation" {
  name = "feed-generation"
}

# Cloud Run Services
resource "google_cloud_run_service" "api" {
  name     = "api-service"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/api:latest"

        env {
          name  = "DATABASE_URL"
          value = "postgresql://..."
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }
    }
  }
}

# Firestore Database
resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# GCS Buckets
resource "google_storage_bucket" "media" {
  name     = "${var.project_id}-media"
  location = var.region

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}
```

### 4.2 Docker 이미지 빌드

```bash
# API 서버 빌드
docker build -f infrastructure/docker/Dockerfile.api -t gcr.io/addeep-ai-agent/api:latest .

# 워커 빌드
docker build -f infrastructure/docker/Dockerfile.worker -t gcr.io/addeep-ai-agent/worker:latest .

# 푸시
docker push gcr.io/addeep-ai-agent/api:latest
docker push gcr.io/addeep-ai-agent/worker:latest
```

### 4.3 Cloud Run 배포

```bash
# API 배포
gcloud run deploy api-service \
  --image gcr.io/addeep-ai-agent/api:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=..."

# 워커 배포 (Pub/Sub 트리거)
gcloud run deploy feed-generator-worker \
  --image gcr.io/addeep-ai-agent/worker:latest \
  --region us-central1 \
  --platform managed \
  --no-allow-unauthenticated \
  --set-env-vars "WORKER_TYPE=feed_generator"
```

---

## 5. 모니터링 및 운영

### 5.1 주요 메트릭

```python
# src/utils/metrics.py

from google.cloud import monitoring_v3
from prometheus_client import Counter, Histogram, Gauge

# Prometheus 메트릭
feed_requests = Counter(
    'feed_requests_total',
    'Total feed requests',
    ['feed_type', 'status']
)

ai_generation_duration = Histogram(
    'ai_generation_duration_seconds',
    'AI generation duration',
    buckets=[1, 2, 5, 10, 20, 30]
)

vector_search_latency = Histogram(
    'vector_search_latency_seconds',
    'Vector search latency'
)

active_users = Gauge(
    'active_users',
    'Current active users'
)
```

### 5.2 로깅

```python
# src/utils/logging.py

import logging
from google.cloud import logging as cloud_logging

# Cloud Logging 설정
client = cloud_logging.Client()
client.setup_logging()

logger = logging.getLogger(__name__)

# 구조화된 로깅
def log_ai_generation(
    user_id: str,
    request_id: str,
    status: str,
    duration: float,
    cost: float
):
    logger.info(
        "AI generation completed",
        extra={
            "user_id": user_id,
            "request_id": request_id,
            "status": status,
            "duration_seconds": duration,
            "cost_usd": cost,
            "labels": {
                "component": "ai_generation",
                "environment": "production"
            }
        }
    )
```

### 5.3 알림 설정

```bash
# Cloud Monitoring Alert Policy
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High AI Generation Latency" \
  --condition-display-name="P95 latency > 30s" \
  --condition-threshold-value=30 \
  --condition-threshold-duration=300s
```

---

**문서 버전:** 1.0
**최종 수정일:** 2026-02-24
