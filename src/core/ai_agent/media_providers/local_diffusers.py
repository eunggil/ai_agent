"""
로컬 Diffusers 프로바이더 - LCM-LoRA 기반 고속 이미지/영상 생성

설정:
    MEDIA_PROVIDER=local_diffusers
    IMAGE_MODEL=lcm-lora-sdxl        # 모델 선택 (아래 지원 목록 참고)
    DIFFUSERS_DEVICE=auto            # auto | cuda | mps | cpu
    MEDIA_OUTPUT_DIR=/tmp/ai_agent_media

지원 이미지 모델:
    lcm-lora-sdxl    SDXL + LCM-LoRA   4~8스텝, 빠름, 고품질 (VRAM 8GB+)
    lcm-lora-sd15    SD1.5 + LCM-LoRA  4~8스텝, 빠름, 가벼움  (VRAM 4GB+)
    sdxl             SDXL 기본          20스텝, 느림, 최고품질  (VRAM 8GB+)
    sd15             SD1.5 기본         20스텝, 느림, 가벼움   (VRAM 4GB+)

지원 영상 모델:
    animatediff-lcm  AnimateDiff + LCM  4스텝 gif/mp4 생성     (VRAM 8GB+)

의존성 설치:
    pip install -r requirements-media.txt

Mac (Apple Silicon) 안내:
    - Docker 내부에서는 MPS 미지원 (CPU 사용, 느림)
    - 호스트에서 직접 실행 시 MPS 가속 가능:
      MEDIA_PROVIDER=local_diffusers uvicorn src.api.main:app --reload
"""
import base64
import logging
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

from .base import MediaProvider, MediaResult

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# 모델 설정 레지스트리
# ──────────────────────────────────────────
IMAGE_MODEL_CONFIGS = {
    "lcm-lora-sdxl": {
        "base_model": "stabilityai/stable-diffusion-xl-base-1.0",
        "lora_model": "latent-consistency/lcm-lora-sdxl",
        "scheduler": "LCMScheduler",
        "num_inference_steps": 4,
        "guidance_scale": 1.0,
        "pipeline_class": "StableDiffusionXLPipeline",
    },
    "lcm-lora-sd15": {
        "base_model": "runwayml/stable-diffusion-v1-5",
        "lora_model": "latent-consistency/lcm-lora-sdv1-5",
        "scheduler": "LCMScheduler",
        "num_inference_steps": 4,
        "guidance_scale": 1.0,
        "pipeline_class": "StableDiffusionPipeline",
    },
    "sdxl": {
        "base_model": "stabilityai/stable-diffusion-xl-base-1.0",
        "lora_model": None,
        "scheduler": "EulerDiscreteScheduler",
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "pipeline_class": "StableDiffusionXLPipeline",
    },
    "sd15": {
        "base_model": "runwayml/stable-diffusion-v1-5",
        "lora_model": None,
        "scheduler": "EulerDiscreteScheduler",
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "pipeline_class": "StableDiffusionPipeline",
    },
}

VIDEO_MODEL_CONFIGS = {
    "animatediff-lcm": {
        "base_model": "emilianJR/epiCRealism",
        "motion_adapter": "wangfuyun/AnimateLCM",
        "num_inference_steps": 6,
        "guidance_scale": 2.0,
        "num_frames": 16,
    },
}


def _get_device() -> str:
    device = os.getenv("DIFFUSERS_DEVICE", "auto")
    if device != "auto":
        return device

    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def _get_torch_dtype(device: str):
    try:
        import torch
        if device in ("cuda", "mps"):
            return torch.float16
        return torch.float32
    except ImportError:
        return None


