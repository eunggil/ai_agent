# 목업 데이터로 AI Agent 빠르게 시작하기

> 인프라 설정 없이 AI Agent 로직부터 검증

## 목차

1. [개요](#1-개요)
2. [환경 설정 (최소)](#2-환경-설정-최소)
3. [목업 데이터 준비](#3-목업-데이터-준비)
4. [목업 벡터 DB](#4-목업-벡터-db)
5. [목업 그래프 DB](#5-목업-그래프-db)
6. [간단한 에이전트 구현](#6-간단한-에이전트-구현)
7. [하이브리드 검색 (목업)](#7-하이브리드-검색-목업)
8. [광고 매칭 (목업)](#8-광고-매칭-목업)
9. [실제 DB로 전환](#9-실제-db로-전환)

---

## 1. 개요

### 목표
- **인프라 설정 없이** AI Agent 로직 개발
- **빠른 프로토타이핑**으로 컨셉 검증
- 나중에 **실제 DB로 쉽게 교체**

### 필요한 것
- Python 3.11+
- Vertex AI API 키 (LLM만 사용)
- 나머지는 전부 in-memory!

---

## 2. 환경 설정 (최소)

### 2.1 프로젝트 구조

```bash
addeep-ai-agent/
├── src/
│   ├── mock/              # 목업 데이터 및 DB
│   │   ├── data.py
│   │   ├── vector_db.py
│   │   └── graph_db.py
│   ├── agent/             # AI Agent
│   │   ├── simple_agent.py
│   │   └── ad_agent.py
│   └── main.py
├── requirements.txt
└── .env
```

### 2.2 의존성 설치

```bash
# requirements.txt
langgraph==0.2.0
langchain==0.3.0
google-cloud-aiplatform==1.70.0
numpy==1.26.0
python-dotenv==1.0.0
```

```bash
pip install -r requirements.txt
```

### 2.3 환경 변수

```bash
# .env
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
```

---

## 3. 목업 데이터 준비

### 3.1 샘플 데이터 정의

```python
# src/mock/data.py

"""목업 데이터 세트"""

# 사용자 데이터
USERS = {
    "user_001": {
        "user_id": "user_001",
        "age": 28,
        "gender": "FEMALE",
        "interests": ["cosmetic", "fashion", "wellness"],
        "recent_views": ["cnt_001", "cnt_003", "cnt_005"]
    },
    "user_002": {
        "user_id": "user_002",
        "age": 35,
        "gender": "MALE",
        "interests": ["fashion", "accessories"],
        "recent_views": ["cnt_002", "cnt_004"]
    }
}

# 콘텐츠 데이터
CONTENTS = {
    "cnt_001": {
        "content_id": "cnt_001",
        "title": "데일리 립메이크업 추천",
        "description": "촉촉하고 자연스러운 립스틱 MLBB 컬러 추천",
        "category": "cosmetic",
        "tags": ["lip", "natural", "daily", "mlbb"],
        "creator": "beauty_creator_01"
    },
    "cnt_002": {
        "content_id": "cnt_002",
        "title": "봄 티셔츠 코디",
        "description": "편안한 오버핏 티셔츠 스타일링",
        "category": "fashion",
        "tags": ["tshirt", "oversize", "casual", "spring"],
        "creator": "fashion_creator_01"
    },
    "cnt_003": {
        "content_id": "cnt_003",
        "title": "섬세한 반지 추천",
        "description": "데일리로 착용하기 좋은 심플한 실버 반지",
        "category": "jewelry",
        "tags": ["ring", "silver", "simple", "daily"],
        "creator": "jewelry_creator_01"
    },
    "cnt_004": {
        "content_id": "cnt_004",
        "title": "가죽 가방 관리법",
        "description": "고급 가죽 가방 오래 사용하는 법",
        "category": "fashion",
        "tags": ["bag", "leather", "care"],
        "creator": "fashion_creator_02"
    },
    "cnt_005": {
        "content_id": "cnt_005",
        "title": "피부 진정 팩 추천",
        "description": "민감한 피부를 위한 진정 스킨케어",
        "category": "cosmetic",
        "tags": ["skincare", "soothing", "sensitive"],
        "creator": "beauty_creator_02"
    }
}

# 상품 데이터
PRODUCTS = {
    "prod_001": {
        "product_id": "prod_001",
        "name": "로즈 누드 립스틱",
        "brand_id": "brand_001",
        "category": "COSMETIC>LIP>LIPSTICK",
        "attributes": {
            "shade_name": "Rose Nude",
            "finish": "SATIN",
            "undertone": "WARM",
            "opacity": "MEDIUM"
        },
        "price": 28000,
        "tags": ["natural", "daily", "moisturizing"]
    },
    "prod_002": {
        "product_id": "prod_002",
        "name": "오버핏 베이직 티셔츠",
        "brand_id": "brand_002",
        "category": "FASHION>TOP>TSHIRT",
        "attributes": {
            "fit": "OVERSIZE",
            "fabric": "COTTON",
            "color": "BEIGE"
        },
        "price": 35000,
        "tags": ["casual", "comfortable", "basic"]
    },
    "prod_003": {
        "product_id": "prod_003",
        "name": "실버 체인 반지",
        "brand_id": "brand_003",
        "category": "JEWELRY>RING",
        "attributes": {
            "material": "SILVER",
            "style": "MINIMAL"
        },
        "price": 45000,
        "tags": ["simple", "daily", "unisex"]
    },
    "prod_004": {
        "product_id": "prod_004",
        "name": "진정 수분 팩",
        "brand_id": "brand_001",
        "category": "COSMETIC>SKINCARE",
        "attributes": {
            "skin_type": ["SENSITIVE", "DRY"],
            "claims": ["soothing", "moisturizing"]
        },
        "price": 18000,
        "tags": ["soothing", "hydrating", "gentle"]
    }
}

# 브랜드 데이터
BRANDS = {
    "brand_001": {
        "brand_id": "brand_001",
        "name": "Beauty Brand A",
        "category": "COSMETIC",
        "tier": "PREMIUM",
        "guidelines": {
            "tone": ["scientific", "trustworthy", "gentle"],
            "forbidden_phrases": ["치료", "완치", "즉각 효과"],
            "required_disclaimers": ["개인차가 있을 수 있습니다"]
        }
    },
    "brand_002": {
        "brand_id": "brand_002",
        "name": "Fashion Brand B",
        "category": "FASHION",
        "tier": "MID",
        "guidelines": {
            "tone": ["casual", "comfortable", "everyday"],
            "forbidden_phrases": [],
            "required_disclaimers": []
        }
    },
    "brand_003": {
        "brand_id": "brand_003",
        "name": "Jewelry Brand C",
        "category": "JEWELRY",
        "tier": "PREMIUM",
        "guidelines": {
            "tone": ["elegant", "minimal", "timeless"],
            "forbidden_phrases": [],
            "required_disclaimers": ["순도 표시 확인"]
        }
    }
}

# 캠페인 데이터
CAMPAIGNS = {
    "camp_001": {
        "campaign_id": "camp_001",
        "name": "립스틱 봄 시즌 프로모션",
        "brand_id": "brand_001",
        "product_ids": ["prod_001"],
        "objective": "CONVERSION",
        "daily_budget": 500000,
        "bid_amount": 2500,
        "status": "ACTIVE",
        "targeting": {
            "age_range": [20, 39],
            "genders": ["FEMALE"],
            "interests": ["cosmetic", "beauty"]
        }
    },
    "camp_002": {
        "campaign_id": "camp_002",
        "name": "티셔츠 신상 런칭",
        "brand_id": "brand_002",
        "product_ids": ["prod_002"],
        "objective": "AWARENESS",
        "daily_budget": 300000,
        "bid_amount": 1800,
        "status": "ACTIVE",
        "targeting": {
            "age_range": [20, 45],
            "genders": ["ALL"],
            "interests": ["fashion"]
        }
    },
    "camp_003": {
        "campaign_id": "camp_003",
        "name": "주얼리 데일리 컬렉션",
        "brand_id": "brand_003",
        "product_ids": ["prod_003"],
        "objective": "CTR",
        "daily_budget": 400000,
        "bid_amount": 2000,
        "status": "ACTIVE",
        "targeting": {
            "age_range": [25, 40],
            "genders": ["ALL"],
            "interests": ["jewelry", "accessories"]
        }
    }
}
```

---

## 4. 목업 벡터 DB

### 4.1 In-Memory 벡터 DB 구현

```python
# src/mock/vector_db.py

"""In-Memory 벡터 데이터베이스"""

import numpy as np
from typing import List, Tuple, Dict, Optional

class MockVectorDB:
    """목업 벡터 DB (코사인 유사도 검색)"""

    def __init__(self):
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, dict] = {}

    def insert(self, id: str, vector: np.ndarray, metadata: dict):
        """벡터 저장"""
        self.vectors[id] = vector / np.linalg.norm(vector)  # 정규화
        self.metadata[id] = metadata

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        filters: Optional[dict] = None
    ) -> List[Tuple[str, dict, float]]:
        """코사인 유사도 기반 검색"""

        query_norm = query_vector / np.linalg.norm(query_vector)

        # 유사도 계산
        results = []
        for id, vector in self.vectors.items():
            # 필터 적용
            if filters:
                metadata = self.metadata[id]
                if not self._match_filters(metadata, filters):
                    continue

            similarity = np.dot(query_norm, vector)
            results.append((id, self.metadata[id], float(similarity)))

        # 정렬
        results.sort(key=lambda x: x[2], reverse=True)

        return results[:k]

    def _match_filters(self, metadata: dict, filters: dict) -> bool:
        """필터 매칭"""
        for key, value in filters.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True

# 글로벌 인스턴스
vector_db = MockVectorDB()


def initialize_mock_vectors():
    """목업 벡터 초기화 (간단한 임베딩)"""

    from src.mock.data import CONTENTS, PRODUCTS

    # 콘텐츠 벡터 (태그 기반 간단한 임베딩)
    for content_id, content in CONTENTS.items():
        # 간단한 방법: 태그를 해시하여 벡터 생성
        vector = _simple_embedding(content["tags"] + [content["category"]])
        vector_db.insert(
            f"content_{content_id}",
            vector,
            {"type": "content", **content}
        )

    # 상품 벡터
    for product_id, product in PRODUCTS.items():
        vector = _simple_embedding(product["tags"] + [product["category"]])
        vector_db.insert(
            f"product_{product_id}",
            vector,
            {"type": "product", **product}
        )


def _simple_embedding(tags: List[str], dim: int = 128) -> np.ndarray:
    """태그 기반 간단한 임베딩 생성"""
    np.random.seed(hash(" ".join(sorted(tags))) % (2**32))
    return np.random.randn(dim)


# 초기화
initialize_mock_vectors()
```

---

## 5. 목업 그래프 DB

### 5.1 In-Memory 그래프 DB 구현

```python
# src/mock/graph_db.py

"""In-Memory 그래프 데이터베이스"""

from typing import List, Dict, Optional
from collections import defaultdict

class MockGraphDB:
    """목업 그래프 DB (간단한 관계 저장)"""

    def __init__(self):
        # 노드: {node_id: {type, properties}}
        self.nodes: Dict[str, dict] = {}

        # 엣지: {(from_id, relation, to_id): {properties}}
        self.edges: Dict[tuple, dict] = {}

        # 인덱스: {node_type: [node_ids]}
        self.type_index: Dict[str, List[str]] = defaultdict(list)

    def add_node(self, node_id: str, node_type: str, properties: dict):
        """노드 추가"""
        self.nodes[node_id] = {
            "type": node_type,
            "properties": properties
        }
        self.type_index[node_type].append(node_id)

    def add_edge(
        self,
        from_id: str,
        relation: str,
        to_id: str,
        properties: dict = None
    ):
        """엣지 추가"""
        self.edges[(from_id, relation, to_id)] = properties or {}

    def get_node(self, node_id: str) -> Optional[dict]:
        """노드 조회"""
        return self.nodes.get(node_id)

    def get_neighbors(
        self,
        node_id: str,
        relation: Optional[str] = None
    ) -> List[tuple]:
        """이웃 노드 조회"""
        neighbors = []

        for (from_id, rel, to_id), props in self.edges.items():
            if from_id == node_id:
                if relation is None or rel == relation:
                    neighbors.append((to_id, rel, props))

        return neighbors

    def check_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 3
    ) -> bool:
        """두 노드 사이 경로 존재 여부"""

        if from_id == to_id:
            return True

        visited = set()
        queue = [(from_id, 0)]

        while queue:
            current, depth = queue.pop(0)

            if current == to_id:
                return True

            if depth >= max_depth:
                continue

            if current in visited:
                continue

            visited.add(current)

            for neighbor_id, _, _ in self.get_neighbors(current):
                queue.append((neighbor_id, depth + 1))

        return False

    def query(self, cypher_like: str, params: dict) -> List[dict]:
        """간단한 쿼리 (Cypher 스타일이지만 매우 단순화)"""

        # 예: "MATCH (p:Product)-[:BELONGS_TO]->(b:Brand) WHERE p.product_id = $pid"
        # 실제로는 특정 패턴만 지원

        if "BELONGS_TO" in cypher_like:
            product_id = params.get("product_id")
            if not product_id:
                return []

            # Product -> Brand 관계 찾기
            for (from_id, rel, to_id) in self.edges.keys():
                if from_id == product_id and rel == "BELONGS_TO":
                    brand = self.get_node(to_id)
                    product = self.get_node(product_id)

                    if brand and product:
                        return [{
                            "product": product,
                            "brand": brand
                        }]

        return []


# 글로벌 인스턴스
graph_db = MockGraphDB()


def initialize_mock_graph():
    """목업 그래프 초기화"""

    from src.mock.data import BRANDS, PRODUCTS, CAMPAIGNS

    # 브랜드 노드
    for brand_id, brand in BRANDS.items():
        graph_db.add_node(brand_id, "Brand", brand)

    # 상품 노드
    for product_id, product in PRODUCTS.items():
        graph_db.add_node(product_id, "Product", product)

        # Product -> Brand 엣지
        graph_db.add_edge(
            product_id,
            "BELONGS_TO",
            product["brand_id"]
        )

    # 캠페인 노드
    for campaign_id, campaign in CAMPAIGNS.items():
        graph_db.add_node(campaign_id, "Campaign", campaign)

        # Campaign -> Product 엣지
        for product_id in campaign["product_ids"]:
            graph_db.add_edge(
                campaign_id,
                "PROMOTES",
                product_id
            )


# 초기화
initialize_mock_graph()
```

---

## 6. 간단한 에이전트 구현

### 6.1 2-노드 에이전트 (Hello World)

```python
# src/agent/simple_agent.py

"""간단한 2-노드 에이전트"""

from langgraph.graph import StateGraph, END
from typing import TypedDict
from google.cloud import aiplatform
import os
from dotenv import load_dotenv

load_dotenv()

# Vertex AI 초기화
aiplatform.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION")
)


class AgentState(TypedDict):
    """에이전트 상태"""
    user_input: str
    analysis: str
    recommendation: str


def analyze_node(state: AgentState) -> AgentState:
    """사용자 입력 분석"""

    user_input = state["user_input"]

    # Gemini로 분석
    model = aiplatform.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
사용자 요청을 분석하세요:
"{user_input}"

다음 정보를 추출:
1. 카테고리 (cosmetic/fashion/jewelry)
2. 원하는 속성
3. 감정/톤

간결하게 3-4줄로 답변.
"""

    response = model.generate_content(prompt)
    state["analysis"] = response.text

    print(f"[Analyze] {response.text}")

    return state


def recommend_node(state: AgentState) -> AgentState:
    """추천 생성"""

    analysis = state["analysis"]

    # 간단한 추천 (실제로는 벡터 검색 결과 사용)
    model = aiplatform.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
다음 분석 기반으로 상품을 추천하세요:
{analysis}

추천 형식:
- 상품명
- 이유 (1-2줄)
"""

    response = model.generate_content(prompt)
    state["recommendation"] = response.text

    print(f"[Recommend] {response.text}")

    return state


# 그래프 구성
def build_simple_agent():
    """간단한 에이전트 빌드"""

    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("recommend", recommend_node)

    # 엣지 정의
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "recommend")
    workflow.add_edge("recommend", END)

    # 컴파일
    app = workflow.compile()

    return app


# 테스트
if __name__ == "__main__":
    agent = build_simple_agent()

    result = agent.invoke({
        "user_input": "촉촉한 립스틱 추천해주세요",
        "analysis": "",
        "recommendation": ""
    })

    print("\n=== 결과 ===")
    print(f"분석: {result['analysis']}")
    print(f"추천: {result['recommendation']}")
```

---

## 7. 하이브리드 검색 (목업)

### 7.1 Vector + Graph 결합 검색

```python
# src/agent/hybrid_search.py

"""하이브리드 검색 (Vector + Graph)"""

import numpy as np
from typing import List, Dict
from src.mock.vector_db import vector_db, _simple_embedding
from src.mock.graph_db import graph_db


class HybridSearch:
    """벡터 + 그래프 하이브리드 검색"""

    def __init__(self):
        self.vector_db = vector_db
        self.graph_db = graph_db

    def search_products(
        self,
        query_tags: List[str],
        user_context: dict,
        k: int = 5
    ) -> List[Dict]:
        """상품 검색 (Vector + Graph)"""

        # 1. Vector 검색 (유사도)
        query_vector = _simple_embedding(query_tags)

        vector_results = self.vector_db.search(
            query_vector,
            k=k * 2,  # 여유있게 2배
            filters={"type": "product"}
        )

        print(f"[Vector] Found {len(vector_results)} candidates")

        # 2. Graph 제약 필터링
        eligible = []

        for result_id, metadata, similarity in vector_results:
            product_id = metadata["product_id"]

            # 브랜드 상태 체크
            brand_id = metadata["brand_id"]
            brand = self.graph_db.get_node(brand_id)

            if not brand:
                continue

            # 타겟팅 체크 (간단한 버전)
            if not self._check_targeting(metadata, user_context):
                continue

            eligible.append({
                "product_id": product_id,
                "product": metadata,
                "brand": brand["properties"],
                "similarity": similarity,
                "reason": f"유사도 {similarity:.2f}, 타겟 적합"
            })

            if len(eligible) >= k:
                break

        print(f"[Graph] Eligible: {len(eligible)} products")

        return eligible

    def _check_targeting(self, product: dict, user_context: dict) -> bool:
        """간단한 타겟팅 체크"""

        # 나이/성별은 간단하게 체크
        # 실제로는 더 복잡한 로직

        return True  # 목업에서는 모두 통과


# 테스트
if __name__ == "__main__":
    searcher = HybridSearch()

    # 검색 테스트
    results = searcher.search_products(
        query_tags=["lip", "natural", "daily"],
        user_context={"age": 28, "gender": "FEMALE"},
        k=3
    )

    print("\n=== 검색 결과 ===")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['product']['name']}")
        print(f"   브랜드: {result['brand']['name']}")
        print(f"   유사도: {result['similarity']:.3f}")
        print(f"   이유: {result['reason']}")
        print()
```

---

## 8. 광고 매칭 (목업)

### 8.1 광고 매칭 에이전트

```python
# src/agent/ad_agent.py

"""광고 결합 에이전트 (목업)"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from google.cloud import aiplatform
from src.agent.hybrid_search import HybridSearch
from src.mock.data import CAMPAIGNS

import os
from dotenv import load_dotenv

load_dotenv()

aiplatform.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION")
)


class AdAgentState(TypedDict):
    """광고 에이전트 상태"""
    user_input: str
    user_context: dict
    content_tags: List[str]
    ad_candidates: List[Dict]
    selected_ad: Dict
    generation_plan: str
    final_content: str


def analyze_request_node(state: AdAgentState) -> AdAgentState:
    """사용자 요청 분석"""

    model = aiplatform.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
사용자 요청: "{state['user_input']}"

다음을 추출하세요:
1. 카테고리
2. 주요 키워드 3-5개 (영어, 태그 형식)

JSON 형식으로 답변:
{{"category": "cosmetic", "tags": ["lip", "natural", "daily"]}}
"""

    response = model.generate_content(prompt)

    # 간단한 파싱 (실제로는 더 견고하게)
    import json
    try:
        result = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        state["content_tags"] = result["tags"]
    except:
        state["content_tags"] = ["cosmetic", "natural"]

    print(f"[Analyze] Tags: {state['content_tags']}")

    return state


def search_ads_node(state: AdAgentState) -> AdAgentState:
    """광고 검색 (하이브리드)"""

    searcher = HybridSearch()

    # 상품 검색
    products = searcher.search_products(
        query_tags=state["content_tags"],
        user_context=state["user_context"],
        k=5
    )

    # 상품 → 캠페인 매핑
    ad_candidates = []

    for product in products:
        product_id = product["product_id"]

        # 해당 상품을 홍보하는 캠페인 찾기
        for campaign_id, campaign in CAMPAIGNS.items():
            if product_id in campaign["product_ids"]:
                if campaign["status"] == "ACTIVE":
                    ad_candidates.append({
                        "campaign_id": campaign_id,
                        "campaign": campaign,
                        "product": product,
                        "score": product["similarity"] * (campaign["bid_amount"] / 10000)
                    })

    # 스코어 정렬
    ad_candidates.sort(key=lambda x: x["score"], reverse=True)

    state["ad_candidates"] = ad_candidates[:3]

    print(f"[Search] Found {len(ad_candidates)} ad candidates")

    return state


def select_ad_node(state: AdAgentState) -> AdAgentState:
    """광고 선택"""

    if not state["ad_candidates"]:
        state["selected_ad"] = {}
        return state

    # 최고 점수 선택
    selected = state["ad_candidates"][0]
    state["selected_ad"] = selected

    print(f"[Select] Selected: {selected['campaign']['name']}")
    print(f"  Product: {selected['product']['product']['name']}")
    print(f"  Score: {selected['score']:.3f}")

    return state


def plan_generation_node(state: AdAgentState) -> AdAgentState:
    """생성 계획 수립"""

    if not state["selected_ad"]:
        state["generation_plan"] = "No ad selected"
        return state

    model = aiplatform.GenerativeModel("gemini-1.5-flash")

    selected = state["selected_ad"]
    product = selected["product"]["product"]
    brand = selected["product"]["brand"]

    prompt = f"""
다음 상품을 콘텐츠에 자연스럽게 결합하는 계획을 세우세요:

사용자 요청: {state['user_input']}
상품: {product['name']}
브랜드: {brand['name']}
브랜드 톤: {brand['guidelines']['tone']}

계획 (3-4줄):
1. 어떤 방식으로 결합할지
2. 어떤 메시지를 전달할지
3. 주의사항
"""

    response = model.generate_content(prompt)
    state["generation_plan"] = response.text

    print(f"[Plan] {response.text}")

    return state


def generate_content_node(state: AdAgentState) -> AdAgentState:
    """최종 콘텐츠 생성"""

    if not state["selected_ad"]:
        state["final_content"] = "광고 후보를 찾을 수 없습니다."
        return state

    model = aiplatform.GenerativeModel("gemini-1.5-flash")

    selected = state["selected_ad"]
    product = selected["product"]["product"]
    brand = selected["product"]["brand"]

    prompt = f"""
다음 계획에 따라 광고 결합 콘텐츠를 생성하세요:

계획:
{state['generation_plan']}

상품 정보:
- 이름: {product['name']}
- 브랜드: {brand['name']}
- 특징: {', '.join(product['tags'])}

콘텐츠 형식:
[인트로 1-2줄]
[상품 소개 자연스럽게]
[클로징 1줄]

금칙어: {', '.join(brand['guidelines'].get('forbidden_phrases', []))}
필수 고지: {', '.join(brand['guidelines'].get('required_disclaimers', []))}
"""

    response = model.generate_content(prompt)
    state["final_content"] = response.text

    print(f"[Generate] {response.text}")

    return state


def build_ad_agent():
    """광고 결합 에이전트 빌드"""

    workflow = StateGraph(AdAgentState)

    # 노드 추가
    workflow.add_node("analyze_request", analyze_request_node)
    workflow.add_node("search_ads", search_ads_node)
    workflow.add_node("select_ad", select_ad_node)
    workflow.add_node("plan_generation", plan_generation_node)
    workflow.add_node("generate_content", generate_content_node)

    # 엣지 정의
    workflow.set_entry_point("analyze_request")
    workflow.add_edge("analyze_request", "search_ads")
    workflow.add_edge("search_ads", "select_ad")
    workflow.add_edge("select_ad", "plan_generation")
    workflow.add_edge("plan_generation", "generate_content")
    workflow.add_edge("generate_content", END)

    # 컴파일
    app = workflow.compile()

    return app


# 테스트
if __name__ == "__main__":
    agent = build_ad_agent()

    result = agent.invoke({
        "user_input": "촉촉하고 자연스러운 립스틱 추천해주세요",
        "user_context": {
            "user_id": "user_001",
            "age": 28,
            "gender": "FEMALE"
        },
        "content_tags": [],
        "ad_candidates": [],
        "selected_ad": {},
        "generation_plan": "",
        "final_content": ""
    })

    print("\n" + "="*60)
    print("최종 생성 콘텐츠:")
    print("="*60)
    print(result["final_content"])
```

---

## 9. 실제 DB로 전환

### 9.1 인터페이스 추상화

목업에서 실제 DB로 전환하기 쉽게 인터페이스를 정의:

```python
# src/core/interfaces.py

"""DB 인터페이스 (목업 ↔ 실제 전환 용이)"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional
import numpy as np


class VectorDBInterface(ABC):
    """벡터 DB 인터페이스"""

    @abstractmethod
    def insert(self, id: str, vector: np.ndarray, metadata: dict):
        pass

    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        k: int,
        filters: Optional[dict]
    ) -> List[Tuple[str, dict, float]]:
        pass


class GraphDBInterface(ABC):
    """그래프 DB 인터페이스"""

    @abstractmethod
    def add_node(self, node_id: str, node_type: str, properties: dict):
        pass

    @abstractmethod
    def add_edge(self, from_id: str, relation: str, to_id: str, properties: dict):
        pass

    @abstractmethod
    def query(self, query: str, params: dict) -> List[dict]:
        pass
```

### 9.2 목업 구현

```python
# src/mock/vector_db.py (수정)

from src.core.interfaces import VectorDBInterface

class MockVectorDB(VectorDBInterface):
    """목업 벡터 DB"""
    # ... 기존 코드 ...
```

### 9.3 실제 구현 (나중에)

```python
# src/data/vector_db/postgresql.py

from src.core.interfaces import VectorDBInterface
import psycopg2

class PostgreSQLVectorDB(VectorDBInterface):
    """실제 PostgreSQL + pgvector"""

    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)

    def insert(self, id: str, vector: np.ndarray, metadata: dict):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO vectors (id, vector, metadata) VALUES (%s, %s, %s)",
                (id, vector.tolist(), json.dumps(metadata))
            )
        self.conn.commit()

    # ... 나머지 구현 ...
```

### 9.4 전환 방법

```python
# src/main.py

# 목업 사용
# from src.mock.vector_db import vector_db

# 실제 DB 사용 (나중에)
from src.data.vector_db.postgresql import PostgreSQLVectorDB
vector_db = PostgreSQLVectorDB("postgresql://...")
```

---

## 10. 실행 및 테스트

### 10.1 간단한 에이전트 실행

```bash
cd addeep-ai-agent
python src/agent/simple_agent.py
```

### 10.2 광고 에이전트 실행

```bash
python src/agent/ad_agent.py
```

### 10.3 전체 통합 테스트

```python
# src/main.py

"""전체 통합 테스트"""

from src.agent.ad_agent import build_ad_agent

def main():
    """메인 함수"""

    agent = build_ad_agent()

    # 여러 테스트 케이스
    test_cases = [
        "촉촉한 립스틱 추천해주세요",
        "편안한 티셔츠 찾아요",
        "섬세한 반지 추천해주세요",
        "민감한 피부를 위한 스킨케어"
    ]

    for test_input in test_cases:
        print(f"\n{'='*60}")
        print(f"테스트: {test_input}")
        print('='*60)

        result = agent.invoke({
            "user_input": test_input,
            "user_context": {"user_id": "user_001", "age": 28, "gender": "FEMALE"},
            "content_tags": [],
            "ad_candidates": [],
            "selected_ad": {},
            "generation_plan": "",
            "final_content": ""
        })

        print(f"\n최종 결과:\n{result['final_content']}")


if __name__ == "__main__":
    main()
```

---

## 11. 다음 단계

### 목업으로 검증 완료 후

1. **Phase 2: 벡터 검색** 실제 구현
   - PostgreSQL + pgvector 설정
   - 실제 임베딩 (Vertex AI Text Embeddings)

2. **Phase 5: PiMS & 온톨로지**
   - 실제 상품 데이터 수집
   - LLM 기반 추출 파이프라인

3. **Phase 4: 그래프 DB**
   - Neo4j 또는 Neptune 설정
   - 브랜드/정책 관계 모델링

---

## 부록: 전체 파일 구조

```
addeep-ai-agent/
├── src/
│   ├── mock/
│   │   ├── __init__.py
│   │   ├── data.py              # 목업 데이터
│   │   ├── vector_db.py         # 목업 벡터 DB
│   │   └── graph_db.py          # 목업 그래프 DB
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── simple_agent.py      # 간단한 에이전트
│   │   ├── ad_agent.py          # 광고 에이전트
│   │   └── hybrid_search.py     # 하이브리드 검색
│   │
│   ├── core/
│   │   └── interfaces.py        # DB 인터페이스
│   │
│   └── main.py                  # 통합 테스트
│
├── requirements.txt
├── .env
└── README.md
```

---

## 요약

✅ **장점**
- 인프라 설정 없이 바로 개발 가능
- AI Agent 로직에 집중
- LLM 호출만 실제 사용
- 나중에 실제 DB로 쉽게 전환

⚠️ **제약**
- 임베딩 품질은 실제와 다름
- 성능 테스트 불가
- 동시성 테스트 불가

🎯 **권장 흐름**
1. 목업으로 에이전트 로직 완성
2. 컨셉 검증 및 데모
3. 실제 DB로 단계적 전환

---

**문서 버전:** 1.0
**최종 수정일:** 2026-02-24
