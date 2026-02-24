"""
AI Agent FastAPI Application
"""
import asyncio
import json
import os
from typing import Any, Dict, Optional

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def _try_parse_json(s: str, default: dict = None) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return default or {}

# 환경 변수
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "vertex")
MEDIA_PROVIDER = os.getenv("MEDIA_PROVIDER", "none")
USE_MOCK_VECTOR_DB = os.getenv("USE_MOCK_VECTOR_DB", "true").lower() == "true"
USE_MOCK_GRAPH_DB = os.getenv("USE_MOCK_GRAPH_DB", "true").lower() == "true"

# FastAPI 앱
app = FastAPI(
    title="AI Agent API",
    description="User-State Driven Media Generation Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────
# Pydantic 모델
# ──────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    environment: str
    config: Dict[str, Any]


class FeedRequest(BaseModel):
    user_id: str
    limit: int = 10
    offset: int = 0


class AIGenerateRequest(BaseModel):
    user_id: str
    prompt: str
    media_type: Optional[str] = None   # "image" | "video" | "text" (없으면 MEDIA_TYPE 환경변수)
    options: Optional[Dict[str, Any]] = None


# ──────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "AI Agent API",
        "version": "0.1.0",
        "environment": ENVIRONMENT,
        "ai_provider": AI_PROVIDER,
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        environment=ENVIRONMENT,
        config={
            "gcp_project_id": GCP_PROJECT_ID,
            "ai_provider": AI_PROVIDER,
            "media_provider": MEDIA_PROVIDER,
            "use_mock_vector_db": USE_MOCK_VECTOR_DB,
            "use_mock_graph_db": USE_MOCK_GRAPH_DB,
        },
    )


@app.get("/v1/feed")
async def get_feed(user_id: str, limit: int = 10, offset: int = 0):
    """기본 피드 조회 (목업)"""
    logger.info(f"Feed request - user_id: {user_id}, limit: {limit}")

    # TODO: 실제 피드 생성 로직 구현 (Phase 4)
    return {
        "user_id": user_id,
        "items": [
            {"id": f"feed_{i}", "type": "basic", "content": f"Sample feed item {i}"}
            for i in range(offset, offset + limit)
        ],
        "total": 100,
        "limit": limit,
        "offset": offset,
    }


@app.post("/v1/ai/generate-feed")
async def generate_ai_feed(request: AIGenerateRequest):
    """AI 피드 생성 (온디맨드) - LangGraph 에이전트 실행"""
    logger.info(f"AI generate request - user_id: {request.user_id}, prompt: {request.prompt}")

    # media_type: 요청값 우선, 없으면 환경변수
    media_type = request.media_type or os.getenv("MEDIA_TYPE", "text")

    try:
        from src.core.ai_agent.agent import get_agent

        agent = get_agent()

        # 동기 에이전트를 스레드풀에서 실행 (이벤트 루프 블로킹 방지)
        result = await asyncio.to_thread(agent.run, request.user_id, request.prompt, media_type)

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])

        # JSON 필드 파싱
        strategy = _try_parse_json(result.get("strategy", "{}"))
        state_analysis = _try_parse_json(result.get("state_analysis", "{}"))

        # 미디어 결과 구성
        media_result = None
        if result.get("media_data"):
            media_result = {
                "type": result.get("media_type", "image"),
                "data": result.get("media_data", ""),       # base64
                "mime_type": result.get("media_metadata", {}).get("mime_type", "image/png"),
                "metadata": result.get("media_metadata", {}),
            }

        return {
            "user_id": request.user_id,
            "prompt": request.prompt,
            "result": {
                "id": f"ai_feed_{request.user_id}",
                "type": "ai_generated",
                "content": result.get("generated_content", ""),
                "media": media_result,
                "metadata": {
                    "llm_provider": result.get("provider_name", AI_PROVIDER),
                    "media_provider": result.get("media_provider_name", MEDIA_PROVIDER),
                    "state_analysis": state_analysis,
                    "selected_ad": strategy.get("selected_product", ""),
                    "combination_method": strategy.get("combination_method", ""),
                    "using_mock": USE_MOCK_VECTOR_DB,
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 생성 실패: {str(e)}")


@app.get("/v1/user/{user_id}")
async def get_user(user_id: str):
    """사용자 정보 조회"""
    from src.core.ai_agent.mock_data import get_user as _get_user

    user = _get_user(user_id)
    return {
        "user_id": user_id,
        "profile": {
            "name": user.get("name", "Unknown"),
            "interests": user.get("interests", []),
            "mindset": user.get("mindset", ""),
            "vector_summary": user.get("vector_summary", ""),
        },
    }


# ──────────────────────────────────────────
# 라이프사이클 이벤트
# ──────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting AI Agent API in {ENVIRONMENT} mode")
    logger.info(f"AI Provider: {AI_PROVIDER} | Media Provider: {MEDIA_PROVIDER}")
    logger.info(f"GCP Project: {GCP_PROJECT_ID}")
    logger.info(f"Mock Vector DB: {USE_MOCK_VECTOR_DB}, Mock Graph DB: {USE_MOCK_GRAPH_DB}")

    # 에이전트 사전 초기화 (첫 요청 지연 방지)
    try:
        from src.core.ai_agent.agent import get_agent
        get_agent()
        logger.info("FeedAgent initialized successfully")
    except Exception as e:
        logger.warning(f"FeedAgent initialization warning: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down AI Agent API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
