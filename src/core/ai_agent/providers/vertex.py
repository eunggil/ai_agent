"""
Vertex AI (Gemini) 프로바이더
옵션 1: 로컬에서 GCP 인증으로 실제 Gemini 호출

설정:
    AI_PROVIDER=vertex
    GCP_PROJECT_ID=your-project-id
    GCP_REGION=us-central1
    VERTEX_AI_MODEL=gemini-2.0-flash

인증:
    gcloud auth application-default login
    또는 GOOGLE_APPLICATION_CREDENTIALS 환경변수로 서비스 계정 키 경로 지정
"""
import os
import logging
from typing import Optional

from .base import ModelProvider

logger = logging.getLogger(__name__)


class VertexProvider(ModelProvider):
    """Vertex AI Gemini 프로바이더"""

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.region = os.getenv("GCP_REGION", os.getenv("VERTEX_AI_LOCATION", "us-central1"))
        self.model_name = os.getenv("VERTEX_AI_MODEL", "gemini-2.0-flash")
        self.temperature = float(os.getenv("VERTEX_AI_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("VERTEX_AI_MAX_TOKENS", "2048"))
        self._model = None

    def _get_model(self):
        if self._model is None:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=self.project_id, location=self.region)
            self._model = GenerativeModel(self.model_name)
            logger.info(f"Vertex AI initialized: project={self.project_id}, model={self.model_name}")

        return self._model

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        model = self._get_model()

        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        from vertexai.generative_models import GenerationConfig
        response = model.generate_content(
            full_prompt,
            generation_config=GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        return response.text

    @property
    def name(self) -> str:
        return "vertex"
