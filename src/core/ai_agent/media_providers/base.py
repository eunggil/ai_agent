"""
미디어 생성 프로바이더 추상 기반 클래스
"""
from abc import ABC, abstractmethod
from typing import Optional


class MediaResult:
    """미디어 생성 결과"""

    def __init__(
        self,
        data: str,               # base64 인코딩된 바이너리 또는 파일 경로
        data_type: str,          # "base64" | "file_path" | "url"
        media_type: str,         # "image" | "video"
        mime_type: str,          # "image/png" | "image/jpeg" | "video/mp4"
        metadata: dict,
    ):
        self.data = data
        self.data_type = data_type
        self.media_type = media_type
        self.mime_type = mime_type
        self.metadata = metadata

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "data_type": self.data_type,
            "media_type": self.media_type,
            "mime_type": self.mime_type,
            "metadata": self.metadata,
        }


class MediaProvider(ABC):
    """미디어 생성 프로바이더 공통 인터페이스"""

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> MediaResult:
        pass

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 4,
        **kwargs,
    ) -> MediaResult:
        raise NotImplementedError(f"{self.name} does not support video generation")

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def supports_video(self) -> bool:
        return False
