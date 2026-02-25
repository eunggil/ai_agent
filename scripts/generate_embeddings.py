"""
Vertex AI text-embedding-004 를 사용하여 users/campaigns 테이블에 벡터 임베딩 삽입

실행 (Docker 컨테이너 내부):
    docker compose exec ai-agent python scripts/generate_embeddings.py

환경변수:
    GCP_PROJECT_ID, GCP_REGION, VERTEX_AI_EMBEDDING_MODEL (기본: text-embedding-004)
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
REGION = os.getenv("GCP_REGION", "us-central1")
EMBEDDING_MODEL = os.getenv("VERTEX_AI_EMBEDDING_MODEL", "text-embedding-004")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "ai_agent"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_embeddings(model: TextEmbeddingModel, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    inputs = [TextEmbeddingInput(text, task_type) for text in texts]
    result = model.get_embeddings(inputs)
    return [e.values for e in result]


def main():
    logger.info(f"Vertex AI 초기화: project={PROJECT_ID}, region={REGION}, model={EMBEDDING_MODEL}")
    vertexai.init(project=PROJECT_ID, location=REGION)
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)

    conn = get_connection()
    try:
        # ── 사용자 임베딩 ─────────────────────────────
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, profile FROM users")
            users = cur.fetchall()

        logger.info(f"사용자 {len(users)}명 임베딩 생성 중...")
        for user in users:
            profile = user["profile"] or {}
            long_text = profile.get("vector_summary", "사용자")
            short_text = " ".join(profile.get("recent_activities", [])) or long_text

            vectors = get_embeddings(model, [long_text, short_text])

            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users
                          SET long_term_vector  = %s::vector,
                              short_term_vector = %s::vector
                        WHERE user_id = %s""",
                    (vectors[0], vectors[1], user["user_id"]),
                )
            logger.info(f"  ✓ user {user['user_id']}")

        # ── 캠페인 임베딩 ─────────────────────────────
        with conn.cursor() as cur:
            cur.execute("SELECT campaign_id, campaign_data, targeting_rules FROM campaigns")
            campaigns = cur.fetchall()

        logger.info(f"캠페인 {len(campaigns)}개 임베딩 생성 중...")
        for camp in campaigns:
            data = camp["campaign_data"] or {}
            rules = camp["targeting_rules"] or {}
            tags = " ".join(rules.get("tags", []))
            text = f"{data.get('product', '')} {data.get('description', '')} {tags}".strip()

            vectors = get_embeddings(model, [text])

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE campaigns SET embedding = %s::vector WHERE campaign_id = %s",
                    (vectors[0], camp["campaign_id"]),
                )
            logger.info(f"  ✓ campaign {camp['campaign_id']} ({data.get('product', '')})")

        conn.commit()
        logger.info("완료! 모든 임베딩이 DB에 저장되었습니다.")

    except Exception as e:
        conn.rollback()
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
