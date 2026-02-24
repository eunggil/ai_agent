"""
미디어 생성 프로바이더 팩토리

환경변수 MEDIA_PROVIDER로 프로바이더 선택:
    none             텍스트만 생성 (기본값)
    ─────────────────────────────────────────
    vertex           Imagen(이미지) + Veo(영상) 자동 선택  ← Vertex AI 권장
    vertex_imagen    Imagen 이미지만
    vertex_veo       Veo 영상만
    ─────────────────────────────────────────
    local_diffusers  로컬 GPU + Diffusers (LCM-LoRA)
    replicate        Replicate API (클라우드, 다양한 모델)

이미지 모델 선택 (IMAGE_MODEL):
    ── Vertex AI (vertex / vertex_imagen) ──
    imagen-4.0-generate-001        Imagen 4 표준  $0.04/장
    imagen-4.0-fast-generate-001   Imagen 4 Fast  $0.02/장  ← 기본값
    imagen-4.0-ultra-generate-001  Imagen 4 Ultra $0.06/장

    ── Local Diffusers / Replicate ─────────
    lcm-lora-sdxl    SDXL + LCM-LoRA  4스텝, 빠름
    lcm-lora-sd15    SD1.5 + LCM-LoRA 4스텝, 가벼움
    sdxl             SDXL 기본
    flux-schnell     Flux Schnell      (replicate 전용)

영상 모델 선택 (VIDEO_MODEL):
    ── Vertex AI (vertex / vertex_veo) ─────
    veo-3.1-fast-generate-001   $0.10/초  오디오 포함  ← 기본값
    veo-3.1-generate-001        $0.20/초  고품질
    veo-3.1-generate-preview    $0.20/초  4K 지원

    ── Local Diffusers ─────────────────────
    animatediff-lcm  AnimateDiff + LCM

    ── Replicate ───────────────────────────
    animate-diff     AnimateDiff v2
    svd              Stable Video Diffusion
"""
import logging
import os
from typing import Optional

from .base import MediaProvider, MediaResult

logger = logging.getLogger(__name__)

_media_provider_instance: Optional[MediaProvider] = None


def get_media_provider() -> Optional[MediaProvider]:
    """싱글턴 미디어 프로바이더 반환 (MEDIA_PROVIDER=none 이면 None)"""
    global _media_provider_instance

    if _media_provider_instance is not None:
        return _media_provider_instance

    provider_name = os.getenv("MEDIA_PROVIDER", "none").lower()

    if provider_name == "none":
        logger.info("Media Provider: none (텍스트 전용 모드)")
        return None

    elif provider_name == "vertex":
        # 이미지 → Imagen 4, 영상 → Veo 3.1 자동 선택
        from .vertex_veo import VertexUnifiedProvider
        _media_provider_instance = VertexUnifiedProvider()

    elif provider_name == "vertex_imagen":
        from .vertex_imagen import VertexImagenProvider
        _media_provider_instance = VertexImagenProvider()

    elif provider_name == "vertex_veo":
        from .vertex_veo import VertexVeoProvider
        _media_provider_instance = VertexVeoProvider()

    elif provider_name == "local_diffusers":
        from .local_diffusers import LocalDiffusersProvider
        _media_provider_instance = LocalDiffusersProvider()

    elif provider_name == "replicate":
        from .replicate_provider import ReplicateProvider
        _media_provider_instance = ReplicateProvider()

    else:
        raise ValueError(
            f"Unknown MEDIA_PROVIDER='{provider_name}'.\n"
            "Valid: vertex, vertex_imagen, vertex_veo, local_diffusers, replicate, none"
        )

    logger.info(f"Media Provider: {_media_provider_instance.name}")
    return _media_provider_instance


def reset_media_provider() -> None:
    """테스트용 초기화"""
    global _media_provider_instance
    _media_provider_instance = None


__all__ = [
    "MediaProvider",
    "MediaResult",
    "get_media_provider",
    "reset_media_provider",
]
