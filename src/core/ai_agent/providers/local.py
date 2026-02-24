"""
로컬 LLM 프로바이더 (Ollama)
옵션 2: 로컬 LLM으로 Vertex AI 대체

설정:
    AI_PROVIDER=local
    OLLAMA_BASE_URL=http://localhost:11434  # 로컬 직접 실행 시
    OLLAMA_BASE_URL=http://ollama:11434     # Docker Compose 내부 통신 시
    LOCAL_MODEL=llama3                      # 또는 mistral, gemma2 등

Ollama 설치:
    macOS: brew install ollama && ollama serve
    모델 다운로드: ollama pull llama3
"""
import os
import logging
from typing import Optional

import httpx

from .base import ModelProvider

logger = logging.getLogger(__name__)


class LocalProvider(ModelProvider):
    """Ollama 기반 로컬 LLM 프로바이더"""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LOCAL_MODEL", "llama3")
        self.timeout = float(os.getenv("LOCAL_MODEL_TIMEOUT", "120"))

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        logger.debug(f"Ollama request: model={self.model}, url={self.base_url}")

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["response"]

    def is_running(self) -> bool:
        """Ollama 서버 실행 여부 확인"""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    @property
    def name(self) -> str:
        return f"local({self.model})"
