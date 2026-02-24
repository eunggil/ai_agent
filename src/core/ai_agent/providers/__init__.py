"""
AI 모델 프로바이더 팩토리

환경변수 AI_PROVIDER로 프로바이더 선택:
    AI_PROVIDER=vertex  → Vertex AI (Gemini)
    AI_PROVIDER=local   → Ollama 로컬 LLM
"""
import os
import logging

from .base import ModelProvider
from .vertex import VertexProvider
from .local import LocalProvider

logger = logging.getLogger(__name__)

_provider_instance: ModelProvider | None = None


def get_provider() -> ModelProvider:
    """싱글턴 프로바이더 반환"""
    global _provider_instance

    if _provider_instance is None:
        provider_name = os.getenv("AI_PROVIDER", "vertex").lower()

        if provider_name == "local":
            _provider_instance = LocalProvider()
            logger.info(f"AI Provider: Local (Ollama) - {_provider_instance.name}")
        elif provider_name == "vertex":
            _provider_instance = VertexProvider()
            logger.info(f"AI Provider: Vertex AI - {_provider_instance.name}")
        else:
            raise ValueError(
                f"Unknown AI_PROVIDER='{provider_name}'. "
                "Valid options: 'vertex', 'local'"
            )

    return _provider_instance


def reset_provider() -> None:
    """테스트용 프로바이더 초기화"""
    global _provider_instance
    _provider_instance = None


__all__ = ["ModelProvider", "VertexProvider", "LocalProvider", "get_provider", "reset_provider"]