class LocalDiffusersProvider(MediaProvider):
    """Diffusers 기반 로컬 이미지/영상 생성 프로바이더"""

    def __init__(self):
        self.image_model_id = os.getenv("IMAGE_MODEL", "lcm-lora-sdxl")
        self.video_model_id = os.getenv("VIDEO_MODEL", "animatediff-lcm")
        self.output_dir = Path(os.getenv("MEDIA_OUTPUT_DIR", "/tmp/ai_agent_media"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.device = _get_device()
        self._image_pipeline = None
        self._video_pipeline = None

        logger.info(
            f"[local_diffusers] device={self.device}, "
            f"image_model={self.image_model_id}, "
            f"video_model={self.video_model_id}"
        )

    # ──────────────────────────────────────
    # 이미지 생성
    # ──────────────────────────────────────

    def _load_image_pipeline(self):
        """이미지 파이프라인 지연 로드"""
        if self._image_pipeline is not None:
            return self._image_pipeline

        try:
            import torch
            from diffusers import (
                DiffusionPipeline,
                LCMScheduler,
                EulerDiscreteScheduler,
                StableDiffusionPipeline,
                StableDiffusionXLPipeline,
            )
        except ImportError:
            raise ImportError(
                "diffusers와 torch가 필요합니다.\n"
                "설치: pip install -r requirements-media.txt"
            )

        cfg = IMAGE_MODEL_CONFIGS.get(self.image_model_id)
        if not cfg:
            raise ValueError(
                f"지원하지 않는 IMAGE_MODEL='{self.image_model_id}'. "
                f"지원 모델: {list(IMAGE_MODEL_CONFIGS.keys())}"
            )

        logger.info(f"[local_diffusers] loading image pipeline: {cfg['base_model']}")
        start = time.time()

        dtype = _get_torch_dtype(self.device)

        # 파이프라인 로드
        PipelineClass = (
            StableDiffusionXLPipeline
            if cfg["pipeline_class"] == "StableDiffusionXLPipeline"
            else StableDiffusionPipeline
        )

        pipe = PipelineClass.from_pretrained(
            cfg["base_model"],
            torch_dtype=dtype,
            variant="fp16" if self.device != "cpu" else None,
        )

        # LCM-LoRA 적용
        if cfg["lora_model"]:
            pipe.load_lora_weights(cfg["lora_model"])
            pipe.fuse_lora()

        # 스케줄러 교체
        if cfg["scheduler"] == "LCMScheduler":
            pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
        else:
            pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)

        pipe = pipe.to(self.device)

        # 메모리 최적화
        if self.device == "cuda":
            pipe.enable_xformers_memory_efficient_attention()

        self._image_pipeline = (pipe, cfg)
        logger.info(f"[local_diffusers] pipeline loaded in {time.time() - start:.1f}s")
        return self._image_pipeline

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        **kwargs,
    ) -> MediaResult:
        pipe, cfg = self._load_image_pipeline()

        num_steps = kwargs.get("num_inference_steps", cfg["num_inference_steps"])
        guidance = kwargs.get("guidance_scale", cfg["guidance_scale"])

        logger.info(
            f"[local_diffusers] generating image: steps={num_steps}, "
            f"device={self.device}, size={width}x{height}"
        )
        start = time.time()

        gen_kwargs = dict(
            prompt=prompt,
            num_inference_steps=num_steps,
            guidance_scale=guidance,
            width=width,
            height=height,
        )
        if negative_prompt:
            gen_kwargs["negative_prompt"] = negative_prompt

        result = pipe(**gen_kwargs)
        image = result.images[0]

        elapsed = time.time() - start
        logger.info(f"[local_diffusers] image generated in {elapsed:.1f}s")

        # PIL Image → base64
        buf = BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        # 파일로도 저장 (디버깅용)
        ts = int(time.time())
        file_path = self.output_dir / f"image_{ts}.png"
        image.save(str(file_path))

        return MediaResult(
            data=b64,
            data_type="base64",
            media_type="image",
            mime_type="image/png",
            metadata={
                "model": self.image_model_id,
                "base_model": cfg["base_model"],
                "lora": cfg.get("lora_model"),
                "provider": self.name,
                "device": self.device,
                "num_steps": num_steps,
                "guidance_scale": guidance,
                "width": width,
                "height": height,
                "generation_time_sec": round(elapsed, 2),
                "saved_path": str(file_path),
                "prompt": prompt[:100],
            },
        )

    # ──────────────────────────────────────
    # 영상 생성 (AnimateDiff + LCM)
    # ──────────────────────────────────────

    @property
    def supports_video(self) -> bool:
        return True

    def _load_video_pipeline(self):
        if self._video_pipeline is not None:
            return self._video_pipeline

        try:
            import torch
            from diffusers import AnimateDiffPipeline, LCMScheduler, MotionAdapter
            from diffusers.utils import export_to_gif
        except ImportError:
            raise ImportError(
                "diffusers와 torch가 필요합니다.\n"
                "설치: pip install -r requirements-media.txt"
            )

        cfg = VIDEO_MODEL_CONFIGS.get(self.video_model_id)
        if not cfg:
            raise ValueError(
                f"지원하지 않는 VIDEO_MODEL='{self.video_model_id}'. "
                f"지원 모델: {list(VIDEO_MODEL_CONFIGS.keys())}"
            )

        logger.info(f"[local_diffusers] loading video pipeline: {cfg['base_model']}")

        dtype = _get_torch_dtype(self.device)

        adapter = MotionAdapter.from_pretrained(
            cfg["motion_adapter"],
            torch_dtype=dtype,
        )
        pipe = AnimateDiffPipeline.from_pretrained(
            cfg["base_model"],
            motion_adapter=adapter,
            torch_dtype=dtype,
        )
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
        pipe = pipe.to(self.device)

        self._video_pipeline = (pipe, cfg)
        return self._video_pipeline

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 4,
        **kwargs,
    ) -> MediaResult:
        from diffusers.utils import export_to_gif

        pipe, cfg = self._load_video_pipeline()

        num_frames = kwargs.get("num_frames", cfg["num_frames"])
        num_steps = kwargs.get("num_inference_steps", cfg["num_inference_steps"])
        guidance = kwargs.get("guidance_scale", cfg["guidance_scale"])

        logger.info(f"[local_diffusers] generating video: frames={num_frames}, steps={num_steps}")
        start = time.time()

        gen_kwargs = dict(
            prompt=prompt,
            num_frames=num_frames,
            num_inference_steps=num_steps,
            guidance_scale=guidance,
        )
        if negative_prompt:
            gen_kwargs["negative_prompt"] = negative_prompt

        result = pipe(**gen_kwargs)
        frames = result.frames[0]

        elapsed = time.time() - start
        logger.info(f"[local_diffusers] video generated in {elapsed:.1f}s")

        # GIF로 저장
        ts = int(time.time())
        gif_path = self.output_dir / f"video_{ts}.gif"
        export_to_gif(frames, str(gif_path))

        with open(gif_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return MediaResult(
            data=b64,
            data_type="base64",
            media_type="video",
            mime_type="image/gif",
            metadata={
                "model": self.video_model_id,
                "provider": self.name,
                "device": self.device,
                "num_frames": num_frames,
                "num_steps": num_steps,
                "generation_time_sec": round(elapsed, 2),
                "saved_path": str(gif_path),
                "prompt": prompt[:100],
            },
        )

    @property
    def name(self) -> str:
        return f"local_diffusers({self.image_model_id})"
