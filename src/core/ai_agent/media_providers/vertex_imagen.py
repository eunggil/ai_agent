"""
Vertex AI Imagen 프로바이더 (이미지 생성)

설정:
    MEDIA_PROVIDER=vertex_imagen  또는  MEDIA_PROVIDER=vertex
    GCP_PROJECT_ID=your-project-id
    VERTEX_AI_IMAGEN_MODEL=imagen-4.0-generate-001
    GCP_REGION=us-central1

지원 모델 (2026 기준):
    imagen-4.0-generate-001        Imagen 4 표준  $0.04/장  ← 기본값
    imagen-4.0-fast-generate-001   Imagen 4 Fast  $0.02/장  (권장, 속도 우선)
    imagen-4.0-ultra-generate-001  Imagen 4 Ultra $0.06/장  (최고품질)
    imagen-3.0-generate-002        Imagen 3       더 저렴    (구세대)
    imagen-3.0-fast-generate-001   Imagen 3 Fast  더 저렴

Imagen 4 제약사항:
    - 이미지 편집(inpainting/outpainting) 미지원 (Imagen 3에서만 가능)
    - width/height 대신 aspect_ratio 사용
    - SynthID 워터마크 기본 삽입 (add_watermark=False로 비활성화 가능)

인증:
    gcloud auth application-default login
    또는 GOOGLE_APPLICATION_CREDENTIALS 환경변수
"""
import base64
import logging
import os
import tempfile

from .base import MediaProvider, MediaResult

logger = logging.getLogger(__name__)

# aspect_ratio를 사용하는 모델 (Imagen 3+)
_ASPECT_RATIO_MODELS = ("imagen-3", "imagen-4")


class VertexImagenProvider(MediaProvider):
    """Vertex AI Imagen 이미지 생성 프로바이더 (Imagen 4 기본)"""

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.region = os.getenv("GCP_REGION", "us-central1")
        self.model_name = os.getenv("VERTEX_AI_IMAGEN_MODEL", "imagen-4.0-generate-001")
        self.add_watermark = os.getenv("IMAGEN_WATERMARK", "false").lower() == "true"

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> MediaResult:
        import vertexai
        from vertexai.vision_models import ImageGenerationModel

        vertexai.init(project=self.project_id, location=self.region)
        model = ImageGenerationModel.from_pretrained(self.model_name)

        logger.info(f"[vertex_imagen] model={self.model_name}, size={width}x{height}")

        params: dict = {
            "prompt": prompt,
            "number_of_images": 1,
            "add_watermark": self.add_watermark,
        }

        if negative_prompt:
            params["negative_prompt"] = negative_prompt

        # Imagen 3/4: aspect_ratio 사용 / Imagen 2(imagegeneration@xxx): width/height 사용
        if any(tag in self.model_name for tag in _ASPECT_RATIO_MODELS):
            params["aspect_ratio"] = _to_aspect_ratio(width, height)
        else:
            params["width"] = width
            params["height"] = height

        response = model.generate_images(**params)
        image = response.images[0]

        image_bytes = _extract_image_bytes(image)
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        return MediaResult(
            data=b64,
            data_type="base64",
            media_type="image",
            mime_type="image/png",
            metadata={
                "model": self.model_name,
                "provider": self.name,
                "aspect_ratio": _to_aspect_ratio(width, height),
                "prompt": prompt[:100],
            },
        )

    @property
    def name(self) -> str:
        return f"vertex_imagen({self.model_name})"


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────

def _to_aspect_ratio(width: int, height: int) -> str:
    ratio = width / height
    candidates = {
        "1:1":  1.0,
        "16:9": 16 / 9,
        "9:16": 9 / 16,
        "4:3":  4 / 3,
        "3:4":  3 / 4,
    }
    return min(candidates, key=lambda k: abs(candidates[k] - ratio))


def _extract_image_bytes(image) -> bytes:
    """SDK 버전별 이미지 바이트 추출"""
    if hasattr(image, "_image_bytes") and image._image_bytes:
        return image._image_bytes
    if hasattr(image, "image_bytes") and image.image_bytes:
        return image.image_bytes
    # 임시 파일을 통해 추출 (구버전 SDK fallback)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        image.save(f.name)
        with open(f.name, "rb") as img_f:
            return img_f.read()
