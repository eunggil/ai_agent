"""
DB 기반 데이터 조회
USE_MOCK_VECTOR_DB=false 일 때 mock_data.py 대신 사용

광고 후보 검색:
  - campaigns.embedding 이 있으면 pgvector 코사인 유사도 검색
  - 임베딩 없으면 전체 조회 후 키워드 스코어링으로 fallback

user_vector 최적화:
  - get_user()가 long_term_vector를 함께 반환
  - retrieve_* 함수들이 user_vector를 직접 받으면 임베딩 생성 API 호출을 생략
"""
import logging
import os
from typing import List, Optional

from src.core.db import get_connection

logger = logging.getLogger(__name__)

DEFAULT_USER = {
    "user_id": "unknown",
    "name": "신규 사용자",
    "age": 25,
    "interests": ["lifestyle"],
    "mindset": "curious",
    "recent_activities": [],
    "vector_summary": "신규 사용자, 선호도 파악 중",
}


# ──────────────────────────────────────────
# 사용자 조회
# ──────────────────────────────────────────

def get_user(user_id: str) -> dict:
    """users 테이블에서 사용자 조회. 없으면 기본값 반환.

    반환값에 'long_term_vector' 키가 포함되어 있으면 DB에 임베딩이 있는 것.
    agent.py의 _load_context_node에서 user_vector로 분리해 state에 저장.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, profile, long_term_vector FROM users WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()

        if row is None:
            logger.warning(f"[db_data] user_id={user_id} not found, using default")
            return {**DEFAULT_USER, "user_id": user_id}

        profile = row["profile"] or {}
        user = {"user_id": row["user_id"], **profile}

        # long_term_vector가 있으면 포함 (retrieve_* 함수에서 임베딩 재생성 생략용)
        vector = row["long_term_vector"]
        if vector is not None:
            user["long_term_vector"] = _to_list(vector)

        return user

    except Exception as e:
        logger.error(f"[db_data] get_user error: {e}")
        return {**DEFAULT_USER, "user_id": user_id}


# ──────────────────────────────────────────
# 광고 후보 검색
# ──────────────────────────────────────────

def retrieve_ad_candidates(
    interests: list,
    prompt: str,
    top_k: int = 3,
    user_vector: Optional[list] = None,
) -> List[dict]:
    """pgvector 유사도 검색으로 광고 후보 조회.

    user_vector가 제공되면 임베딩 API 호출을 생략하고 재사용.
    임베딩이 없으면 키워드 스코어링으로 fallback.
    """
    query_vector = user_vector or _generate_embedding(f"{prompt} {' '.join(interests)}")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if query_vector:
                    cur.execute(
                        """
                        SELECT campaign_id, brand_id, campaign_data, targeting_rules,
                               ROUND(CAST(
                                   (1 - (embedding <=> %s::vector)) * 0.7
                                   + COALESCE((campaign_data->>'bid')::float, 0) / 10.0 * 0.3
                               AS NUMERIC), 3) AS relevance_score
                        FROM campaigns
                        WHERE embedding IS NOT NULL
                        ORDER BY relevance_score DESC
                        LIMIT %s
                        """,
                        (query_vector, top_k),
                    )
                    rows = cur.fetchall()

                    if rows:
                        logger.info(f"[db_data] ad vector search: {len(rows)} candidates")
                        return [_row_to_ad(row) for row in rows]

                # fallback: 전체 조회 후 키워드 스코어링
                logger.warning("[db_data] ad embedding not ready, falling back to keyword scoring")
                cur.execute(
                    "SELECT campaign_id, brand_id, campaign_data, targeting_rules FROM campaigns"
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error(f"[db_data] retrieve_ad_candidates error: {e}")
        return []

    return _keyword_score_ads(rows, interests, prompt, top_k)


# ──────────────────────────────────────────
# 관련 상품 검색
# ──────────────────────────────────────────

def retrieve_products(
    interests: list,
    prompt: str,
    top_k: int = 3,
    user_vector: Optional[list] = None,
) -> List[dict]:
    """products 테이블에서 관련 상품 검색.

    user_vector가 제공되면 임베딩 API 호출을 생략하고 재사용.
    """
    query_vector = user_vector or _generate_embedding(f"{prompt} {' '.join(interests)}")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if query_vector:
                    cur.execute(
                        """
                        SELECT product_id, brand_id, product_data,
                               ROUND(CAST(1 - (embedding <=> %s::vector) AS NUMERIC), 3) AS similarity
                        FROM products
                        WHERE embedding IS NOT NULL
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (query_vector, top_k),
                    )
                    rows = cur.fetchall()

                    if rows:
                        logger.info(f"[db_data] product vector search: {len(rows)} results")
                        return [_row_to_product(row) for row in rows]

                # fallback: 카테고리/키워드 기반
                logger.warning("[db_data] product embedding not ready, falling back to keyword scoring")
                cur.execute("SELECT product_id, brand_id, product_data FROM products")
                rows = cur.fetchall()

    except Exception as e:
        logger.error(f"[db_data] retrieve_products error: {e}")
        return []

    return _keyword_score_products(rows, interests, prompt, top_k)


# ──────────────────────────────────────────
# 참고 콘텐츠 검색
# ──────────────────────────────────────────

