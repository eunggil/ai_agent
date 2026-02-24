"""
AI 모델 프로바이더 추상 기반 클래스
"""
from abc import ABC, abstractmethod
from typing import Optional


class ModelProvider(ABC):
    """LLM 프로바이더 공통 인터페이스"""

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            system: 시스템 프롬프트 (선택)

        Returns:
            생성된 텍스트
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """프로바이더 이름"""
        pass
