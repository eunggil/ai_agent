"""
DB 기반 데이터 조회
USE_MOCK_VECTOR_DB=false 일 때 mock_data.py 대신 사용

광고 후보 검색:
  - campaigns.embedding 이 있으면 pgvector 코사인 유사도 검색
  - 임베딩 없으면 전체 조회 후 키워드 스코어링으로 fallback
"""
import logging
import os
from typing import List

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
    """users 테이블에서 사용자 조회. 없으면 기본값 반환."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, profile FROM users WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()

        if row is None:
            logger.warning(f"[db_data] user_id={user_id} not found, using default")
            return {**DEFAULT_USER, "user_id": user_id}

        profile = row["profile"] or {}
        return {"user_id": row["user_id"], **profile}

    except Exception as e:
        logger.error(f"[db_data] get_user error: {e}")
        return {**DEFAULT_USER, "user_id": user_id}


# ──────────────────────────────────────────
# 광고 후보 검색
# ──────────────────────────────────────────

def retrieve_ad_candidates(interests: list, prompt: str, top_k: int = 3) -> List[dict]:
    """pgvector 유사도 검색으로 광고 후보 조회. 임베딩 미생성 시 키워드 스코어링으로 fallback."""
    query_vector = _generate_embedding(f"{prompt} {' '.join(interests)}")

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
                        logger.info(f"[db_data] vector search: {len(rows)} candidates")
                        return [_row_to_ad(row) for row in rows]

                # fallback: 전체 조회 후 키워드 스코어링
                logger.warning("[db_data] embedding not ready, falling back to keyword scoring")
                cur.execute(
                    "SELECT campaign_id, brand_id, campaign_data, targeting_rules FROM campaigns"
                )
                rows = cur.fetchall()

    except Exception as e:
        logger.error(f"[db_data] retrieve_ad_candidates error: {e}")
        return []

    return _keyword_score(rows, interests, prompt, top_k)


# ──────────────────────────────────────────
# 헬퍼
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


def _keyword_score(rows, interests: list, prompt: str, top_k: int) -> List[dict]:
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
