# AI 기반 개인화 피드 생성형 SNS 아키텍처 설계

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [데이터 레이어 설계](#3-데이터-레이어-설계)
4. [벡터 DB 설계](#4-벡터-db-설계)
5. [AI Agent 설계](#5-ai-agent-설계)
6. [피드 생성 파이프라인](#6-피드-생성-파이프라인)
7. [광고 매칭 시스템](#7-광고-매칭-시스템)
8. [확장 전략](#8-확장-전략)
9. [구현 로드맵](#9-구현-로드맵)

---

## 1. 시스템 개요

### 1.1 프로젝트 비전

**글로벌 개인화 AI 기반 피드 생성형 SNS**

- AI 옵션 기반 온디맨드 콘텐츠 생성
- 광고/상품 자연스러운 결합
- 비동기 중심 고성능 아키텍처

### 1.2 핵심 철학

이 시스템은 단순한 추천 시스템이 아닌 **User-State Driven Media Generation Platform**입니다.

#### 기존 SNS의 접근
```
콘텐츠 생성 → 사용자 매칭 → 피드 노출
```

#### 우리 시스템의 접근
```
사용자 상태 추론 → 전략 결정 → 콘텐츠 생성 → 광고 결합 → 피드 노출
```

**핵심 차별점:**
- 벡터 검색은 "후보 찾기"일 뿐
- 진짜 핵심은 **"상태 추론 + 전략 결정 + 생성"**

### 1.3 관련 문서

이 아키텍처 설계는 여러 세부 문서로 구성되어 있습니다:

- **[AI Agent 상세 설계](AGENT_DESIGN.md)**: LangGraph 기반 에이전트 구현, 하이브리드 검색, 광고 랭킹
- **[PiMS & 온톨로지 설계](PIMS_ONTOLOGY.md)**: 상품 정보 관리, 온톨로지, 그래프 DB, VTO
- **[데이터 스키마](DATA_SCHEMA.md)**: BigQuery, Vector DB, Firestore, Pub/Sub 스키마
- **[API 명세서](API_SPEC.md)**: REST API 상세 명세
- **[구현 가이드](IMPLEMENTATION_GUIDE.md)**: 개발 환경, 배포, 모니터링

---

## 2. 전체 아키텍처

### 2.1 시스템 구성 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│  (Mobile App, Web App, API Gateway)                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Feed Orchestration Layer                       │
│  • 요청 처리                                                │
│  • 워커 관리                                                │
│  • 캐시 정책                                                │
│  • 생성 제한 정책                                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼────────┐   ┌──────▼─────────┐
│  Basic Feed    │   │  AI Feed       │
│  (Batch)       │   │  (On-Demand)   │
└───────┬────────┘   └──────┬─────────┘
        │                   │
        │         ┌─────────▼──────────────────────────────┐
        │         │     AI Agent Layer                     │
        │         │  ① State Interpreter                   │
        │         │  ② Strategy Planner                    │
        │         │  ③ Creative Generator                  │
        │         └─────────┬──────────────────────────────┘
        │                   │
        └─────────┬─────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Vector Engine Layer                            │
│  • 벡터 생성 파이프라인                                     │
│  • 벡터 저장 및 검색                                        │
│  • 벡터 결합 로직                                           │
│  • 광고 매칭 엔진                                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                 Data Layer                                  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │BigQuery  │  │ Pub/Sub  │  │Firestore │  │Vector DB │   │
│  │(분석뇌)  │  │(신경망)  │  │(서빙캐시)│  │(상태기억)│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 시스템 역할 정의

| 컴포넌트 | 역할 | 비유 |
|---------|------|------|
| BigQuery | 행동 로그 분석, 모델 재학습 | 분석 뇌 |
| Pub/Sub | 이벤트 스트림, 트리거 전파 | 이벤트 신경망 |
| Vector DB | 압축된 사용자 상태 저장 | 압축된 상태 기억 |
| Agent | 상태 추론, 전략 결정 | 전략가 |
| Generator | AI 미디어 생성 | 창작자 |
| Firestore | 생성 완료 피드 서빙 | 서빙 캐시 |

---

## 3. 데이터 레이어 설계

### 3.1 데이터 저장소 분리 전략

데이터 레이어는 **용도별로 4가지로 완전 분리**합니다.

#### (A) 행동 / 로우 데이터 저장

**저장소:** BigQuery

**목적:**
- 사용자 행동 로그 적재
- 사용자 원천 데이터
- 광고 노출/클릭 로그
- 오프라인 분석
- 모델 재학습 데이터

**특징:**
- 완전 오프라인 분석 영역
- 실시간 서빙 없음
- 대용량 배치 처리

**스키마 예시:**
```sql
-- 사용자 행동 로그
CREATE TABLE user_behavior_logs (
  user_id STRING,
  event_type STRING,  -- view, like, share, comment, skip
  content_id STRING,
  timestamp TIMESTAMP,
  session_id STRING,
  context JSON,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id;

-- 광고 노출 로그
CREATE TABLE ad_impression_logs (
  user_id STRING,
  ad_id STRING,
  campaign_id STRING,
  impression_time TIMESTAMP,
  click_time TIMESTAMP,
  conversion_time TIMESTAMP,
  revenue FLOAT64,
  metadata JSON
)
PARTITION BY DATE(impression_time)
CLUSTER BY user_id, campaign_id;
```

#### (B) 이벤트 스트림

**메시징:** Cloud Pub/Sub

**역할:**
- 사용자 행동 이벤트 전파
- 피드 생성 트리거
- 광고 집행 이벤트
- 벡터 재생성 트리거

**특징:**
- 시스템의 신경망 역할
- 비동기 처리의 핵심
- 확장성 보장

**Topic 구조:**
```
topics/
├── user-events          # 사용자 행동 이벤트
├── feed-generation      # 피드 생성 요청
├── vector-update        # 벡터 업데이트 트리거
├── ad-serving          # 광고 서빙 이벤트
└── content-moderation  # 콘텐츠 검수
```

**이벤트 스키마 예시:**
```json
{
  "event_type": "ai_feed_request",
  "user_id": "user_123",
  "request": {
    "prompt": "오늘 기분 좋은 영상 보여줘",
    "image_url": "gs://bucket/image.jpg",
    "context": {
      "location": "Seoul",
      "time_of_day": "evening",
      "weather": "rainy"
    }
  },
  "timestamp": "2026-02-24T14:30:00Z",
  "session_id": "sess_456"
}
```

#### (C) 피드/프로필 캐시

**저장소:** Cloud Firestore

**역할:**
- 생성 완료된 피드 저장
- 사용자 프로필 캐시
- AI 생성 결과 캐시
- 빠른 읽기 지원

**중요:**
⚠️ Firestore는 **계산/정렬 엔진이 아니라** "서빙 캐시"로만 사용

**컬렉션 구조:**
```
firestore/
├── users/
│   └── {user_id}/
│       ├── profile          # 사용자 프로필
│       └── feed_cache/      # 피드 캐시
│           └── {feed_id}
├── generated_feeds/
│   └── {feed_id}/
│       ├── content
│       ├── metadata
│       └── ads
└── campaigns/
    └── {campaign_id}
```

**문서 예시:**
```json
// users/{user_id}/feed_cache/{feed_id}
{
  "feed_id": "feed_789",
  "type": "ai_generated",
  "content": {
    "media_url": "gs://bucket/generated/video_123.mp4",
    "script": "...",
    "thumbnails": []
  },
  "ads": [
    {
      "ad_id": "ad_456",
      "placement": "inline",
      "integration_type": "story_blend"
    }
  ],
  "created_at": "2026-02-24T14:35:00Z",
  "ttl": "2026-02-25T14:35:00Z",
  "view_count": 0,
  "engagement": {}
}
```

#### (D) 벡터 DB

**초기 구성:** Cloud SQL (PostgreSQL + pgvector)

**확장 시 분리:**
- 사용자 벡터: PostgreSQL (샤딩)
- 콘텐츠/광고 벡터: Vertex AI Vector Search

**스키마 설계:**
```sql
-- 사용자 장기 벡터
CREATE TABLE user_long_term_vectors (
  user_id VARCHAR(255) PRIMARY KEY,
  vector vector(768),  -- pgvector extension
  metadata JSONB,
  updated_at TIMESTAMP,
  version INT
);

CREATE INDEX ON user_long_term_vectors
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);

-- 사용자 단기 벡터
CREATE TABLE user_short_term_vectors (
  user_id VARCHAR(255) PRIMARY KEY,
  vector vector(768),
  session_id VARCHAR(255),
  metadata JSONB,
  created_at TIMESTAMP,
  ttl TIMESTAMP  -- Time To Live
);

CREATE INDEX ON user_short_term_vectors
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);

-- 광고 벡터
CREATE TABLE ad_vectors (
  ad_id VARCHAR(255) PRIMARY KEY,
  campaign_id VARCHAR(255),
  vector vector(768),
  metadata JSONB,
  budget_remaining DECIMAL,
  targeting_rules JSONB,
  performance_score FLOAT,
  updated_at TIMESTAMP
);

CREATE INDEX ON ad_vectors
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);

-- 콘텐츠 벡터
CREATE TABLE content_vectors (
  content_id VARCHAR(255) PRIMARY KEY,
  content_type VARCHAR(50),  -- ugc, brand, editorial
  vector vector(768),
  metadata JSONB,
  popularity_score FLOAT,
  created_at TIMESTAMP
);

CREATE INDEX ON content_vectors
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);
```

### 3.2 데이터 흐름

```
사용자 행동
    │
    ├──→ BigQuery (로그 저장)
    │
    ├──→ Pub/Sub (이벤트 발행)
    │       │
    │       ├──→ 벡터 업데이트 워커
    │       │       │
    │       │       └──→ Vector DB (상태 갱신)
    │       │
    │       └──→ 피드 생성 워커
    │               │
    │               ├──→ Vector DB (검색)
    │               ├──→ AI Agent (생성)
    │               └──→ Firestore (캐시)
    │
    └──→ 실시간 스트림 분석
```

---

## 4. 벡터 DB 설계

### 4.1 벡터 계층 분리 전략

벡터는 **반드시 계층별로 분리**하여 관리합니다.

#### 4.1.1 User Long-term Vector

**의미:**
- 사용자의 가치관
- 장기 소비 성향
- 라이프 스테이지
- 인구통계학적 특성

**생성 방법:**
- BigQuery 배치 파이프라인
- 30일 ~ 90일 행동 데이터 분석
- 임베딩 모델: text-embedding-004

**업데이트 주기:**
- 하루 1~2회 배치 업데이트
- 점진적 변화 추적

**벡터 생성 로직:**
```python
# Pseudo code
def generate_long_term_vector(user_id):
    # 1. 장기 행동 데이터 수집
    behaviors = fetch_behaviors_from_bigquery(
        user_id=user_id,
        days=90
    )

    # 2. 특성 추출
    features = extract_features(behaviors)
    # - 선호 카테고리 분포
    # - 시청 시간대 패턴
    # - 콘텐츠 길이 선호도
    # - 인게이지먼트 패턴

    # 3. 텍스트 표현 생성
    profile_text = generate_profile_text(features)
    # 예: "30대 여성, 건강/웰빙 관심, 저녁 시청 선호,
    #      긴 콘텐츠 선호, 높은 공유율"

    # 4. 임베딩 생성
    vector = embedding_model.embed(profile_text)

    return vector, features
```

#### 4.1.2 User Short-term Vector

**의미:**
- 최근 행동 의도
- 세션 컨텍스트
- 현재 감정 상태
- 즉각적인 관심사

**생성 방법:**
- Pub/Sub 이벤트 기반 실시간 업데이트
- 최근 1~7일 행동 중심
- 세션 내 행동 패턴 분석

**업데이트 주기:**
- 이벤트 발생 시 즉시 업데이트
- TTL: 7일 (자동 만료)

**벡터 생성 로직:**
```python
def generate_short_term_vector(user_id, session_id):
    # 1. 최근 행동 수집
    recent_behaviors = fetch_recent_behaviors(
        user_id=user_id,
        hours=24
    )

    # 2. 세션 컨텍스트 분석
    session_context = analyze_session(session_id)
    # - 현재 시간대
    # - 디바이스 타입
    # - 위치 정보
    # - 날씨 정보

    # 3. 의도 추론
    intent_text = infer_intent(recent_behaviors, session_context)
    # 예: "저녁 휴식 중, 가벼운 엔터테인먼트 원함,
    #      모바일 시청, 짧은 콘텐츠 선호"

    # 4. 임베딩 생성
    vector = embedding_model.embed(intent_text)

    return vector, session_context
```

#### 4.1.3 Content Vector

**의미:**
- 콘텐츠 주제/카테고리
- 톤앤매너
- 정서적 특성
- 스타일적 특성

**생성 방법:**
- 콘텐츠 메타데이터 + 실제 콘텐츠 분석
- 멀티모달 임베딩 (텍스트 + 이미지 + 비디오)

**스키마:**
```python
{
  "content_id": "cnt_123",
  "vector": [0.1, 0.2, ...],  # 768-dim
  "metadata": {
    "category": "wellness",
    "subcategory": "meditation",
    "tone": "calm",
    "length": "short",
    "visual_style": "minimalist",
    "keywords": ["mindfulness", "breathing", "relaxation"]
  },
  "popularity_score": 0.85
}
```

#### 4.1.4 Ad/Product Vector

**의미:**
- 광고 타겟 의도
- 제품 특성
- 캠페인 목표
- 브랜드 톤

**생성 방법:**
- 광고 크리에이티브 분석
- 타겟팅 정보
- 제품 설명

**스키마:**
```python
{
  "ad_id": "ad_456",
  "campaign_id": "camp_789",
  "vector": [0.3, 0.4, ...],  # 768-dim
  "metadata": {
    "product_category": "health_supplement",
    "target_age": "25-40",
    "target_gender": "all",
    "tone": "scientific",
    "price_range": "premium",
    "keywords": ["immunity", "vitamin", "natural"]
  },
  "targeting_rules": {
    "min_age": 25,
    "max_age": 40,
    "interests": ["health", "wellness"],
    "exclude_recent_purchasers": true
  },
  "budget_remaining": 50000.0,
  "performance_score": 0.72,
  "bid_amount": 2.5
}
```

### 4.2 벡터 결합 전략

**중요:** 단순 평균 금지!

사용자의 최종 벡터는 **가중 결합**으로 생성합니다.

```python
def compute_final_user_vector(
    user_id: str,
    context: dict,
    feed_type: str
) -> np.ndarray:
    # 1. 벡터 로드
    long_term_vec = load_long_term_vector(user_id)
    short_term_vec = load_short_term_vector(user_id)

    # 2. 가중치 결정
    if feed_type == "ai_generated":
        # AI 피드는 현재 의도 중요
        w_short = 0.7
        w_long = 0.3
    elif context.get("time_spent_recently") > 30:
        # 오래 사용 중이면 단기 의도 반영
        w_short = 0.6
        w_long = 0.4
    else:
        # 일반 피드는 장기 선호 중요
        w_short = 0.3
        w_long = 0.7

    # 3. 컨텍스트 기반 조정
    if context.get("is_first_session_today"):
        w_long += 0.1
        w_short -= 0.1

    # 4. 정규화
    total = w_short + w_long
    w_short /= total
    w_long /= total

    # 5. 결합
    final_vector = (
        w_short * short_term_vec +
        w_long * long_term_vec
    )

    return final_vector, {
        "w_short": w_short,
        "w_long": w_long
    }
```

### 4.3 벡터 검색 최적화

#### 4.3.1 인덱스 전략

```sql
-- IVFFlat 인덱스 (초기)
CREATE INDEX idx_user_vectors ON user_long_term_vectors
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);

-- HNSW 인덱스 (고성능 필요 시)
CREATE INDEX idx_user_vectors_hnsw ON user_long_term_vectors
USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

#### 4.3.2 검색 쿼리 예시

```sql
-- Top-K 광고 후보 검색
SELECT
  ad_id,
  campaign_id,
  1 - (vector <=> $1::vector) AS similarity,
  metadata,
  budget_remaining,
  performance_score
FROM ad_vectors
WHERE
  budget_remaining > 0
  AND (metadata->>'target_age_min')::int <= $2
  AND (metadata->>'target_age_max')::int >= $3
ORDER BY vector <=> $1::vector
LIMIT 20;
```

---

## 5. AI Agent 설계

**이 시스템의 핵심. 단순 RAG가 아닙니다.**

> 💡 **상세 설계는 [AGENT_DESIGN.md](AGENT_DESIGN.md)를 참조하세요.**
> - LangGraph 기반 상태머신 구현
> - 하이브리드 검색 (Vector + Graph)
> - 광고 랭킹 4단계 프로세스
> - 브랜드 안전 장치 3중 방어
> - Vertex AI 활용 전략

### 5.1 Agent의 역할 정의

Agent는 3단계 역할을 수행합니다:

```
┌─────────────────────────────────────────┐
│  ① State Interpreter (상태 해석기)      │
│  입력: 벡터 + 프롬프트 + 이미지          │
│  출력: 감정/의도/전략 JSON              │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  ② Strategy Planner (전략 결정기)        │
│  입력: 해석 결과 + 광고 후보             │
│  출력: 광고 통합 전략 JSON              │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  ③ Creative Generator (미디어 생성기)    │
│  입력: 전략 + 광고 정보                  │
│  출력: 스크립트 + 이미지 + 영상         │
└─────────────────────────────────────────┘
```

### 5.2 단계별 상세 설계

#### 5.2.1 ① State Interpreter (상태 해석기)

**목적:** 사용자의 현재 상태와 니즈를 해석

**입력:**
- `user_vector`: 결합된 사용자 벡터
- `prompt`: 사용자 요청 ("오늘 기분 좋은 영상 보여줘")
- `image`: 업로드 이미지 (선택)
- `context`: 세션 컨텍스트

**출력 스키마:**
```json
{
  "emotional_state": {
    "primary": "seeking_relaxation",
    "secondary": "slightly_stressed",
    "energy_level": "low",
    "mood": "neutral_to_positive"
  },
  "intent": {
    "content_type": "video",
    "content_length": "short_to_medium",
    "content_tone": "uplifting",
    "engagement_type": "passive_consumption"
  },
  "persuasion_strategy": {
    "approach": "soft_recommendation",
    "tone": "friendly",
    "directness": "indirect",
    "value_proposition": "mood_improvement"
  },
  "ad_integration_preference": {
    "tolerance": "medium",
    "preferred_type": "story_blend",
    "max_ads": 1,
    "timing": "after_content"
  },
  "confidence": 0.85
}
```

**프롬프트 템플릿:**
```python
STATE_INTERPRETER_PROMPT = """
You are a user state interpreter for a personalized content platform.

User Profile Summary:
- Long-term interests: {long_term_summary}
- Recent behavior: {short_term_summary}
- Current context: {session_context}

User Request:
"{user_prompt}"

{image_analysis}

Task:
Analyze the user's current emotional state, intent, and needs.
Determine the optimal persuasion strategy and ad integration approach.

Output a JSON with:
1. emotional_state: Current emotional and energy state
2. intent: What content they're seeking
3. persuasion_strategy: How to approach this user
4. ad_integration_preference: How to integrate ads

Be specific and actionable. Consider cultural context and time of day.
"""
```

**구현 예시:**
```python
async def interpret_state(
    user_id: str,
    prompt: str,
    image: Optional[str] = None,
    context: dict = None
) -> StateInterpretation:

    # 1. 벡터 로드 및 결합
    user_vector, weights = compute_final_user_vector(
        user_id, context, "ai_generated"
    )

    # 2. 프로필 요약 생성
    long_term_summary = generate_profile_summary(
        user_id, "long_term"
    )
    short_term_summary = generate_profile_summary(
        user_id, "short_term"
    )

    # 3. 이미지 분석 (있는 경우)
    image_analysis = ""
    if image:
        image_analysis = await analyze_image(image)

    # 4. 프롬프트 구성
    prompt_text = STATE_INTERPRETER_PROMPT.format(
        long_term_summary=long_term_summary,
        short_term_summary=short_term_summary,
        session_context=json.dumps(context),
        user_prompt=prompt,
        image_analysis=image_analysis
    )

    # 5. LLM 호출
    response = await call_llm(
        model="gemini-pro",
        prompt=prompt_text,
        response_format="json"
    )

    return StateInterpretation(**response)
```

#### 5.2.2 ② Strategy Planner (전략 결정기)

**목적:** 광고 통합 전략 결정

**입력:**
- `state_interpretation`: 상태 해석 결과
- `ad_candidates`: 벡터 검색으로 찾은 광고 후보 (Top-20)
- `content_candidates`: 콘텐츠 후보

**출력 스키마:**
```json
{
  "content_strategy": {
    "primary_content_type": "short_video",
    "theme": "nature_relaxation",
    "duration": "60-90s",
    "visual_style": "cinematic",
    "audio_style": "ambient"
  },
  "ad_strategy": {
    "selected_ads": [
      {
        "ad_id": "ad_456",
        "integration_type": "story_blend",
        "placement": "inline",
        "transition": "smooth",
        "rationale": "Health supplement fits wellness theme"
      }
    ],
    "total_ads": 1,
    "revenue_potential": 3.5
  },
  "generation_plan": {
    "approach": "template_based_customization",
    "base_template": "nature_scene",
    "customizations": [
      "add_product_subtle",
      "align_color_palette"
    ],
    "estimated_cost": 0.15,
    "estimated_time": "5-8s"
  },
  "fallback_strategy": {
    "if_generation_fails": "use_curated_content",
    "if_no_suitable_ad": "show_organic_only"
  }
}
```

**전략 결정 로직:**
```python
async def plan_strategy(
    state: StateInterpretation,
    user_vector: np.ndarray
) -> StrategyPlan:

    # 1. 광고 후보 검색
    ad_candidates = await search_ad_candidates(
        user_vector=user_vector,
        limit=20
    )

    # 2. 광고 필터링 및 스코어링
    scored_ads = []
    for ad in ad_candidates:
        score = compute_ad_score(
            ad=ad,
            state=state,
            strategy="maximize_revenue_with_ux"
        )
        if score > 0.3:  # 임계값
            scored_ads.append((ad, score))

    scored_ads.sort(key=lambda x: x[1], reverse=True)

    # 3. 광고 선택 전략 결정
    if state.ad_integration_preference.tolerance == "high":
        max_ads = 2
        integration_type = "direct"
    elif state.ad_integration_preference.tolerance == "medium":
        max_ads = 1
        integration_type = "story_blend"
    else:
        max_ads = 0 if random.random() > 0.3 else 1
        integration_type = "subtle"

    selected_ads = scored_ads[:max_ads]

    # 4. 콘텐츠 전략 결정
    content_strategy = determine_content_strategy(
        state=state,
        selected_ads=[ad for ad, _ in selected_ads]
    )

    # 5. 생성 계획 수립
    generation_plan = create_generation_plan(
        content_strategy=content_strategy,
        ads=selected_ads,
        budget_limit=0.50  # $0.50 per generation
    )

    return StrategyPlan(
        content_strategy=content_strategy,
        ad_strategy={"selected_ads": selected_ads, ...},
        generation_plan=generation_plan
    )
```

**광고 스코어링 함수:**
```python
def compute_ad_score(
    ad: AdCandidate,
    state: StateInterpretation,
    strategy: str
) -> float:
    """
    광고 적합도 스코어 계산

    고려 요소:
    1. 벡터 유사도 (30%)
    2. 타겟팅 룰 매칭 (20%)
    3. 수익 잠재력 (25%)
    4. 사용자 상태 적합도 (25%)
    """

    # 1. 벡터 유사도 (이미 계산됨)
    similarity_score = ad.similarity

    # 2. 타겟팅 룰 매칭
    targeting_match = check_targeting_rules(ad, state)

    # 3. 수익 잠재력
    revenue_score = (
        ad.bid_amount *
        ad.performance_score *
        state.ad_integration_preference.tolerance_numeric
    )
    revenue_score = min(revenue_score / 10.0, 1.0)  # 정규화

    # 4. 상태 적합도
    state_fit = compute_state_fitness(ad, state)

    # 5. 가중 합산
    if strategy == "maximize_revenue_with_ux":
        weights = {
            "similarity": 0.30,
            "targeting": 0.20,
            "revenue": 0.25,
            "state_fit": 0.25
        }
    elif strategy == "maximize_ux":
        weights = {
            "similarity": 0.35,
            "targeting": 0.15,
            "revenue": 0.15,
            "state_fit": 0.35
        }
    else:  # maximize_revenue
        weights = {
            "similarity": 0.20,
            "targeting": 0.20,
            "revenue": 0.40,
            "state_fit": 0.20
        }

    final_score = (
        weights["similarity"] * similarity_score +
        weights["targeting"] * targeting_match +
        weights["revenue"] * revenue_score +
        weights["state_fit"] * state_fit
    )

    return final_score
```

#### 5.2.3 ③ Creative Generator (미디어 생성기)

**목적:** 실제 미디어 생성

**입력:**
- `strategy_plan`: 전략 계획
- `ad_details`: 선택된 광고 상세 정보

**출력:**
```json
{
  "media": {
    "video_url": "gs://bucket/generated/video_123.mp4",
    "thumbnail_url": "gs://bucket/generated/thumb_123.jpg",
    "duration": 75,
    "format": "mp4",
    "resolution": "1080x1920"
  },
  "script": {
    "narration": "Take a deep breath...",
    "scenes": [
      {
        "timestamp": "0-10s",
        "description": "Sunrise over mountains",
        "audio": "ambient_nature"
      },
      {
        "timestamp": "10-20s",
        "description": "Product placement - wellness supplement",
        "audio": "soft_music"
      }
    ]
  },
  "metadata": {
    "generation_time": 6.5,
    "cost": 0.18,
    "model_used": "imagen-3",
    "ad_integrated": true
  }
}
```

**생성 파이프라인:**
```python
async def generate_creative(
    strategy: StrategyPlan,
    state: StateInterpretation
) -> GeneratedMedia:

    # 1. 스크립트 생성
    script = await generate_script(
        content_strategy=strategy.content_strategy,
        tone=state.persuasion_strategy.tone,
        ads=strategy.ad_strategy.selected_ads
    )

    # 2. 장면별 이미지 생성
    scenes = []
    for scene in script.scenes:
        if scene.type == "ad_integration":
            # 광고 소재와 일관된 이미지 생성
            image = await generate_ad_integrated_image(
                scene=scene,
                ad=scene.ad,
                style=strategy.content_strategy.visual_style
            )
        else:
            # 일반 콘텐츠 이미지 생성
            image = await generate_image(
                prompt=scene.description,
                style=strategy.content_strategy.visual_style
            )
        scenes.append({
            "image": image,
            "duration": scene.duration,
            "narration": scene.narration
        })

    # 3. 비디오 합성
    video = await compose_video(
        scenes=scenes,
        audio_style=strategy.content_strategy.audio_style,
        transitions=strategy.ad_strategy.transitions
    )

    # 4. 썸네일 생성
    thumbnail = await generate_thumbnail(
        video=video,
        timestamp=3.0
    )

    return GeneratedMedia(
        media={"video_url": video.url, "thumbnail_url": thumbnail.url},
        script=script,
        metadata={...}
    )
```

### 5.3 왜 3단계로 분리하는가?

**실패하는 시스템의 특징:**
```python
# ❌ 안티패턴: 바로 생성
prompt = f"Create a video for: {user_request}"
video = ai_model.generate(prompt)
```

**성공하는 구조:**
```python
# ✅ 올바른 접근
state = interpret_state(user, request)      # 1. 상태 이해
strategy = plan_strategy(state, ads)         # 2. 전략 수립
media = generate_creative(strategy)          # 3. 실행
```

**이유:**
1. **디버깅 가능성**: 각 단계를 독립적으로 검증
2. **비용 최적화**: 생성 전에 전략 검증
3. **품질 보장**: 단계별 품질 게이트
4. **확장성**: 각 단계를 독립적으로 개선

---

## 6. 피드 생성 파이프라인

### 6.1 피드 유형 분리

시스템은 두 가지 피드 생성 방식을 지원합니다:

#### 6.1.1 Basic Feed (배치 생성)

**특징:**
- 주기적 배치 생성 (1시간마다)
- AI 생성 없음
- 기존 콘텐츠 큐레이션
- 저비용

**파이프라인:**
```
배치 스케줄러
    │
    ├──→ 사용자 벡터 로드
    ├──→ 콘텐츠 검색 (벡터)
    ├──→ 광고 매칭
    ├──→ 피드 구성
    └──→ Firestore 캐시
```

**구현:**
```python
async def generate_basic_feed_batch(
    user_ids: List[str]
) -> None:
    """배치 피드 생성"""

    for user_id in user_ids:
        # 1. 사용자 벡터 로드
        user_vector, _ = compute_final_user_vector(
            user_id,
            context={},
            feed_type="basic"
        )

        # 2. 콘텐츠 검색
        contents = await search_contents(
            vector=user_vector,
            limit=50,
            filters={"type": ["ugc", "editorial"]}
        )

        # 3. 광고 매칭
        ads = await match_ads_simple(
            user_vector=user_vector,
            content_count=len(contents)
        )

        # 4. 피드 구성 (콘텐츠 10개당 광고 1개)
        feed_items = []
        for i, content in enumerate(contents[:20]):
            feed_items.append({
                "type": "content",
                "content_id": content.id
            })
            if (i + 1) % 10 == 0 and ads:
                feed_items.append({
                    "type": "ad",
                    "ad_id": ads.pop(0).ad_id
                })

        # 5. Firestore 저장
        await save_feed_to_firestore(
            user_id=user_id,
            feed_items=feed_items,
            feed_type="basic",
            ttl=3600  # 1시간
        )
```

#### 6.1.2 AI Feed (온디맨드 생성)

**특징:**
- 사용자 요청 시 생성
- AI Agent 풀 파이프라인 실행
- 고비용, 고품질
- 수 초 소요 허용

**파이프라인:**
```
사용자 요청
    │
    ├──→ Pub/Sub 이벤트 발행
    │
Cloud Run 워커
    │
    ├──→ ① State Interpreter
    │       │
    │       └──→ 상태 해석 JSON
    │
    ├──→ ② Strategy Planner
    │       │
    │       ├──→ 광고 검색 (Vector DB)
    │       └──→ 전략 JSON
    │
    ├──→ ③ Creative Generator
    │       │
    │       ├──→ 스크립트 생성 (Gemini)
    │       ├──→ 이미지 생성 (Imagen)
    │       ├──→ 비디오 합성
    │       └──→ GCS 업로드
    │
    └──→ Firestore 저장
         │
         └──→ 사용자에게 알림
```

**구현:**
```python
@app.route("/generate-ai-feed", methods=["POST"])
async def generate_ai_feed_endpoint(request):
    """AI 피드 생성 엔드포인트"""

    data = request.json
    user_id = data["user_id"]
    prompt = data["prompt"]
    image = data.get("image")
    context = data.get("context", {})

    # 1. Pub/Sub로 비동기 처리 요청
    message = {
        "user_id": user_id,
        "prompt": prompt,
        "image": image,
        "context": context,
        "request_id": generate_uuid()
    }

    await pubsub.publish(
        topic="feed-generation",
        message=message
    )

    return {
        "status": "processing",
        "request_id": message["request_id"],
        "estimated_time": "5-10s"
    }


async def ai_feed_worker(message: dict):
    """AI 피드 생성 워커 (Pub/Sub 구독)"""

    try:
        user_id = message["user_id"]
        prompt = message["prompt"]
        image = message.get("image")
        context = message.get("context", {})

        # 1. 상태 해석
        state = await interpret_state(
            user_id=user_id,
            prompt=prompt,
            image=image,
            context=context
        )

        # 2. 벡터 계산
        user_vector, weights = compute_final_user_vector(
            user_id, context, "ai_generated"
        )

        # 3. 전략 수립
        strategy = await plan_strategy(
            state=state,
            user_vector=user_vector
        )

        # 4. 비용 체크
        if strategy.generation_plan.estimated_cost > 0.5:
            await notify_user(
                user_id,
                "Generation too expensive, using curated content"
            )
            # Fallback to basic feed
            return

        # 5. 미디어 생성
        media = await generate_creative(
            strategy=strategy,
            state=state
        )

        # 6. Firestore 저장
        feed_id = await save_ai_feed_to_firestore(
            user_id=user_id,
            media=media,
            strategy=strategy,
            metadata={
                "prompt": prompt,
                "generation_time": media.metadata.generation_time,
                "cost": media.metadata.cost
            }
        )

        # 7. 사용자 알림
        await notify_user(
            user_id,
            f"Your personalized content is ready: {feed_id}"
        )

        # 8. 로그 기록
        await log_to_bigquery({
            "user_id": user_id,
            "feed_id": feed_id,
            "type": "ai_generated",
            "cost": media.metadata.cost,
            "generation_time": media.metadata.generation_time,
            "timestamp": datetime.utcnow()
        })

    except Exception as e:
        logger.error(f"AI feed generation failed: {e}")
        await notify_user(
            user_id,
            "Generation failed, please try again"
        )
```

### 6.2 생성 제한 정책

**사용자당 제한:**
- 일반 사용자: 5회/일
- 프리미엄 사용자: 무제한
- 신규 사용자: 3회/일 (첫 7일)

**비용 제한:**
- 생성당 최대 비용: $0.50
- 사용자당 일일 총 비용: $2.00

**구현:**
```python
async def check_generation_quota(
    user_id: str,
    user_tier: str
) -> Tuple[bool, str]:
    """생성 쿼터 체크"""

    # Redis에서 오늘 사용 횟수 조회
    today = datetime.utcnow().date()
    key = f"generation_count:{user_id}:{today}"
    count = await redis.get(key) or 0

    # 티어별 제한
    limits = {
        "free": 5,
        "premium": 999,
        "new": 3
    }

    limit = limits.get(user_tier, 5)

    if count >= limit:
        return False, f"Daily limit reached ({limit})"

    # 비용 체크
    cost_key = f"generation_cost:{user_id}:{today}"
    total_cost = await redis.get(cost_key) or 0.0

    if total_cost >= 2.0:
        return False, "Daily cost limit reached ($2.00)"

    return True, "OK"
```

---

## 7. 광고 매칭 시스템

### 7.1 광고 선택 4단계 프로세스

광고 선택은 단순 유사도가 아니라 **"수익 + 상태 적합도" 최적화 문제**입니다.

```
┌─────────────────────────────────────────┐
│  1. 벡터 유사도 Top-K 추출               │
│     - Vector DB 검색                     │
│     - 코사인 유사도 기반                 │
│     - Top-20 추출                        │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  2. 캠페인 룰 필터링                     │
│     - 타겟팅 룰 검증                     │
│     - 예산 잔액 확인                     │
│     - 노출 빈도 제한                     │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  3. 수익 스코어 계산                     │
│     - eCPM 계산                          │
│     - 과거 성과 반영                     │
│     - 입찰가 가중치                      │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  4. 전략 적합도 평가                     │
│     - 사용자 상태 적합도                 │
│     - 콘텐츠 통합 자연스러움             │
│     - 최종 순위 결정                     │
└─────────────────────────────────────────┘
```

### 7.2 단계별 구현

#### 7.2.1 Step 1: 벡터 유사도 검색

```python
async def search_ad_candidates(
    user_vector: np.ndarray,
    limit: int = 20
) -> List[AdCandidate]:
    """벡터 유사도 기반 광고 후보 검색"""

    query = """
        SELECT
            ad_id,
            campaign_id,
            vector,
            metadata,
            budget_remaining,
            performance_score,
            bid_amount,
            1 - (vector <=> $1::vector) AS similarity
        FROM ad_vectors
        WHERE budget_remaining > 0
        ORDER BY vector <=> $1::vector
        LIMIT $2
    """

    results = await db.execute(
        query,
        user_vector.tolist(),
        limit
    )

    return [AdCandidate(**row) for row in results]
```

#### 7.2.2 Step 2: 캠페인 룰 필터링

```python
def filter_by_campaign_rules(
    candidates: List[AdCandidate],
    user_profile: UserProfile,
    recent_impressions: List[str]
) -> List[AdCandidate]:
    """캠페인 타겟팅 룰 기반 필터링"""

    filtered = []

    for ad in candidates:
        rules = ad.targeting_rules

        # 1. 인구통계 필터
        if not check_demographic_match(rules, user_profile):
            continue

        # 2. 관심사 필터
        if not check_interest_match(rules, user_profile):
            continue

        # 3. 노출 빈도 제한
        if ad.ad_id in recent_impressions:
            continue

        # 4. 시간대 타겟팅
        if not check_time_targeting(rules):
            continue

        # 5. 위치 타겟팅
        if not check_geo_targeting(rules, user_profile.location):
            continue

        filtered.append(ad)

    return filtered


def check_demographic_match(
    rules: dict,
    profile: UserProfile
) -> bool:
    """인구통계 매칭"""

    # 나이
    if "age_range" in rules:
        min_age, max_age = rules["age_range"]
        if not (min_age <= profile.age <= max_age):
            return False

    # 성별
    if "gender" in rules:
        if rules["gender"] != "all" and rules["gender"] != profile.gender:
            return False

    # 지역
    if "countries" in rules:
        if profile.country not in rules["countries"]:
            return False

    return True


def check_interest_match(
    rules: dict,
    profile: UserProfile
) -> bool:
    """관심사 매칭"""

    if "required_interests" not in rules:
        return True

    required = set(rules["required_interests"])
    user_interests = set(profile.interests)

    # 최소 1개 이상 매칭
    return len(required & user_interests) > 0
```

#### 7.2.3 Step 3: 수익 스코어 계산

```python
def compute_revenue_score(
    ad: AdCandidate,
    context: dict
) -> float:
    """수익 스코어 계산 (eCPM 기반)"""

    # 1. 기본 입찰가
    base_bid = ad.bid_amount

    # 2. 과거 성과 반영
    performance_multiplier = ad.performance_score
    # performance_score = CTR * CVR * 품질점수

    # 3. 예산 압박도 (마감 임박 시 높은 가중치)
    budget_pressure = compute_budget_pressure(ad)

    # 4. 시간대 가중치
    time_multiplier = get_time_of_day_multiplier(
        context.get("time_of_day")
    )

    # 5. eCPM 계산
    ecpm = (
        base_bid *
        performance_multiplier *
        (1 + budget_pressure * 0.2) *
        time_multiplier
    )

    return ecpm


def compute_budget_pressure(ad: AdCandidate) -> float:
    """예산 압박도 계산"""

    # 일일 예산 대비 남은 비율
    daily_budget = ad.metadata.get("daily_budget", 1000)
    remaining_ratio = ad.budget_remaining / daily_budget

    # 남은 시간 (오늘 자정까지)
    now = datetime.now()
    midnight = now.replace(hour=23, minute=59, second=59)
    hours_remaining = (midnight - now).total_seconds() / 3600

    # 압박도: 예산이 많이 남았는데 시간이 얼마 없으면 높음
    if hours_remaining < 2:
        pressure = remaining_ratio  # 0~1
    else:
        pressure = 0

    return pressure
```

#### 7.2.4 Step 4: 전략 적합도 평가

```python
def compute_strategy_fitness(
    ad: AdCandidate,
    state: StateInterpretation,
    content_strategy: ContentStrategy
) -> float:
    """전략 적합도 평가"""

    scores = []

    # 1. 감정 상태 적합도
    emotional_fit = compute_emotional_fitness(
        ad.metadata.get("emotional_tone"),
        state.emotional_state
    )
    scores.append(("emotional", emotional_fit, 0.3))

    # 2. 콘텐츠 톤 일관성
    tone_consistency = compute_tone_consistency(
        ad.metadata.get("brand_tone"),
        content_strategy.tone
    )
    scores.append(("tone", tone_consistency, 0.25))

    # 3. 통합 자연스러움
    integration_naturalness = compute_integration_score(
        ad.category,
        content_strategy.theme,
        state.ad_integration_preference.preferred_type
    )
    scores.append(("integration", integration_naturalness, 0.25))

    # 4. 타이밍 적합도
    timing_fit = compute_timing_fitness(
        ad.metadata.get("optimal_timing"),
        state.intent.engagement_type
    )
    scores.append(("timing", timing_fit, 0.2))

    # 가중 평균
    final_score = sum(score * weight for _, score, weight in scores)

    return final_score


def compute_emotional_fitness(
    ad_tone: str,
    user_state: dict
) -> float:
    """감정 상태 적합도"""

    # 매핑 테이블
    compatibility_matrix = {
        ("seeking_relaxation", "calm"): 1.0,
        ("seeking_relaxation", "energetic"): 0.3,
        ("seeking_excitement", "energetic"): 1.0,
        ("seeking_excitement", "calm"): 0.4,
        ("stressed", "calm"): 0.9,
        ("stressed", "urgent"): 0.2,
        # ... 더 많은 조합
    }

    user_emotion = user_state.get("primary")
    key = (user_emotion, ad_tone)

    return compatibility_matrix.get(key, 0.5)
```

### 7.3 최종 광고 선택 및 순위

```python
async def select_final_ads(
    candidates: List[AdCandidate],
    state: StateInterpretation,
    content_strategy: ContentStrategy,
    max_ads: int = 2
) -> List[SelectedAd]:
    """최종 광고 선택"""

    scored_ads = []

    for ad in candidates:
        # 수익 스코어
        revenue_score = compute_revenue_score(ad, state.context)

        # 전략 적합도
        fitness_score = compute_strategy_fitness(
            ad, state, content_strategy
        )

        # 최종 스코어 (수익 60%, 적합도 40%)
        final_score = (
            0.6 * normalize(revenue_score, 0, 10) +
            0.4 * fitness_score
        )

        scored_ads.append({
            "ad": ad,
            "revenue_score": revenue_score,
            "fitness_score": fitness_score,
            "final_score": final_score
        })

    # 정렬
    scored_ads.sort(key=lambda x: x["final_score"], reverse=True)

    # Top-N 선택
    selected = scored_ads[:max_ads]

    return [
        SelectedAd(
            ad_id=item["ad"].ad_id,
            score=item["final_score"],
            revenue=item["revenue_score"],
            fitness=item["fitness_score"],
            rationale=generate_rationale(item)
        )
        for item in selected
    ]
```

### 7.4 광고 통합 방식

선택된 광고를 콘텐츠에 통합하는 3가지 방식:

#### 방식 1: Story Blend (스토리 혼합)

광고가 스토리의 자연스러운 일부가 되도록 통합

```python
# 예시: 명상 콘텐츠 + 건강 보조제 광고
script = """
장면 1: 아침 햇살이 창문으로 들어옵니다
나레이션: "새로운 하루를 시작하는 당신에게"

장면 2: 요가 매트 위에서 스트레칭
나레이션: "몸과 마음의 균형을 찾는 시간"

장면 3: [광고 통합] 건강 보조제가 테이블 위에
나레이션: "건강한 습관과 함께하는 비타민"

장면 4: 명상하는 모습
나레이션: "오늘도 활기찬 하루를 시작하세요"
"""
```

#### 방식 2: Inline (인라인 배치)

콘텐츠와 광고를 명확히 구분하되, 자연스럽게 전환

```python
# 예시: 여행 콘텐츠 + 항공권 광고
structure = [
    {"type": "content", "duration": 30, "desc": "파리 여행 영상"},
    {"type": "transition", "duration": 2, "desc": "부드러운 전환"},
    {"type": "ad", "duration": 6, "desc": "항공권 프로모션"},
    {"type": "transition", "duration": 2, "desc": "부드러운 전환"},
    {"type": "content", "duration": 30, "desc": "파리 여행 영상 계속"}
]
```

#### 방식 3: Subtle (은은한 배치)

광고를 배경 요소로 자연스럽게 노출

```python
# 예시: 요리 영상 + 주방 용품 광고
# 광고 제품이 영상 배경에 자연스럽게 배치
placement = {
    "type": "product_placement",
    "visibility": "background",
    "duration": "throughout",
    "prominence": "subtle"
}
```

---

## 8. 확장 전략

### 8.1 단계별 확장 로드맵

#### Phase 1: MVP (0-10K users)

| 영역 | 솔루션 | 비용 |
|------|--------|------|
| 사용자 벡터 | PostgreSQL (pgvector) | ~$100/월 |
| 콘텐츠 벡터 | PostgreSQL (pgvector) | ~$100/월 |
| 피드 저장 | Firestore | ~$50/월 |
| 생성 워커 | Cloud Run (단일 리전) | ~$200/월 |
| LLM 비용 | Gemini API | ~$500/월 |
| 이미지 생성 | Imagen API | ~$300/월 |
| **총계** | | **~$1,250/월** |

#### Phase 2: 성장기 (10K-100K users)

| 영역 | 변경사항 | 비용 |
|------|----------|------|
| 사용자 벡터 | PostgreSQL + Read Replicas | ~$500/월 |
| 콘텐츠 벡터 | Vertex Vector Search 전환 | ~$400/월 |
| 피드 저장 | Firestore (멀티 리전) | ~$300/월 |
| 생성 워커 | Cloud Run (3개 리전) | ~$800/월 |
| LLM 비용 | Gemini API (배치 할인) | ~$2,000/월 |
| 이미지 생성 | Imagen API (볼륨 할인) | ~$1,500/월 |
| **총계** | | **~$5,500/월** |

#### Phase 3: 확장기 (100K-1M users)

| 영역 | 변경사항 | 비용 |
|------|----------|------|
| 사용자 벡터 | PostgreSQL Sharding (지역별) | ~$2,000/월 |
| 콘텐츠 벡터 | Vertex Vector Search (확장) | ~$1,500/월 |
| 피드 저장 | Firestore (글로벌 분산) | ~$1,500/월 |
| 생성 워커 | Cloud Run (10개 리전) | ~$3,000/월 |
| LLM 비용 | Gemini API + 온프레미스 혼합 | ~$8,000/월 |
| 이미지 생성 | Imagen + Stable Diffusion 혼합 | ~$5,000/월 |
| CDN | Cloud CDN | ~$1,000/월 |
| **총계** | | **~$22,000/월** |

### 8.2 기술 스택 전환 계획

#### 8.2.1 Vector DB 확장

```
MVP (0-10K)
    PostgreSQL (pgvector)
    단일 인스턴스
    └─→ 성능: ~1K QPS

성장기 (10K-100K)
    PostgreSQL (Read Replicas) + Vertex Vector Search
    사용자 벡터: PostgreSQL (높은 쓰기)
    콘텐츠 벡터: Vertex (높은 읽기)
    └─→ 성능: ~10K QPS

확장기 (100K-1M)
    PostgreSQL (샤딩) + Vertex Vector Search
    지역별 샤딩
    글로벌 라우팅
    └─→ 성능: ~100K QPS
```

**마이그레이션 전략:**
```python
async def migrate_to_vertex_vector_search():
    """콘텐츠 벡터를 Vertex로 마이그레이션"""

    # 1. Vertex 인덱스 생성
    index = await vertex_ai.create_index(
        display_name="content-vectors",
        dimensions=768,
        distance_type="COSINE"
    )

    # 2. 배치로 데이터 마이그레이션
    batch_size = 1000
    offset = 0

    while True:
        # PostgreSQL에서 읽기
        vectors = await db.execute("""
            SELECT content_id, vector, metadata
            FROM content_vectors
            ORDER BY content_id
            LIMIT $1 OFFSET $2
        """, batch_size, offset)

        if not vectors:
            break

        # Vertex에 쓰기
        await vertex_ai.upsert_datapoints(
            index=index,
            datapoints=[
                {
                    "id": v["content_id"],
                    "feature_vector": v["vector"],
                    "restricts": v["metadata"]
                }
                for v in vectors
            ]
        )

        offset += batch_size

    # 3. 검증 후 트래픽 전환
    # 4. PostgreSQL 데이터 보관 (백업)
```

#### 8.2.2 피드 저장소 확장

```python
# Firestore 리전별 분산 전략

# 사용자 위치 기반 리전 매핑
REGION_MAPPING = {
    "NA": "us-central1",
    "EU": "europe-west1",
    "ASIA": "asia-northeast1"
}

async def save_feed_to_firestore(
    user_id: str,
    feed_data: dict
):
    # 사용자 지역 확인
    user_region = await get_user_region(user_id)
    firestore_region = REGION_MAPPING[user_region]

    # 지역별 Firestore 클라이언트
    db = get_firestore_client(firestore_region)

    # 저장
    await db.collection("feeds").document(user_id).set(feed_data)
```

#### 8.2.3 생성 워커 확장

```
MVP
    Cloud Run (us-central1)
    단일 리전
    └─→ 레이턴시: ~5-10s

성장기
    Cloud Run (us, eu, asia)
    3개 리전
    지역별 라우팅
    └─→ 레이턴시: ~3-6s

확장기
    Cloud Run (10개 리전)
    엣지 컴퓨팅
    로컬 캐싱
    └─→ 레이턴시: ~2-4s
```

### 8.3 비용 최적화 전략

#### 8.3.1 AI 생성 비용 최적화

```python
# 1. 템플릿 기반 생성 (저비용)
async def generate_with_template(
    template_id: str,
    customizations: dict
) -> GeneratedMedia:
    """
    템플릿 기반 생성 (비용 ~$0.05)
    전체 생성 대비 90% 비용 절감
    """
    template = load_template(template_id)

    # 텍스트만 커스터마이징
    customized = customize_template(
        template,
        customizations
    )

    return customized


# 2. 배치 생성 (중간 비용)
async def generate_batch_content(
    requests: List[GenerationRequest]
) -> List[GeneratedMedia]:
    """
    배치 생성 (비용 ~$0.15 per item)
    30% 비용 절감
    """
    # Gemini Batch API 사용
    results = await gemini.batch_generate(requests)
    return results


# 3. 온디맨드 생성 (고비용)
async def generate_custom_content(
    request: GenerationRequest
) -> GeneratedMedia:
    """
    완전 커스텀 생성 (비용 ~$0.50)
    최고 품질
    """
    # 풀 파이프라인
    result = await full_generation_pipeline(request)
    return result


# 사용자 티어별 생성 방식 선택
def select_generation_method(user_tier: str):
    if user_tier == "free":
        return generate_with_template
    elif user_tier == "standard":
        return generate_batch_content
    else:  # premium
        return generate_custom_content
```

#### 8.3.2 캐싱 전략

```python
# 3-tier 캐싱

# L1: Redis (핫 데이터)
async def get_feed_from_l1(user_id: str):
    key = f"feed:hot:{user_id}"
    return await redis.get(key)


# L2: Firestore (웜 데이터)
async def get_feed_from_l2(user_id: str):
    doc = await firestore.collection("feeds").document(user_id).get()
    return doc.to_dict()


# L3: Cloud Storage (콜드 데이터)
async def get_feed_from_l3(user_id: str):
    blob = storage_client.bucket("feeds-archive").blob(f"{user_id}.json")
    return json.loads(blob.download_as_string())


# 계층적 조회
async def get_feed(user_id: str):
    # L1 시도
    feed = await get_feed_from_l1(user_id)
    if feed:
        return feed

    # L2 시도
    feed = await get_feed_from_l2(user_id)
    if feed:
        # L1에 캐싱
        await redis.set(f"feed:hot:{user_id}", feed, ex=300)
        return feed

    # L3 시도
    feed = await get_feed_from_l3(user_id)
    if feed:
        # L2에 캐싱
        await firestore.collection("feeds").document(user_id).set(feed)
        return feed

    # 없으면 생성
    return await generate_new_feed(user_id)
```

### 8.4 글로벌 확장 고려사항

#### 8.4.1 다국어 지원

```python
# 벡터는 언어 독립적
# 프롬프트와 생성물만 번역

LANGUAGE_MODELS = {
    "en": "gemini-pro",
    "ko": "gemini-pro-korean",
    "ja": "gemini-pro-japanese",
    # ...
}

async def generate_localized_content(
    strategy: StrategyPlan,
    language: str
) -> GeneratedMedia:
    model = LANGUAGE_MODELS[language]

    # 프롬프트 번역
    localized_prompt = await translate_prompt(
        strategy.content_strategy,
        target_language=language
    )

    # 생성
    media = await generate_with_model(
        model=model,
        prompt=localized_prompt
    )

    return media
```

#### 8.4.2 데이터 주권 (GDPR, 개인정보)

```python
# 지역별 데이터 격리

DATA_RESIDENCY = {
    "EU": {
        "vector_db": "europe-west1",
        "storage": "eu-west1",
        "processing": "europe-west1"
    },
    "US": {
        "vector_db": "us-central1",
        "storage": "us-west1",
        "processing": "us-central1"
    }
}

async def process_with_residency(
    user_id: str,
    data: dict
):
    user_region = await get_user_legal_region(user_id)
    residency = DATA_RESIDENCY[user_region]

    # 해당 지역에서만 처리
    result = await process_in_region(
        data,
        region=residency["processing"]
    )

    return result
```

---

## 9. 구현 로드맵

### 9.1 설계 순서 (권장)

이 순서가 가장 안정적이고 리스크가 낮습니다:

```
Week 1-2: 데이터 플로우 설계
    ├─→ BigQuery 스키마 정의
    ├─→ Pub/Sub 토픽 구조
    ├─→ Firestore 컬렉션 설계
    └─→ 데이터 파이프라인 정의

Week 3-4: 벡터 스키마 설계
    ├─→ 벡터 차원 결정
    ├─→ 메타데이터 구조
    ├─→ 인덱스 전략
    └─→ 업데이트 정책

Week 5-6: 광고 매칭 로직 설계
    ├─→ 스코어링 함수 정의
    ├─→ 필터링 룰 설계
    ├─→ 수익 모델 구현
    └─→ A/B 테스트 프레임워크

Week 7-8: Agent 단계 정의
    ├─→ State Interpreter 프롬프트
    ├─→ Strategy Planner 로직
    ├─→ Creative Generator 템플릿
    └─→ 품질 검증 로직

Week 9-10: 생성 템플릿 설계
    ├─→ 콘텐츠 템플릿 라이브러리
    ├─→ 광고 통합 패턴
    ├─→ 스타일 가이드
    └─→ 안전 필터

Week 11-12: 비용 모델링
    ├─→ 사용자당 비용 추정
    ├─→ 수익 예측
    ├─→ ROI 분석
    └─→ 최적화 전략

Week 13-14: 글로벌 확장 전략
    ├─→ 다국어 지원
    ├─→ 데이터 주권
    ├─→ 리전별 배포
    └─→ 성능 최적화
```

### 9.2 개발 우선순위

#### P0 (필수, MVP에 포함)

1. **기본 데이터 파이프라인**
   - BigQuery 로그 수집
   - Pub/Sub 이벤트 스트림
   - Firestore 피드 캐시

2. **벡터 기본 기능**
   - PostgreSQL + pgvector 설정
   - 사용자 장기 벡터 생성
   - 콘텐츠 벡터 생성

3. **AI Agent 기본**
   - State Interpreter (기본 버전)
   - 템플릿 기반 생성

4. **기본 피드**
   - 배치 피드 생성
   - 간단한 광고 매칭

#### P1 (중요, 빠른 추가)

1. **AI 온디맨드 생성**
   - 전체 3단계 Agent
   - 커스텀 미디어 생성

2. **고급 광고 매칭**
   - 4단계 광고 선택
   - 수익 최적화

3. **사용자 단기 벡터**
   - 실시간 업데이트
   - 세션 컨텍스트

#### P2 (나중에)

1. **성능 최적화**
   - 캐싱 레이어
   - 벡터 검색 최적화

2. **글로벌 확장**
   - 다국어 지원
   - 리전별 배포

### 9.3 마일스톤

#### Milestone 1: MVP (Month 1-2)
- [ ] 데이터 파이프라인 구축
- [ ] 기본 벡터 시스템
- [ ] 배치 피드 생성
- [ ] 간단한 광고 매칭
- **Goal:** 100명 테스트 유저

#### Milestone 2: AI 기능 (Month 3-4)
- [ ] AI Agent 전체 구현
- [ ] 온디맨드 생성
- [ ] 광고 통합 3가지 방식
- **Goal:** 1,000명 베타 유저

#### Milestone 3: 최적화 (Month 5-6)
- [ ] 성능 최적화
- [ ] 비용 최적화
- [ ] 품질 개선
- **Goal:** 10,000명 유저

#### Milestone 4: 확장 (Month 7-12)
- [ ] 글로벌 배포
- [ ] 다국어 지원
- [ ] 고급 기능
- **Goal:** 100,000명 유저

---

## 10. 부록

### 10.1 핵심 메트릭

#### 비즈니스 메트릭
- **DAU/MAU**: 일일/월간 활성 사용자
- **생성 요청률**: DAU 대비 AI 생성 요청 비율
- **광고 CTR**: 광고 클릭률
- **eCPM**: 1,000회 노출당 수익
- **ARPU**: 사용자당 평균 수익

#### 기술 메트릭
- **생성 레이턴시**: P50, P95, P99
- **생성 성공률**: 성공 / 전체 요청
- **벡터 검색 속도**: QPS, 레이턴시
- **캐시 히트율**: Redis, Firestore

#### 품질 메트릭
- **사용자 만족도**: AI 생성 콘텐츠 평점
- **광고 통합 자연스러움**: 사용자 피드백
- **콘텐츠 안전성**: 필터링 성공률

### 10.2 참고 아키텍처 다이어그램

```
사용자 행동 흐름:

User App
    │
    ├──→ [View Content] ──→ Firestore (캐시 조회)
    │                           │
    │                           └──→ [Cache Miss]
    │                                   │
    │                                   └──→ Pub/Sub (생성 요청)
    │                                           │
    │                                           └──→ Cloud Run Worker
    │                                                   │
    │                                                   ├──→ Vector DB (검색)
    │                                                   ├──→ AI Agent (생성)
    │                                                   └──→ Firestore (저장)
    │
    ├──→ [Request AI Feed] ──→ API Gateway
    │                              │
    │                              └──→ Pub/Sub (즉시)
    │                                      │
    │                                      └──→ Cloud Run Worker
    │
    └──→ [Engagement] ──→ Pub/Sub (이벤트)
                              │
                              ├──→ BigQuery (로그)
                              └──→ Vector Update Worker
                                      │
                                      └──→ Vector DB (업데이트)
```

### 10.3 기술 스택 요약

| 레이어 | 기술 | 용도 |
|--------|------|------|
| **Frontend** | React Native / Flutter | 모바일 앱 |
| **API Gateway** | Cloud Run / API Gateway | API 엔드포인트 |
| **Orchestration** | Cloud Run | 피드 오케스트레이션 |
| **AI Agent** | Gemini Pro, Claude | 상태 해석, 전략 수립 |
| **Generation** | Imagen, Veo 2 | 이미지, 비디오 생성 |
| **Vector DB** | PostgreSQL (pgvector) | 벡터 저장 (초기) |
| **Vector DB** | Vertex AI Vector Search | 벡터 저장 (확장) |
| **Cache** | Firestore | 피드 서빙 캐시 |
| **Stream** | Pub/Sub | 이벤트 스트림 |
| **Analytics** | BigQuery | 로그 분석 |
| **Storage** | Cloud Storage | 미디어 저장 |
| **CDN** | Cloud CDN | 미디어 배포 |

### 10.4 보안 고려사항

1. **콘텐츠 안전성**
   - AI 생성 결과 필터링
   - 부적절한 콘텐츠 차단
   - 사용자 신고 시스템

2. **개인정보 보호**
   - 벡터 비식별화
   - GDPR 준수
   - 데이터 주권

3. **광고 정책**
   - 투명한 광고 표시
   - 부적절한 광고 차단
   - 사용자 차단 기능

---

## 결론

이 아키텍처는:

1. **사용자 상태 중심**: 콘텐츠를 찾는 것이 아니라 상태를 이해하고 생성
2. **비동기 중심**: 확장 가능한 이벤트 기반 아키텍처
3. **AI 네이티브**: 추천이 아니라 생성
4. **수익 최적화**: 광고를 자연스럽게 통합
5. **글로벌 확장 가능**: 처음부터 확장성 고려

**핵심 철학:**
> 벡터 검색은 도구일 뿐, 진짜 가치는 사용자 상태를 이해하고 최적의 경험을 **생성**하는 데 있습니다.

---

**문서 버전:** 1.0
**최종 수정일:** 2026-02-24
**작성자:** Architecture Team
