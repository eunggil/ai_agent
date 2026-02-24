# 실제 구현 로드맵

> 어떤 순서로 무엇을 만들어야 하는가?

## 목차

1. [구현 철학](#1-구현-철학)
2. [Phase 0: 인프라 기초](#2-phase-0-인프라-기초-1주)
3. [Phase 1: 데이터 파이프라인 MVP](#3-phase-1-데이터-파이프라인-mvp-2주)
4. [Phase 2: 벡터 검색 기본](#4-phase-2-벡터-검색-기본-2주)
5. [Phase 3: 간단한 에이전트](#5-phase-3-간단한-에이전트-2주)
6. [Phase 4: 광고 매칭 기본](#6-phase-4-광고-매칭-기본-2주)
7. [Phase 5: PiMS & 온톨로지](#7-phase-5-pims--온톨로지-3주)
8. [Phase 6: 고급 에이전트](#8-phase-6-고급-에이전트-3주)
9. [Phase 7: 프로덕션 준비](#9-phase-7-프로덕션-준비-2주)
10. [병렬 작업 가능 항목](#10-병렬-작업-가능-항목)

---

## 1. 구현 철학

### 핵심 원칙

1. **가장 위험한 것부터 검증**
   - "이게 정말 될까?" → 먼저 증명
   - LLM 기반 생성, 벡터 검색, 그래프 제약이 실제로 작동하는지

2. **End-to-End를 빨리**
   - 전체 파이프라인의 간단한 버전을 먼저 완성
   - 각 단계를 고도화하는 건 나중에

3. **데이터부터**
   - 좋은 AI는 좋은 데이터에서 나옴
   - 토큰화/정규화가 안 되면 아무것도 안 됨

4. **측정 가능하게**
   - 매 단계마다 성공 지표 정의
   - 로그/트레이스를 처음부터

---

## 2. Phase 0: 인프라 기초 (1주)

### 목표
"개발 환경에서 코드를 실행할 수 있는 상태"

### 작업 목록

#### 2.1 GCP 프로젝트 설정
```bash
# 프로젝트 생성
gcloud projects create addeep-ai-agent-dev

# API 활성화
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

#### 2.2 로컬 개발 환경
```bash
# 저장소 구조 생성
mkdir -p src/{api,core,data,workers,models,utils}
mkdir -p tests/{unit,integration}
mkdir -p infrastructure/{terraform,docker}

# Python 환경
python -m venv venv
source venv/bin/activate

# 기본 의존성
pip install \
  fastapi uvicorn \
  sqlalchemy psycopg2-binary \
  google-cloud-aiplatform \
  google-cloud-pubsub \
  google-cloud-firestore \
  google-cloud-bigquery \
  langgraph langchain \
  numpy pandas
```

#### 2.3 PostgreSQL + pgvector (로컬)
```bash
# Docker Compose로 시작
docker-compose up -d postgres redis
```

**docker-compose.yml**
```yaml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: addeep
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

#### 2.4 성공 기준
- [ ] GCP 프로젝트 생성 완료
- [ ] 로컬에서 Python 코드 실행 가능
- [ ] PostgreSQL 연결 확인
- [ ] Redis 연결 확인

---

## 3. Phase 1: 데이터 파이프라인 MVP (2주)

### 목표
"데이터가 쌓이고 흐르는 것 확인"

### 우선순위: 🔥 최우선

**이유:**
- 데이터 없으면 아무것도 못 함
- 파이프라인 검증이 가장 오래 걸림
- 병렬 작업의 기반

### 작업 목록

#### 3.1 BigQuery 스키마 생성
```sql
-- user_behavior_logs
CREATE TABLE `addeep-dev.analytics.user_behavior_logs` (
  event_id STRING NOT NULL,
  user_id STRING NOT NULL,
  event_type STRING NOT NULL,
  content_id STRING,
  timestamp TIMESTAMP NOT NULL,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id;

-- ai_generation_logs
CREATE TABLE `addeep-dev.analytics.ai_generation_logs` (
  generation_id STRING NOT NULL,
  user_id STRING NOT NULL,
  status STRING NOT NULL,
  cost_usd FLOAT64,
  generation_time_seconds FLOAT64,
  timestamp TIMESTAMP NOT NULL
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id;
```

#### 3.2 Pub/Sub 토픽 생성
```python
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()

topics = [
    'user-events',
    'feed-generation',
    'vector-update',
    'ad-serving'
]

for topic_name in topics:
    topic_path = publisher.topic_path('addeep-dev', topic_name)
    publisher.create_topic(request={"name": topic_path})
```

#### 3.3 이벤트 Publisher (간단한 버전)
```python
# src/data/pubsub/publisher.py

from google.cloud import pubsub_v1
import json
from typing import Dict, Any

class EventPublisher:
    def __init__(self, project_id: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.project_id = project_id

    async def publish_user_event(self, event: Dict[str, Any]):
        """사용자 행동 이벤트 발행"""
        topic_path = self.publisher.topic_path(
            self.project_id,
            'user-events'
        )

        data = json.dumps(event).encode('utf-8')
        future = self.publisher.publish(topic_path, data)

        return future.result()  # 동기 대기 (개발 단계)

# 테스트
if __name__ == "__main__":
    publisher = EventPublisher("addeep-dev")

    event = {
        "event_id": "evt_001",
        "user_id": "user_123",
        "event_type": "view",
        "content_id": "cnt_456",
        "timestamp": "2026-02-24T10:00:00Z"
    }

    message_id = publisher.publish_user_event(event)
    print(f"Published: {message_id}")
```

#### 3.4 간단한 Subscriber (BigQuery로 저장)
```python
# src/workers/bigquery_sink.py

from google.cloud import pubsub_v1, bigquery
import json

def callback(message):
    """메시지를 BigQuery에 저장"""
    data = json.loads(message.data.decode('utf-8'))

    client = bigquery.Client()
    table_id = "addeep-dev.analytics.user_behavior_logs"

    errors = client.insert_rows_json(table_id, [data])

    if not errors:
        message.ack()
    else:
        print(f"Errors: {errors}")
        message.nack()

# Subscriber 시작
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(
    'addeep-dev',
    'user-events-to-bigquery'
)

streaming_pull_future = subscriber.subscribe(
    subscription_path,
    callback=callback
)

print("Listening for messages...")
streaming_pull_future.result()
```

#### 3.5 성공 기준
- [ ] 이벤트 발행 → Pub/Sub → BigQuery 흐름 확인
- [ ] BigQuery에서 데이터 조회 가능
- [ ] 최소 100개 테스트 이벤트 정상 처리

---

## 4. Phase 2: 벡터 검색 기본 (2주)

### 목표
"유사도 검색이 작동하는지 확인"

### 우선순위: 🔥 최우선

**이유:**
- 하이브리드 검색의 핵심
- 의외로 까다로움 (임베딩 품질, 검색 속도)

### 작업 목록

#### 4.1 Vector DB 스키마 생성
```sql
-- PostgreSQL + pgvector

-- pgvector extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 콘텐츠 벡터
CREATE TABLE content_vectors (
  content_id VARCHAR(255) PRIMARY KEY,
  content_type VARCHAR(50),
  vector vector(768),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 (IVFFlat)
CREATE INDEX idx_content_vectors_ivfflat
ON content_vectors
USING ivfflat (vector vector_cosine_ops)
WITH (lists = 100);
```

#### 4.2 간단한 임베딩 생성기
```python
# src/core/vector/embedder.py

from google.cloud import aiplatform
from typing import List
import numpy as np

class TextEmbedder:
    def __init__(self):
        aiplatform.init(
            project="addeep-dev",
            location="us-central1"
        )
        self.model = aiplatform.TextEmbeddingModel.from_pretrained(
            "text-embedding-004"
        )

    def embed(self, texts: List[str]) -> List[np.ndarray]:
        """텍스트를 임베딩으로 변환"""
        embeddings = self.model.get_embeddings(texts)
        return [np.array(emb.values) for emb in embeddings]

# 테스트
if __name__ == "__main__":
    embedder = TextEmbedder()

    texts = [
        "오늘 날씨가 좋네요",
        "립스틱 추천해주세요",
        "편안한 옷 찾아요"
    ]

    vectors = embedder.embed(texts)
    print(f"Generated {len(vectors)} embeddings")
    print(f"Dimension: {vectors[0].shape}")
```

#### 4.3 벡터 저장 및 검색
```python
# src/core/vector/search.py

import psycopg2
import numpy as np
from typing import List, Tuple

class VectorSearch:
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)

    def insert(self, content_id: str, vector: np.ndarray, metadata: dict):
        """벡터 저장"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO content_vectors (content_id, vector, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (content_id) DO UPDATE
                SET vector = EXCLUDED.vector, metadata = EXCLUDED.metadata
                """,
                (content_id, vector.tolist(), json.dumps(metadata))
            )
        self.conn.commit()

    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple]:
        """유사도 검색"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    content_id,
                    metadata,
                    1 - (vector <=> %s::vector) AS similarity
                FROM content_vectors
                ORDER BY vector <=> %s::vector
                LIMIT %s
                """,
                (query_vector.tolist(), query_vector.tolist(), k)
            )
            return cur.fetchall()

# 테스트
if __name__ == "__main__":
    search = VectorSearch("postgresql://dev:devpass@localhost/addeep")

    # 샘플 데이터 삽입
    embedder = TextEmbedder()

    contents = [
        ("cnt_1", "립스틱 추천", {"category": "cosmetic"}),
        ("cnt_2", "티셔츠 추천", {"category": "fashion"}),
        ("cnt_3", "반지 추천", {"category": "jewelry"}),
    ]

    for content_id, text, metadata in contents:
        vector = embedder.embed([text])[0]
        search.insert(content_id, vector, metadata)

    # 검색 테스트
    query_text = "화장품 추천"
    query_vector = embedder.embed([query_text])[0]

    results = search.search(query_vector, k=3)
    for content_id, metadata, similarity in results:
        print(f"{content_id}: {similarity:.3f}")
```

#### 4.4 성공 기준
- [ ] 임베딩 생성 성공
- [ ] 벡터 저장 성공
- [ ] 유사도 검색 결과가 의미적으로 맞음
- [ ] 1000개 벡터 기준 검색 속도 < 100ms

---

## 5. Phase 3: 간단한 에이전트 (2주)

### 목표
"LangGraph로 상태머신을 만들고 LLM이 결정하게 하기"

### 우선순위: 🔥 최우선

**이유:**
- 에이전트가 핵심 차별점
- 복잡도 높아서 일찍 시작

### 작업 목록

#### 5.1 간단한 2-노드 그래프 (Hello World)
```python
# src/core/ai_agent/simple_agent.py

from langgraph.graph import StateGraph, END
from typing import TypedDict
from google.cloud import aiplatform

class AgentState(TypedDict):
    """에이전트 상태"""
    user_input: str
    analysis: str
    recommendation: str

def analyze_node(state: AgentState) -> AgentState:
    """사용자 입력 분석"""
    user_input = state["user_input"]

    # Gemini로 분석
    model = aiplatform.GenerativeModel("gemini-1.5-pro")
    prompt = f"다음 요청을 분석하세요: {user_input}"

    response = model.generate_content(prompt)
    state["analysis"] = response.text

    return state

def recommend_node(state: AgentState) -> AgentState:
    """추천 생성"""
    analysis = state["analysis"]

    model = aiplatform.GenerativeModel("gemini-1.5-pro")
    prompt = f"다음 분석 기반으로 추천하세요: {analysis}"

    response = model.generate_content(prompt)
    state["recommendation"] = response.text

    return state

# 그래프 구성
workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_node)
workflow.add_node("recommend", recommend_node)

workflow.set_entry_point("analyze")
workflow.add_edge("analyze", "recommend")
workflow.add_edge("recommend", END)

# 컴파일
app = workflow.compile()

# 실행 테스트
if __name__ == "__main__":
    result = app.invoke({
        "user_input": "립스틱 추천해주세요",
        "analysis": "",
        "recommendation": ""
    })

    print("Analysis:", result["analysis"])
    print("Recommendation:", result["recommendation"])
```

#### 5.2 체크포인터 추가 (상태 저장)
```python
from langgraph.checkpoint.sqlite import SqliteSaver

# 체크포인터 생성
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# 그래프 컴파일 시 추가
app = workflow.compile(checkpointer=checkpointer)

# Thread ID로 세션 관리
config = {"configurable": {"thread_id": "user_123"}}

result = app.invoke(
    {"user_input": "립스틱 추천", "analysis": "", "recommendation": ""},
    config
)
```

#### 5.3 조건부 라우팅 추가
```python
def should_ask_more(state: AgentState) -> str:
    """더 질문할지 결정"""
    analysis = state["analysis"]

    if "불확실" in analysis or "정보 부족" in analysis:
        return "ask_more"
    return "recommend"

workflow.add_conditional_edges(
    "analyze",
    should_ask_more,
    {
        "ask_more": "ask_more_info",
        "recommend": "recommend"
    }
)
```

#### 5.4 성공 기준
- [ ] 2-노드 그래프 실행 성공
- [ ] 상태가 체크포인터에 저장됨
- [ ] 조건부 라우팅 작동
- [ ] Thread 기반 세션 관리 확인

---

## 6. Phase 4: 광고 매칭 기본 (2주)

### 목표
"벡터 검색 + 간단한 랭킹으로 광고 선택"

### 우선순위: 🟡 중요

### 작업 목록

#### 6.1 광고 데이터 준비
```sql
-- 광고 벡터 테이블
CREATE TABLE ad_vectors (
  ad_id VARCHAR(255) PRIMARY KEY,
  campaign_id VARCHAR(255),
  vector vector(768),
  metadata JSONB,
  bid_amount DECIMAL(6, 2),
  budget_remaining DECIMAL(10, 2),
  status VARCHAR(20) DEFAULT 'active'
);

-- 샘플 광고 데이터
INSERT INTO ad_vectors (ad_id, campaign_id, vector, metadata, bid_amount, budget_remaining)
VALUES
  ('ad_001', 'camp_001', (SELECT vector FROM content_vectors WHERE content_id = 'cnt_1'),
   '{"product": "립스틱", "brand": "브랜드A"}', 2.5, 1000.0),
  ('ad_002', 'camp_002', (SELECT vector FROM content_vectors WHERE content_id = 'cnt_2'),
   '{"product": "티셔츠", "brand": "브랜드B"}', 1.8, 1500.0);
```

#### 6.2 간단한 광고 매칭
```python
# src/core/ads/simple_matcher.py

class SimpleAdMatcher:
    def __init__(self, vector_search: VectorSearch):
        self.search = vector_search

    def match_ads(self, content_vector: np.ndarray, k: int = 5) -> List[dict]:
        """콘텐츠에 맞는 광고 찾기"""

        # 1. 벡터 검색
        with self.search.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ad_id,
                    campaign_id,
                    metadata,
                    bid_amount,
                    budget_remaining,
                    1 - (vector <=> %s::vector) AS similarity
                FROM ad_vectors
                WHERE status = 'active' AND budget_remaining > 0
                ORDER BY vector <=> %s::vector
                LIMIT %s
                """,
                (content_vector.tolist(), content_vector.tolist(), k)
            )
            results = cur.fetchall()

        # 2. 간단한 스코어링 (similarity × bid)
        scored = []
        for row in results:
            ad_id, campaign_id, metadata, bid, budget, similarity = row
            score = similarity * (bid / 10.0)  # 정규화

            scored.append({
                "ad_id": ad_id,
                "campaign_id": campaign_id,
                "metadata": metadata,
                "similarity": similarity,
                "bid": bid,
                "score": score
            })

        # 3. 정렬
        scored.sort(key=lambda x: x["score"], reverse=True)

        return scored

# 테스트
if __name__ == "__main__":
    search = VectorSearch("postgresql://dev:devpass@localhost/addeep")
    matcher = SimpleAdMatcher(search)

    embedder = TextEmbedder()
    query_vector = embedder.embed(["립스틱 추천"])[0]

    matched_ads = matcher.match_ads(query_vector, k=3)

    for ad in matched_ads:
        print(f"{ad['ad_id']}: score={ad['score']:.3f}, similarity={ad['similarity']:.3f}")
```

#### 6.3 성공 기준
- [ ] 광고 벡터 저장 성공
- [ ] 콘텐츠 기반 광고 검색 성공
- [ ] 스코어링 결과가 합리적
- [ ] 3개 이상 광고 후보 반환

---

## 7. Phase 5: PiMS & 온톨로지 (3주)

### 목표
"상품 데이터를 AI가 이해하는 형태로"

### 우선순위: 🟡 중요 (병렬 가능)

### 작업 목록

#### 7.1 온톨로지 v0 코드 테이블
```python
# src/models/ontology.py

from enum import Enum

class Category(str, Enum):
    # Fashion
    FASHION_TOP = "FASHION>TOP"
    FASHION_BOTTOM = "FASHION>BOTTOM"
    FASHION_OUTER = "FASHION>OUTER"

    # Cosmetic
    COSMETIC_LIP = "COSMETIC>LIP"
    COSMETIC_BASE = "COSMETIC>BASE"
    COSMETIC_EYE = "COSMETIC>EYE"

    # Jewelry
    JEWELRY_RING = "JEWELRY>RING"
    JEWELRY_NECKLACE = "JEWELRY>NECKLACE"

class Attribute(str, Enum):
    # Color
    COLOR_BLACK = "BLACK"
    COLOR_WHITE = "WHITE"
    COLOR_BEIGE = "BEIGE"

    # Fit (Fashion)
    FIT_SLIM = "SLIM"
    FIT_REGULAR = "REGULAR"
    FIT_OVERSIZE = "OVERSIZE"

    # Finish (Cosmetic)
    FINISH_MATTE = "MATTE"
    FINISH_SATIN = "SATIN"
    FINISH_GLOSSY = "GLOSSY"

# 정규화 사전
NORMALIZATION_DICT = {
    "color": {
        "오프화이트": "BEIGE",
        "아이보리": "BEIGE",
        "크림": "BEIGE",
        "검정": "BLACK",
        "흰색": "WHITE",
    },
    "fit": {
        "슬림": "SLIM",
        "기본": "REGULAR",
        "레귤러": "REGULAR",
        "오버": "OVERSIZE",
        "루즈": "OVERSIZE",
    },
    "finish": {
        "매트": "MATTE",
        "무광": "MATTE",
        "글로시": "GLOSSY",
        "윤광": "GLOSSY",
    }
}
```

#### 7.2 Product Token 생성기
```python
# src/core/pims/token_generator.py

from typing import Dict
import json

class ProductTokenGenerator:
    def __init__(self, llm_client):
        self.llm = llm_client

    def extract_from_description(self, description: str, images: List[str] = None) -> dict:
        """상품 설명에서 구조화된 정보 추출"""

        prompt = f"""
다음 상품 설명에서 정보를 추출하세요.

설명: {description}

다음 JSON 형식으로 출력:
{{
  "category_path": "COSMETIC>LIP>LIPSTICK",
  "attributes": {{
    "color_family": "BEIGE",
    "finish": "SATIN",
    ...
  }},
  "style_tags": ["natural", "daily"],
  "claims_detected": ["moisturizing"]
}}
"""

        response = self.llm.generate_content(prompt)
        extracted = json.loads(response.text)

        return extracted

    def normalize_attributes(self, attributes: dict) -> dict:
        """동의어를 표준 코드로 매핑"""
        normalized = {}

        for key, value in attributes.items():
            if key in NORMALIZATION_DICT:
                normalized[key] = NORMALIZATION_DICT[key].get(
                    value.lower(),
                    value
                )
            else:
                normalized[key] = value

        return normalized

    def create_product_token(self, product_id: str, description: str) -> dict:
        """Product Token 생성"""

        # 1. 추출
        extracted = self.extract_from_description(description)

        # 2. 정규화
        normalized_attrs = self.normalize_attributes(extracted["attributes"])

        # 3. 토큰 구성
        token = {
            "product_id": product_id,
            "version": 1,
            "source": "AI_AGENT",
            "normalized": {
                "category_path": extracted["category_path"],
                "attributes": normalized_attrs,
                "style_tags": extracted["style_tags"]
            },
            "constraints": {
                "claims_allowed": extracted.get("claims_detected", []),
                "claims_forbidden": []  # 정책에서 로드
            }
        }

        return token

# 테스트
if __name__ == "__main__":
    generator = ProductTokenGenerator(llm_client)

    description = "촉촉한 매트 립스틱, 자연스러운 누드 베이지 컬러"

    token = generator.create_product_token("P001", description)
    print(json.dumps(token, indent=2, ensure_ascii=False))
```

#### 7.3 성공 기준
- [ ] 온톨로지 코드 테이블 정의
- [ ] LLM 추출 성공률 > 80%
- [ ] 정규화 커버리지 > 70%
- [ ] Product Token 생성 성공

---

## 8. Phase 6: 고급 에이전트 (3주)

### 목표
"실제 광고결합 생성 에이전트 완성"

### 우선순위: 🟢 고도화

### 작업 목록

#### 8.1 9단계 파이프라인 구현
```python
# src/core/ai_agent/ad_combination_agent.py

class AdCombinationAgent:
    """광고결합 콘텐츠 생성 에이전트"""

    def __init__(self):
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """9단계 그래프 구축"""

        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("ingest", self.ingest_node)
        workflow.add_node("safety_precheck", self.safety_precheck_node)
        workflow.add_node("hybrid_retrieve", self.hybrid_retrieve_node)
        workflow.add_node("ad_ranking", self.ad_ranking_node)
        workflow.add_node("act_plan", self.act_plan_node)
        workflow.add_node("generate", self.generate_node)
        workflow.add_node("post_check", self.post_check_node)
        workflow.add_node("publish", self.publish_node)

        # 엣지 정의
        workflow.set_entry_point("ingest")
        workflow.add_edge("ingest", "safety_precheck")

        # 조건부 분기: Safety 실패 시 중단
        workflow.add_conditional_edges(
            "safety_precheck",
            lambda state: "proceed" if state["safety_passed"] else "abort",
            {
                "proceed": "hybrid_retrieve",
                "abort": END
            }
        )

        workflow.add_edge("hybrid_retrieve", "ad_ranking")
        workflow.add_edge("ad_ranking", "act_plan")
        workflow.add_edge("act_plan", "generate")
        workflow.add_edge("generate", "post_check")

        # 조건부 분기: Post-check 실패 시 재생성
        workflow.add_conditional_edges(
            "post_check",
            lambda state: "publish" if state["post_check_passed"] else "generate",
            {
                "publish": "publish",
                "generate": "generate"  # 재시도
            }
        )

        workflow.add_edge("publish", END)

        return workflow.compile(checkpointer=checkpointer)
```

#### 8.2 하이브리드 검색 (Vector + Graph)
```python
async def hybrid_retrieve_node(self, state: AgentState) -> AgentState:
    """Vector 검색 + Graph 제약"""

    content_vector = state["content_vector"]

    # 1. Vector 검색 (넓게)
    vector_candidates = await self.vector_search.search(
        content_vector,
        k=20
    )

    # 2. Graph 제약 필터링 (좁게)
    eligible_candidates = []

    for candidate in vector_candidates:
        # Cypher 쿼리로 적격성 체크
        is_eligible = await self.graph_db.execute(
            """
            MATCH (p:Product {product_id: $product_id})-[:BELONGS_TO]->(b:Brand)
            WHERE p.status = 'ACTIVE' AND b.status = 'ACTIVE'
            RETURN count(*) > 0 AS eligible
            """,
            {"product_id": candidate["product_id"]}
        )

        if is_eligible:
            eligible_candidates.append(candidate)

    state["ad_candidates"] = eligible_candidates
    return state
```

#### 8.3 브랜드 안전 장치
```python
async def post_check_node(self, state: AgentState) -> AgentState:
    """생성 결과 검증 (3중 방어)"""

    generated_content = state["generated_content"]
    brand_spec = state["brand_spec"]

    # 1. Template Lock (이미 생성 시 적용됨)

    # 2. Vision Post-check
    violations = await self.vision_checker.check(
        generated_content.image,
        brand_spec.logo_spec
    )

    if violations:
        # 3. Repair Loop
        repaired = await self.repair_loop(
            generated_content,
            violations,
            max_retries=3
        )

        if repaired:
            state["generated_content"] = repaired
            state["post_check_passed"] = True
        else:
            state["post_check_passed"] = False
            state["post_check_error"] = "Repair failed"
    else:
        state["post_check_passed"] = True

    return state
```

#### 8.4 성공 기준
- [ ] 9단계 파이프라인 완성
- [ ] 하이브리드 검색 작동
- [ ] 브랜드 안전 장치 작동
- [ ] End-to-End 테스트 성공

---

## 9. Phase 7: 프로덕션 준비 (2주)

### 목표
"실제 사용자에게 서비스 가능한 상태"

### 우선순위: 🔴 필수

### 작업 목록

#### 9.1 모니터링
```python
# src/utils/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
generation_requests = Counter(
    'generation_requests_total',
    'Total generation requests',
    ['status']
)

generation_duration = Histogram(
    'generation_duration_seconds',
    'Generation duration'
)

generation_cost = Histogram(
    'generation_cost_usd',
    'Generation cost in USD'
)

# 사용
with generation_duration.time():
    result = await agent.generate(request)

generation_cost.observe(result.cost)
generation_requests.labels(status='success').inc()
```

#### 9.2 로깅 및 트레이싱
```python
# src/utils/logging.py

import logging
from google.cloud import logging as cloud_logging

client = cloud_logging.Client()
client.setup_logging()

logger = logging.getLogger(__name__)

# 구조화된 로깅
def log_generation(request_id, user_id, status, duration, cost):
    logger.info(
        "Generation completed",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "status": status,
            "duration_seconds": duration,
            "cost_usd": cost,
            "labels": {
                "component": "ai_agent",
                "environment": "production"
            }
        }
    )
```

#### 9.3 에러 처리 및 재시도
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def generate_with_retry(request):
    """재시도 로직"""
    try:
        return await agent.generate(request)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise
```

#### 9.4 성공 기준
- [ ] Prometheus 메트릭 수집
- [ ] Cloud Logging 연동
- [ ] 재시도 로직 작동
- [ ] 에러 알림 설정

---

## 10. 병렬 작업 가능 항목

다음 작업들은 병렬로 진행할 수 있습니다:

### 팀 A: 데이터 & 인프라
- Phase 1: 데이터 파이프라인
- Phase 2: 벡터 검색
- Phase 7: 모니터링

### 팀 B: AI & 에이전트
- Phase 3: 간단한 에이전트
- Phase 6: 고급 에이전트

### 팀 C: PiMS & 온톨로지
- Phase 5: PiMS & 온톨로지
- 그래프 DB 설계

### 팀 D: 광고 시스템
- Phase 4: 광고 매칭
- 광고 랭킹 고도화

---

## 요약: 추천 순서

### 최우선 (1-4주)
```
Week 1: Phase 0 (인프라 기초)
Week 2-3: Phase 1 (데이터 파이프라인) + Phase 2 (벡터 검색)
Week 4-5: Phase 3 (간단한 에이전트)
```

### 중요 (5-9주)
```
Week 6-7: Phase 4 (광고 매칭)
Week 8-10: Phase 5 (PiMS & 온톨로지)
```

### 고도화 (10-15주)
```
Week 11-13: Phase 6 (고급 에이전트)
Week 14-15: Phase 7 (프로덕션 준비)
```

---

## 체크리스트

### 시작 전
- [ ] GCP 프로젝트 생성
- [ ] 팀 역할 분담
- [ ] 개발 환경 설정

### 매 Phase 후
- [ ] 성공 기준 달성 확인
- [ ] 코드 리뷰
- [ ] 문서 업데이트
- [ ] 데모 준비

### MVP 완성 (Phase 1-3)
- [ ] 데이터 흐름 확인
- [ ] 벡터 검색 작동
- [ ] 에이전트 실행 성공
- [ ] 팀 데모

### 프로덕션 준비 (Phase 7)
- [ ] 성능 테스트
- [ ] 보안 점검
- [ ] 모니터링 설정
- [ ] 배포 체크리스트

---

**문서 버전:** 1.0
**최종 수정일:** 2026-02-24
**작성자:** Implementation Team
