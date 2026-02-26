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


def upload_to_gcs_public(data: bytes, bucket_name: str, blob_name: str, content_type: str) -> str:
    """GCS에 파일을 업로드하고 public URL을 반환합니다.

    버킷에 allUsers Storage Object Viewer IAM 권한이 필요합니다
    (Uniform bucket-level access 환경):
        gsutil iam ch allUsers:objectViewer gs://BUCKET_NAME
    """
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)
    # Uniform bucket-level access 환경에서는 IAM으로 공개 설정
    # → ACL API 대신 URL을 직접 구성
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
