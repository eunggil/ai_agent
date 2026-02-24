"""
Replicate API 프로바이더 - 클라우드 기반 이미지/영상 생성
로컬 GPU 없이 다양한 모델 사용 가능

설정:
    MEDIA_PROVIDER=replicate
    REPLICATE_API_TOKEN=your-token
    IMAGE_MODEL=lcm-lora-sdxl        # 아래 지원 모델 참고
    VIDEO_MODEL=animate-diff

지원 이미지 모델:
    lcm-lora-sdxl     fofr/lcm-lora-sdxl              빠름, LCM-LoRA
    sdxl              stability-ai/sdxl                고품질
    flux-schnell      black-forest-labs/flux-schnell   최신, 빠름
    flux-dev          black-forest-labs/flux-dev        최신, 고품질

지원 영상 모델:
    animate-diff      lucataco/animate-diff-v2         GIF/MP4 생성
    svd               stability-ai/stable-video-diffusion  이미지→영상

API 토큰:
    https://replicate.com/account/api-tokens

의존성:
    pip install replicate
"""
import base64
import logging
import os
import urllib.request

from .base import MediaProvider, MediaResult

logger = logging.getLogger(__name__)

# 모델 ID 매핑
IMAGE_MODELS = {
    "lcm-lora-sdxl": "fofr/lcm-lora-sdxl:2c90f6e5b59d497efe0b57d05d3d5dca3b8fc0f5f8e45e4b08d10b4de78b553e",
    "sdxl": "stability-ai/sdxl:7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc",
    "flux-schnell": "black-forest-labs/flux-schnell",
    "flux-dev": "black-forest-labs/flux-dev",
}

VIDEO_MODELS = {
    "animate-diff": "lucataco/animate-diff-v2:ad71226753cc7a3e21aa9c34b4f62e8fa5b8fb44d2c48d04ecb98a08e9e8af14",
    "svd": "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
}


class ReplicateProvider(MediaProvider):
    """Replicate API 미디어 생성 프로바이더"""

    def __init__(self):
        self.api_token = os.getenv("REPLICATE_API_TOKEN", "")
        self.image_model_id = os.getenv("IMAGE_MODEL", "lcm-lora-sdxl")
        self.video_model_id = os.getenv("VIDEO_MODEL", "animate-diff")

        if self.api_token:
            os.environ["REPLICATE_API_TOKEN"] = self.api_token

    def _get_client(self):
        try:
            import replicate
            return replicate
        except ImportError:
            raise ImportError(
                "replicate 패키지가 필요합니다.\n"
                "설치: pip install replicate"
            )

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> MediaResult:
        client = self._get_client()

        model_version = IMAGE_MODELS.get(self.image_model_id)
        if not model_version:
            raise ValueError(
                f"지원하지 않는 IMAGE_MODEL='{self.image_model_id}'. "
                f"지원 모델: {list(IMAGE_MODELS.keys())}"
            )

        logger.info(f"[replicate] generating image: model={self.image_model_id}")

        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
        }
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        output = client.run(model_version, input=input_params)

        # output은 URL 리스트 또는 단일 URL
        image_url = output[0] if isinstance(output, list) else output

        # URL에서 이미지 다운로드 → base64
        with urllib.request.urlopen(image_url) as resp:
            image_bytes = resp.read()
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        return MediaResult(
            data=b64,
            data_type="base64",
            media_type="image",
            mime_type="image/png",
            metadata={
                "model": self.image_model_id,
                "model_version": model_version,
                "provider": self.name,
                "width": width,
                "height": height,
                "prompt": prompt[:100],
                "source_url": str(image_url),
            },
        )

    @property
    def supports_video(self) -> bool:
        return True

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 4,
        **kwargs,
    ) -> MediaResult:
        client = self._get_client()

        model_version = VIDEO_MODELS.get(self.video_model_id)
        if not model_version:
            raise ValueError(
                f"지원하지 않는 VIDEO_MODEL='{self.video_model_id}'. "
                f"지원 모델: {list(VIDEO_MODELS.keys())}"
            )

        logger.info(f"[replicate] generating video: model={self.video_model_id}")

        input_params = {"prompt": prompt}
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        output = client.run(model_version, input=input_params)

        video_url = output[0] if isinstance(output, list) else output

        # 다운로드 → base64
        with urllib.request.urlopen(video_url) as resp:
            video_bytes = resp.read()
        b64 = base64.b64encode(video_bytes).decode("utf-8")

        return MediaResult(
            data=b64,
            data_type="base64",
            media_type="video",
            mime_type="video/mp4",
            metadata={
                "model": self.video_model_id,
                "provider": self.name,
                "prompt": prompt[:100],
                "source_url": str(video_url),
            },
        )

    @property
    def name(self) -> str:
        return f"replicate({self.image_model_id})"
