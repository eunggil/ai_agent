# 데이터 스키마 상세 설계

## 목차

1. [BigQuery 스키마](#1-bigquery-스키마)
2. [Vector DB 스키마](#2-vector-db-스키마)
3. [Firestore 스키마](#3-firestore-스키마)
4. [Pub/Sub 메시지 스키마](#4-pubsub-메시지-스키마)

---

## 1. BigQuery 스키마

### 1.1 사용자 행동 로그 (user_behavior_logs)

```sql
CREATE TABLE `project.analytics.user_behavior_logs` (
  -- 기본 정보
  event_id STRING NOT NULL,
  user_id STRING NOT NULL,
  session_id STRING,
  timestamp TIMESTAMP NOT NULL,

  -- 이벤트 정보
  event_type STRING NOT NULL,  -- view, like, share, comment, skip, request_ai
  content_id STRING,
  content_type STRING,  -- video, image, article, ai_generated

  -- 컨텍스트
  device_type STRING,  -- mobile, tablet, desktop
  platform STRING,  -- ios, android, web
  app_version STRING,
  location GEOGRAPHY,
  country STRING,
  city STRING,

  -- 행동 세부 정보
  duration_seconds FLOAT64,  -- 시청/읽기 시간
  scroll_depth FLOAT64,  -- 스크롤 깊이 (0-1)
  interaction_count INT64,  -- 인터랙션 횟수
  completion_rate FLOAT64,  -- 완료율 (0-1)

  -- 메타데이터
  metadata JSON,
  user_agent STRING,
  referrer STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, event_type
OPTIONS(
  description="사용자 행동 로그",
  partition_expiration_days=730  -- 2년 보관
);
```

### 1.2 AI 생성 로그 (ai_generation_logs)

```sql
CREATE TABLE `project.analytics.ai_generation_logs` (
  -- 기본 정보
  generation_id STRING NOT NULL,
  user_id STRING NOT NULL,
  request_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,

  -- 요청 정보
  prompt TEXT,
  image_input STRING,  -- GCS path
  request_type STRING,  -- text_only, image_prompt, multimodal

  -- 생성 결과
  status STRING NOT NULL,  -- success, failed, timeout, quota_exceeded
  output_url STRING,  -- GCS path
  output_type STRING,  -- video, image, article

  -- 성능 메트릭
  generation_time_seconds FLOAT64,
  model_used STRING,  -- gemini-pro, imagen-3, etc.
  tokens_used INT64,

  -- 비용
  cost_usd FLOAT64,
  cost_breakdown JSON,  -- {llm: 0.05, image: 0.10, video: 0.03}

  -- AI Agent 단계별 메트릭
  state_interpretation_time FLOAT64,
  strategy_planning_time FLOAT64,
  creative_generation_time FLOAT64,

  -- 품질 메트릭
  safety_score FLOAT64,  -- 0-1
  quality_score FLOAT64,  -- 0-1
  user_rating FLOAT64,  -- 사용자 평가 (1-5)

  -- 상태 및 전략
  state_interpretation JSON,
  strategy_plan JSON,

  -- 에러 정보
  error_message STRING,
  error_code STRING,

  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, status
OPTIONS(
  description="AI 생성 요청 및 결과 로그"
);
```

### 1.3 광고 노출/클릭 로그 (ad_impression_logs)

```sql
CREATE TABLE `project.analytics.ad_impression_logs` (
  -- 기본 정보
  impression_id STRING NOT NULL,
  user_id STRING NOT NULL,
  session_id STRING,
  timestamp TIMESTAMP NOT NULL,

  -- 광고 정보
  ad_id STRING NOT NULL,
  campaign_id STRING NOT NULL,
  advertiser_id STRING,

  -- 콘텐츠 정보
  content_id STRING,  -- 광고가 표시된 콘텐츠
  placement_type STRING,  -- story_blend, inline, subtle
  position INT64,  -- 피드 내 위치

  -- 매칭 정보
  similarity_score FLOAT64,
  revenue_score FLOAT64,
  fitness_score FLOAT64,
  final_score FLOAT64,

  -- 사용자 행동
  impression_time TIMESTAMP,
  view_duration_seconds FLOAT64,
  click_time TIMESTAMP,
  conversion_time TIMESTAMP,
  conversion_value FLOAT64,

  -- 수익
  bid_amount FLOAT64,
  revenue FLOAT64,
  revenue_type STRING,  -- cpm, cpc, cpa

  -- 컨텍스트
  user_state JSON,  -- 노출 당시 사용자 상태
  device_type STRING,
  location GEOGRAPHY,

  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY ad_id, campaign_id, user_id
OPTIONS(
  description="광고 노출 및 성과 로그"
);
```

### 1.4 벡터 업데이트 로그 (vector_update_logs)

```sql
CREATE TABLE `project.analytics.vector_update_logs` (
  -- 기본 정보
  update_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,

  -- 대상 정보
  entity_type STRING NOT NULL,  -- user_long_term, user_short_term, content, ad
  entity_id STRING NOT NULL,

  -- 벡터 정보
  vector_version INT64,
  update_type STRING,  -- full_rebuild, incremental, real_time
  data_window_days INT64,  -- 계산에 사용된 데이터 기간

  -- 성능
  computation_time_seconds FLOAT64,
  source_rows_processed INT64,

  -- 품질
  confidence_score FLOAT64,
  drift_from_previous FLOAT64,  -- 이전 버전과의 차이

  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY entity_type, entity_id
OPTIONS(
  description="벡터 생성 및 업데이트 로그"
);
```

### 1.5 사용자 프로필 (user_profiles)

```sql
CREATE TABLE `project.analytics.user_profiles` (
  -- 기본 정보
  user_id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP,

  -- 인구통계
  age INT64,
  gender STRING,
  country STRING,
  language STRING,

  -- 티어
  user_tier STRING,  -- free, standard, premium
  subscription_start DATE,
  subscription_end DATE,

  -- 선호도 (집계)
  favorite_categories ARRAY<STRING>,
  content_length_preference STRING,  -- short, medium, long
  viewing_times ARRAY<STRING>,  -- morning, afternoon, evening, night

  -- 행동 통계
  total_views INT64,
  total_likes INT64,
  total_shares INT64,
  total_comments INT64,
  avg_session_duration_minutes FLOAT64,

  -- AI 사용 통계
  ai_generations_count INT64,
  ai_generations_today INT64,
  last_ai_generation_time TIMESTAMP,

  -- 광고 통계
  total_ad_views INT64,
  total_ad_clicks INT64,
  ad_ctr FLOAT64,

  metadata JSON
)
OPTIONS(
  description="사용자 프로필 스냅샷 (일 단위 업데이트)"
);
```

---

## 2. Vector DB 스키마

> **현재 구현:** 로컬 개발 환경은 PostgreSQL + pgvector를 사용합니다.
> 임베딩 모델: Vertex AI **text-embedding-004** (768차원)
> 벡터 인덱스: **HNSW** (cosine similarity)

### 2.1 사용자 테이블 (PostgreSQL)

```sql
CREATE TABLE users (
  user_id       VARCHAR(50) PRIMARY KEY,
  name          VARCHAR(100),
  age           INT,
  gender        VARCHAR(10),
  country       VARCHAR(10),
  interests     TEXT[],           -- 관심사 배열
  tier          VARCHAR(20),      -- free | standard | premium
  embedding     vector(768),      -- text-embedding-004 768차원
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 인덱스 (cosine similarity)
CREATE INDEX idx_users_embedding
ON users
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**데모 데이터:** 15명 (seed_demo_data.py로 자동 시드)

### 2.2 캠페인 테이블 (광고 캠페인)

```sql
CREATE TABLE campaigns (
  campaign_id    VARCHAR(50) PRIMARY KEY,
  title          VARCHAR(200),
  description    TEXT,
  category       VARCHAR(50),     -- fashion | beauty | health | food | ...
  target_age_min INT,
  target_age_max INT,
  target_gender  VARCHAR(10),
  bid_amount     DECIMAL(6,2),
  status         VARCHAR(20) DEFAULT 'active',
  image_url      TEXT,            -- 샘플 이미지 URL (picsum.photos 등)
  embedding      vector(768),     -- text-embedding-004 768차원
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 인덱스
CREATE INDEX idx_campaigns_embedding
ON campaigns
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**데모 데이터:** 100개 (8개 카테고리, seed_demo_data.py로 자동 시드)

### 2.3 상품 테이블

```sql
CREATE TABLE products (
  product_id   VARCHAR(50) PRIMARY KEY,
  name         VARCHAR(200),
  description  TEXT,
  category     VARCHAR(50),
  price        DECIMAL(10,2),
  brand        VARCHAR(100),
  image_url    TEXT,            -- 샘플 이미지 URL
  embedding    vector(768),
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 인덱스
CREATE INDEX idx_products_embedding
ON products
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**데모 데이터:** 100개 (8개 카테고리, seed_demo_data.py로 자동 시드)

### 2.4 콘텐츠 테이블

```sql
CREATE TABLE contents (
  content_id   VARCHAR(50) PRIMARY KEY,
  title        VARCHAR(200),
  body         TEXT,
  category     VARCHAR(50),
  content_type VARCHAR(50),     -- article | video | image
  embedding    vector(768),
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 인덱스
CREATE INDEX idx_contents_embedding
ON contents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**데모 데이터:** 100개 (seed_demo_data.py로 자동 시드)

### 2.5 벡터 검색 방식

광고 후보 검색 시 pgvector cosine similarity + bid 보너스 결합:

```sql
-- 코사인 유사도 기반 Top-K 광고 후보 검색
SELECT
  campaign_id, title, category, bid_amount, image_url,
  1 - (embedding <=> %s::vector) AS similarity
FROM campaigns
WHERE status = 'active'
ORDER BY (1 - (embedding <=> %s::vector)) * 0.7 + (bid_amount / 10.0) * 0.3 DESC
LIMIT 10;
```

- embedding 없는 경우 키워드 기반 점수로 폴백
- 최종 스코어 = 코사인 유사도(70%) + 입찰금액 보너스(30%)

---

## 3. Firestore 스키마

### 3.1 사용자 피드 캐시

```
Collection: users/{user_id}/feed_cache

Document Structure:
{
  "feed_id": "feed_abc123",
  "type": "basic" | "ai_generated",
  "created_at": Timestamp,
  "ttl": Timestamp,  // TTL for auto-deletion

  // 피드 아이템
  "items": [
    {
      "type": "content",
      "content_id": "cnt_123",
      "position": 0
    },
    {
      "type": "ad",
      "ad_id": "ad_456",
      "placement_type": "inline",
      "position": 10
    },
    ...
  ],

  // 메타데이터
  "metadata": {
    "total_items": 20,
    "content_count": 18,
    "ad_count": 2,
    "generation_method": "batch" | "on_demand",
    "user_tier": "free"
  },

  // 사용자 상태 (AI 피드인 경우)
  "user_state": {
    "emotional_state": {...},
    "intent": {...}
  },

  // 통계
  "stats": {
    "view_count": 0,
    "completion_rate": 0.0,
    "avg_item_duration": 0.0
  }
}

Indexes:
- type
- created_at
- ttl (for TTL policy)
```

### 3.2 생성된 AI 콘텐츠

```
Collection: generated_content/{content_id}

Document Structure:
{
  "content_id": "gen_xyz789",
  "user_id": "user_123",
  "created_at": Timestamp,
  "ttl": Timestamp,

  // 생성 결과
  "media": {
    "type": "video" | "image" | "article",
    "url": "gs://bucket/path/to/media.mp4",
    "thumbnail_url": "gs://bucket/path/to/thumb.jpg",
    "duration_seconds": 75,
    "format": "mp4",
    "resolution": "1080x1920",
    "file_size_bytes": 12345678
  },

  // 스크립트
  "script": {
    "full_text": "...",
    "scenes": [
      {
        "timestamp": "0-10s",
        "description": "...",
        "narration": "...",
        "audio": "ambient_nature"
      },
      ...
    ]
  },

  // 통합된 광고
  "integrated_ads": [
    {
      "ad_id": "ad_456",
      "placement_type": "story_blend",
      "timestamp": "10-20s",
      "transition": "smooth"
    }
  ],

  // 생성 메타데이터
  "generation_metadata": {
    "model_used": "gemini-pro",
    "generation_time_seconds": 6.5,
    "cost_usd": 0.18,
    "state_interpretation": {...},
    "strategy_plan": {...}
  },

  // 품질 메트릭
  "quality": {
    "safety_score": 0.95,
    "quality_score": 0.87,
    "user_rating": 4.5,
    "user_feedback": "Great content!"
  },

  // 통계
  "stats": {
    "view_count": 15,
    "like_count": 3,
    "share_count": 1,
    "completion_rate": 0.85,
    "avg_watch_time": 68.5
  }
}

Indexes:
- user_id
- created_at
- media.type
```

### 3.3 사용자 프로필 캐시

```
Collection: user_profiles/{user_id}

Document Structure:
{
  "user_id": "user_123",
  "updated_at": Timestamp,

  // 기본 정보
  "profile": {
    "display_name": "...",
    "avatar_url": "...",
    "age": 32,
    "gender": "female",
    "country": "KR",
    "language": "ko"
  },

  // 티어
  "subscription": {
    "tier": "premium",
    "start_date": Date,
    "end_date": Date,
    "auto_renew": true
  },

  // 선호도 (요약)
  "preferences": {
    "favorite_categories": ["wellness", "travel", "food"],
    "content_length": "medium",
    "preferred_times": ["evening"],
    "notification_enabled": true
  },

  // 할당량
  "quotas": {
    "ai_generations_today": 3,
    "ai_generations_limit": 5,
    "last_reset": Date
  },

  // 최근 활동
  "recent_activity": {
    "last_seen": Timestamp,
    "last_ai_generation": Timestamp,
    "session_count_today": 2
  },

  // 통계 요약
  "stats_summary": {
    "total_views": 1543,
    "total_likes": 234,
    "avg_session_minutes": 23.5
  }
}

Indexes:
- subscription.tier
- updated_at
```

### 3.4 활성 캠페인

```
Collection: active_campaigns/{campaign_id}

Document Structure:
{
  "campaign_id": "camp_789",
  "advertiser_id": "adv_456",
  "created_at": Timestamp,
  "updated_at": Timestamp,

  // 캠페인 정보
  "name": "Summer Health Promotion",
  "description": "...",
  "status": "active" | "paused" | "completed",

  // 스케줄
  "schedule": {
    "start_date": Date,
    "end_date": Date,
    "timezone": "Asia/Seoul"
  },

  // 예산
  "budget": {
    "total": 10000.00,
    "daily": 500.00,
    "remaining": 7234.50,
    "currency": "USD"
  },

  // 광고 목록
  "ad_ids": ["ad_456", "ad_457", "ad_458"],

  // 타겟팅
  "targeting": {
    "age_range": [25, 40],
    "genders": ["all"],
    "countries": ["KR", "JP"],
    "interests": ["health", "wellness"]
  },

  // 실시간 성과
  "performance": {
    "impressions": 12543,
    "clicks": 523,
    "conversions": 47,
    "ctr": 0.0417,
    "cvr": 0.0899,
    "revenue": 2765.50,
    "roi": 2.76
  },

  // 최적화 설정
  "optimization": {
    "goal": "maximize_conversions" | "maximize_clicks" | "maximize_reach",
    "auto_bid": true,
    "bid_strategy": "target_cpa"
  }
}

Indexes:
- status
- advertiser_id
- schedule.end_date
```

---

## 4. Pub/Sub 메시지 스키마

### 4.1 사용자 행동 이벤트 (topic: user-events)

```json
{
  "event_id": "evt_abc123",
  "event_type": "view" | "like" | "share" | "comment" | "skip",
  "user_id": "user_123",
  "session_id": "sess_456",
  "timestamp": "2026-02-24T14:30:00Z",

  "content": {
    "content_id": "cnt_789",
    "content_type": "video",
    "category": "wellness"
  },

  "context": {
    "device_type": "mobile",
    "platform": "ios",
    "app_version": "1.2.3",
    "location": {
      "country": "KR",
      "city": "Seoul"
    },
    "time_of_day": "afternoon",
    "weather": "sunny"
  },

  "behavior": {
    "duration_seconds": 45.3,
    "completion_rate": 0.85,
    "scroll_depth": 0.75,
    "interaction_count": 2
  },

  "metadata": {}
}
```

### 4.2 AI 피드 생성 요청 (topic: feed-generation)

```json
{
  "request_id": "req_xyz789",
  "user_id": "user_123",
  "request_type": "ai_feed",
  "timestamp": "2026-02-24T14:30:00Z",

  "prompt": {
    "text": "오늘 기분 좋은 영상 보여줘",
    "image_url": "gs://bucket/uploads/image_123.jpg"
  },

  "context": {
    "session_id": "sess_456",
    "device_type": "mobile",
    "location": {
      "country": "KR",
      "city": "Seoul"
    },
    "time_of_day": "evening",
    "weather": "rainy"
  },

  "user_profile": {
    "user_tier": "premium",
    "age": 32,
    "gender": "female",
    "language": "ko"
  },

  "constraints": {
    "max_cost_usd": 0.50,
    "timeout_seconds": 30,
    "quality_tier": "high"
  },

  "metadata": {}
}
```

### 4.3 벡터 업데이트 트리거 (topic: vector-update)

```json
{
  "update_id": "upd_def456",
  "trigger_type": "user_event" | "scheduled_batch" | "manual",
  "timestamp": "2026-02-24T14:30:00Z",

  "target": {
    "entity_type": "user_long_term" | "user_short_term" | "content" | "ad",
    "entity_ids": ["user_123", "user_456"],
    "update_mode": "full_rebuild" | "incremental"
  },

  "data_window": {
    "start_date": "2026-01-25",
    "end_date": "2026-02-24",
    "days": 30
  },

  "priority": "high" | "normal" | "low",

  "metadata": {}
}
```

### 4.4 광고 서빙 이벤트 (topic: ad-serving)

```json
{
  "event_id": "adv_ghi789",
  "event_type": "impression" | "click" | "conversion",
  "timestamp": "2026-02-24T14:30:00Z",

  "user": {
    "user_id": "user_123",
    "session_id": "sess_456"
  },

  "ad": {
    "ad_id": "ad_456",
    "campaign_id": "camp_789",
    "advertiser_id": "adv_123"
  },

  "context": {
    "content_id": "cnt_789",
    "placement_type": "story_blend",
    "position": 10,
    "device_type": "mobile"
  },

  "matching": {
    "similarity_score": 0.87,
    "revenue_score": 3.45,
    "fitness_score": 0.92,
    "final_score": 0.89
  },

  "financial": {
    "bid_amount": 2.50,
    "revenue": 2.50,
    "revenue_type": "cpm"
  },

  "behavior": {
    "view_duration_seconds": 5.3,
    "clicked": true,
    "converted": false
  },

  "metadata": {}
}
```

### 4.5 콘텐츠 검수 (topic: content-moderation)

```json
{
  "moderation_id": "mod_jkl012",
  "content_id": "gen_xyz789",
  "content_type": "ai_generated_video",
  "timestamp": "2026-02-24T14:30:00Z",

  "content_url": "gs://bucket/generated/video_123.mp4",
  "script": "...",

  "checks": [
    "safety",
    "quality",
    "brand_safety",
    "copyright"
  ],

  "priority": "high",

  "metadata": {
    "user_id": "user_123",
    "generation_cost": 0.18
  }
}
```

---

## 5. 데이터 파이프라인

### 5.1 실시간 파이프라인

```
사용자 행동
    │
    └──→ Pub/Sub (user-events)
            │
            ├──→ BigQuery Subscription
            │       └──→ Streaming Insert to BigQuery
            │
            ├──→ Vector Update Subscriber
            │       └──→ Update short-term vector
            │
            └──→ Analytics Subscriber
                    └──→ Real-time metrics
```

### 5.2 배치 파이프라인

```
Daily 2AM UTC:
    BigQuery
        │
        ├──→ 사용자 프로필 집계
        │       └──→ Update user_profiles table
        │
        ├──→ 장기 벡터 생성
        │       └──→ Update user_long_term_vectors
        │
        ├──→ 콘텐츠 인기도 계산
        │       └──→ Update content_vectors.popularity_score
        │
        └──→ 광고 성과 계산
                └──→ Update ad_vectors.performance_score
```

---

## 6. 데이터 보관 정책

| 데이터 유형 | 보관 기간 | 아카이브 |
|------------|----------|---------|
| 사용자 행동 로그 | 2년 | Cloud Storage |
| AI 생성 로그 | 1년 | Cloud Storage |
| 광고 로그 | 2년 | Cloud Storage |
| 벡터 업데이트 로그 | 6개월 | 삭제 |
| 생성된 미디어 | 30일 | 삭제 또는 아카이브 |
| 피드 캐시 | TTL 기반 | 자동 삭제 |
| 사용자 프로필 | 영구 | - |

---

**문서 버전:** 1.1
**최종 수정일:** 2026-02-25
