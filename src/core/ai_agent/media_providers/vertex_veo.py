"""
Vertex AI Veo 프로바이더 (영상 생성)

설정:
    MEDIA_PROVIDER=vertex_veo  또는  MEDIA_PROVIDER=vertex
    GCP_PROJECT_ID=your-project-id
    VERTEX_VEO_MODEL=veo-3.1-fast-generate-001
    VERTEX_VEO_GCS_BUCKET=your-bucket-name   ← 필수 (Veo 출력이 GCS에 저장됨)
    GCP_REGION=us-central1

지원 모델 (2026 기준):
    veo-3.1-fast-generate-001    $0.10/초  빠름, 오디오 포함  ← 기본값
    veo-3.1-generate-001         $0.20/초  고품질, 오디오 포함
    veo-3.1-generate-preview     $0.20/초  4K 지원 (Preview)
    veo-2.0-generate-001         $0.50/초  구세대 (비권장)

Veo 주요 특성:
    - 출력 영상이 GCS 버킷에 저장됨 → VERTEX_VEO_GCS_BUCKET 필수
    - 생성에 수십 초~수 분 소요 (비동기 Long-Running Operation)
    - 720p 기본, veo-3.1-generate-preview는 1080p/4K 지원
    - 4~8초 영상 생성 (Veo 3)
    - 오디오 자동 생성 포함 (Veo 3.1)
    - 지원 비율: 16:9 (가로), 9:16 (세로)

GCS 버킷 준비:
    gsutil mb -l us-central1 gs://your-bucket-name
    # 또는 Cloud Console에서 생성

인증:
    gcloud auth application-default login
    서비스 계정에 roles/storage.objectAdmin 권한 필요
"""
import base64
import logging
import os
import time
import uuid
from pathlib import Path

from .base import MediaProvider, MediaResult

logger = logging.getLogger(__name__)

# Veo 3 모델 목록 (duration 및 aspect_ratio 지원)
_VEO3_MODELS = ("veo-3",)
_VEO2_MODELS = ("veo-2",)


class VertexVeoProvider(MediaProvider):
    """Vertex AI Veo 영상 생성 프로바이더"""

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.region = os.getenv("GCP_REGION", "us-central1")
        self.model_name = os.getenv("VERTEX_VEO_MODEL", "veo-3.1-fast-generate-001")
        self.gcs_bucket = os.getenv("VERTEX_VEO_GCS_BUCKET", "")
        self.timeout = int(os.getenv("VEO_TIMEOUT_SECONDS", "600"))  # 최대 10분

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> MediaResult:
        raise NotImplementedError(
            "VertexVeoProvider는 영상 생성 전용입니다. "
            "이미지 생성에는 MEDIA_PROVIDER=vertex_imagen을 사용하세요."
        )

    @property
    def supports_video(self) -> bool:
        return True

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 8,
        **kwargs,
    ) -> MediaResult:
        if not self.gcs_bucket:
            raise ValueError(
                "Veo 영상 생성에는 GCS 버킷이 필요합니다.\n"
                "환경변수 설정: VERTEX_VEO_GCS_BUCKET=your-bucket-name\n"
                "버킷 생성: gsutil mb -l us-central1 gs://your-bucket-name"
            )

        import vertexai

        # VideoGenerationModel은 SDK 버전에 따라 위치가 다를 수 있음
        try:
            from vertexai.preview.vision_models import VideoGenerationModel
        except ImportError:
            from vertexai.vision_models import VideoGenerationModel

        vertexai.init(project=self.project_id, location=self.region)

        # Veo 3: duration 4/6/8초, Veo 2: 4/8초만 지원
        duration_seconds = _clamp_duration(duration_seconds, self.model_name)

        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        gcs_prefix = f"gs://{self.gcs_bucket}/veo_output/{uuid.uuid4().hex}/"

        logger.info(
            f"[vertex_veo] model={self.model_name}, "
            f"duration={duration_seconds}s, output={gcs_prefix}"
        )
        start = time.time()

        model = VideoGenerationModel.from_pretrained(self.model_name)

        params: dict = {
            "prompt": prompt,
            "target_gcs_uri": gcs_prefix,
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "number_of_videos": 1,
        }
        if negative_prompt:
            params["negative_prompt"] = negative_prompt

        # Long-Running Operation 실행
        lro = model.generate_video(**params)

        logger.info(f"[vertex_veo] waiting for operation (timeout={self.timeout}s)...")
        lro.result(timeout=self.timeout)

        elapsed = time.time() - start
        logger.info(f"[vertex_veo] completed in {elapsed:.1f}s")

        # GCS에서 mp4 파일 찾아서 다운로드
        video_bytes = _download_video_from_gcs(self.gcs_bucket, gcs_prefix)
        b64 = base64.b64encode(video_bytes).decode("utf-8")

        return MediaResult(
            data=b64,
            data_type="base64",
            media_type="video",
            mime_type="video/mp4",
            metadata={
                "model": self.model_name,
                "provider": self.name,
                "duration_seconds": duration_seconds,
                "aspect_ratio": aspect_ratio,
                "generation_time_sec": round(elapsed, 2),
                "gcs_output": gcs_prefix,
                "prompt": prompt[:100],
            },
        )

    @property
    def name(self) -> str:
        return f"vertex_veo({self.model_name})"


# ──────────────────────────────────────────
# 통합 프로바이더: 이미지→Imagen, 영상→Veo
# ──────────────────────────────────────────

class VertexUnifiedProvider(MediaProvider):
    """Vertex AI 통합 프로바이더
    - 이미지: Imagen 4
    - 영상:   Veo 3.1
    """

    def __init__(self):
        from .vertex_imagen import VertexImagenProvider
        self._imagen = VertexImagenProvider()
        self._veo = VertexVeoProvider()

    def generate_image(self, prompt, negative_prompt="", width=1024, height=1024, **kwargs):
        return self._imagen.generate_image(prompt, negative_prompt, width, height, **kwargs)

    def generate_video(self, prompt, negative_prompt="", duration_seconds=8, **kwargs):
        return self._veo.generate_video(prompt, negative_prompt, duration_seconds, **kwargs)

    @property
    def supports_video(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return f"vertex({self._imagen.model_name} / {self._veo.model_name})"


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────

def _clamp_duration(duration: int, model_name: str) -> int:
    """모델별 지원 duration으로 보정"""
    if any(tag in model_name for tag in _VEO3_MODELS):
        allowed = [4, 6, 8]
    else:
        allowed = [4, 8]
    return min(allowed, key=lambda x: abs(x - duration))


def _download_video_from_gcs(bucket_name: str, gcs_prefix: str) -> bytes:
    """GCS 경로에서 mp4 파일 다운로드"""
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # prefix 추출 (gs://bucket/path/ → path/)
    prefix = gcs_prefix.replace(f"gs://{bucket_name}/", "")

    blobs = list(bucket.list_blobs(prefix=prefix))
    mp4_blobs = [b for b in blobs if b.name.endswith(".mp4")]

    if not mp4_blobs:
        raise RuntimeError(
            f"GCS에서 영상 파일을 찾을 수 없습니다: {gcs_prefix}\n"
            "Veo 생성이 완료되지 않았거나 권한 문제일 수 있습니다."
        )

    # 가장 최근 파일 선택
    mp4_blobs.sort(key=lambda b: b.updated, reverse=True)
    logger.info(f"[vertex_veo] downloading: {mp4_blobs[0].name}")
    return mp4_blobs[0].download_as_bytes()