def retrieve_reference_contents(
    interests: list,
    prompt: str,
    top_k: int = 2,
    user_vector: Optional[list] = None,
) -> List[dict]:
    """contents 테이블에서 창작 참고용 콘텐츠 검색.

    user_vector가 제공되면 임베딩 API 호출을 생략하고 재사용.
    """
    query_vector = user_vector or _generate_embedding(f"{prompt} {' '.join(interests)}")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if query_vector:
                    cur.execute(
                        """
                        SELECT content_id, content_type, metadata,
                               ROUND(CAST(1 - (embedding <=> %s::vector) AS NUMERIC), 3) AS similarity
                        FROM contents
                        WHERE embedding IS NOT NULL
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (query_vector, top_k),
                    )
                    rows = cur.fetchall()

                    if rows:
                        logger.info(f"[db_data] content vector search: {len(rows)} results")
                        return [_row_to_content(row) for row in rows]

                # fallback: 카테고리 기반 랜덤 샘플
                cur.execute(
                    "SELECT content_id, content_type, metadata FROM contents LIMIT %s",
                    (top_k,),
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error(f"[db_data] retrieve_reference_contents error: {e}")
        return []

    return [_row_to_content(row) for row in rows]


# ──────────────────────────────────────────
# 임베딩 생성
# ──────────────────────────────────────────

def _generate_embedding(text: str) -> list:
    """Vertex AI text-embedding-004 로 쿼리 임베딩 생성."""
    try:
        import vertexai
        from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

        project_id = os.getenv("GCP_PROJECT_ID", "")
        region = os.getenv("GCP_REGION", "us-central1")
        model_name = os.getenv("VERTEX_AI_EMBEDDING_MODEL", "text-embedding-004")

        vertexai.init(project=project_id, location=region)
        model = TextEmbeddingModel.from_pretrained(model_name)
        result = model.get_embeddings([TextEmbeddingInput(text, "RETRIEVAL_QUERY")])
        return result[0].values
    except Exception as e:
        logger.warning(f"[db_data] embedding generation failed: {e}")
        return []


# ──────────────────────────────────────────
# 변환 헬퍼
# ──────────────────────────────────────────

def _row_to_ad(row) -> dict:
    data = row["campaign_data"] or {}
    rules = row["targeting_rules"] or {}
    return {
        "ad_id": data.get("ad_id", row["campaign_id"]),
        "campaign_id": row["campaign_id"],
        "product": data.get("product", ""),
        "brand": data.get("brand", row.get("brand_id") or ""),
        "category": data.get("category", ""),
        "description": data.get("description", ""),
        "bid": float(data.get("bid", 0)),
        "image_url": data.get("image_url", ""),
        "tags": rules.get("tags", []),
        "relevance_score": float(row.get("relevance_score", 0.5)),
    }


def _row_to_product(row) -> dict:
    data = row["product_data"] or {}
    return {
        "product_id": row["product_id"],
        "brand_id": row.get("brand_id", ""),
        "name": data.get("name", ""),
        "brand": data.get("brand", row.get("brand_id") or ""),
        "category": data.get("category", ""),
        "description": data.get("description", ""),
        "price": data.get("price", 0),
        "image_url": data.get("image_url", ""),
        "similarity": float(row.get("similarity", 0.5)),
    }


def _row_to_content(row) -> dict:
    meta = row["metadata"] or {}
    return {
        "content_id": row["content_id"],
        "content_type": row.get("content_type", ""),
        "text": meta.get("text", ""),
        "brand": meta.get("brand", ""),
        "category": meta.get("category", ""),
        "image_url": meta.get("image_url", ""),
        "similarity": float(row.get("similarity", 0.5)),
    }


# ──────────────────────────────────────────
# 키워드 스코어링 fallback
# ──────────────────────────────────────────

def _keyword_score_ads(rows, interests: list, prompt: str, top_k: int) -> List[dict]:
    prompt_lower = prompt.lower()
    scored = []

    for row in rows:
        data = row["campaign_data"] or {}
        rules = row["targeting_rules"] or {}
        tags = rules.get("tags", [])
        score = 0.0

        for interest in interests:
            if interest in tags:
                score += 0.4
        for tag in tags:
            if tag in prompt_lower:
                score += 0.3
        if data.get("category", "") in prompt_lower:
            score += 0.2
        score += float(data.get("bid", 0)) / 10.0

        ad = _row_to_ad(row)
        ad["relevance_score"] = round(score, 3)
        scored.append(ad)

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]


def _keyword_score_products(rows, interests: list, prompt: str, top_k: int) -> List[dict]:
    prompt_lower = prompt.lower()
    scored = []

    for row in rows:
        data = row["product_data"] or {}
        score = 0.0
        category = data.get("category", "")

        if category in interests:
            score += 0.4
        if category in prompt_lower:
            score += 0.3
        if data.get("brand", "").lower() in prompt_lower:
            score += 0.2

        product = _row_to_product(row)
        product["similarity"] = round(score, 3)
        scored.append(product)

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────

def _to_list(vector) -> list:
    """pgvector 반환값을 Python list로 변환."""
    if isinstance(vector, list):
        return vector
    if hasattr(vector, "tolist"):
        return vector.tolist()
    if isinstance(vector, str):
        import ast
        return ast.literal_eval(vector)
    return list(vector)
