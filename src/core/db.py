"""
PostgreSQL 연결 관리 (psycopg2)
"""
import os
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


def get_connection():
    """새 DB 연결 반환. with 문과 함께 사용 권장."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "ai_agent"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
