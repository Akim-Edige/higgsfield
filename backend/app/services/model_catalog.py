"""Model catalog with capabilities and pricing info."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ModelInfo:
    """Model information."""

    model_key: str
    tool_type: str  # 'text_to_image', 'text_to_video', 'image_to_video', 'speak'
    display_name: str
    defaults: dict
    avg_latency_ms: int
    est_cost: Decimal
    max_input_length: int | None = None
    max_output_duration_s: int | None = None
    supports_negative_prompt: bool = False
    supports_cfg: bool = False


# Model catalog
MODELS: dict[str, ModelInfo] = {
    # Text-to-Image models
    "nano_banana": ModelInfo(
        model_key="nano_banana",
        tool_type="text_to_image",
        display_name="Nano Banana (Fast T2I)",
        defaults={"steps": 20, "cfg": 7.0, "width": 1024, "height": 1024},
        avg_latency_ms=3000,
        est_cost=Decimal("0.01"),
        max_input_length=500,
        supports_negative_prompt=True,
        supports_cfg=True,
    ),
    "seedream_4": ModelInfo(
        model_key="seedream_4",
        tool_type="text_to_image",
        display_name="SeeDream 4 (Quality T2I)",
        defaults={"steps": 25, "cfg": 7.5, "width": 1024, "height": 1024},
        avg_latency_ms=5000,
        est_cost=Decimal("0.02"),
        max_input_length=1000,
        supports_negative_prompt=True,
        supports_cfg=True,
    ),
    # Text-to-Video models
    "kling_21_master": ModelInfo(
        model_key="kling_21_master",
        tool_type="text_to_video",
        display_name="Kling 2.1 Master (Cinematic T2V)",
        defaults={"duration_s": 5, "fps": 24, "width": 1280, "height": 720},
        avg_latency_ms=120000,
        est_cost=Decimal("0.50"),
        max_input_length=500,
        max_output_duration_s=10,
    ),
    "minimax_hailuo_02": ModelInfo(
        model_key="minimax_hailuo_02",
        tool_type="text_to_video",
        display_name="Minimax Hailuo 0.2 (Versatile T2V/I2V)",
        defaults={"duration_s": 6, "fps": 25, "width": 1280, "height": 720},
        avg_latency_ms=90000,
        est_cost=Decimal("0.40"),
        max_input_length=500,
        max_output_duration_s=10,
    ),
    "seedance_1_lite": ModelInfo(
        model_key="seedance_1_lite",
        tool_type="text_to_video",
        display_name="SeeDance 1 Lite (Fast T2V)",
        defaults={"duration_s": 4, "fps": 24, "width": 1024, "height": 576},
        avg_latency_ms=60000,
        est_cost=Decimal("0.25"),
        max_input_length=300,
        max_output_duration_s=6,
    ),
    # Image-to-Video models
    "kling_25_turbo": ModelInfo(
        model_key="kling_25_turbo",
        tool_type="image_to_video",
        display_name="Kling 2.5 Turbo (Fast I2V)",
        defaults={"duration_s": 5, "fps": 24, "motion_strength": 0.5},
        avg_latency_ms=80000,
        est_cost=Decimal("0.35"),
        max_output_duration_s=10,
    ),
    "wan_25_fast": ModelInfo(
        model_key="wan_25_fast",
        tool_type="image_to_video",
        display_name="Wan 2.5 Fast (I2V)",
        defaults={"duration_s": 5, "fps": 24, "motion_strength": 0.5},
        avg_latency_ms=70000,
        est_cost=Decimal("0.30"),
        max_output_duration_s=10,
    ),
    "veo3": ModelInfo(
        model_key="veo3",
        tool_type="image_to_video",
        display_name="Veo3 (Quality I2V)",
        defaults={"duration_s": 6, "fps": 30, "motion_strength": 0.6},
        avg_latency_ms=100000,
        est_cost=Decimal("0.45"),
        max_output_duration_s=12,
    ),
    # Speak/Audio
    "veo3_speak": ModelInfo(
        model_key="veo3_speak",
        tool_type="speak",
        display_name="Veo3 Speak (TTS)",
        defaults={"voice": "neutral"},
        avg_latency_ms=5000,
        est_cost=Decimal("0.05"),
        max_input_length=500,
    ),
}


def get_model(model_key: str) -> ModelInfo | None:
    """Get model info by key."""
    return MODELS.get(model_key)


def get_models_by_tool_type(tool_type: str) -> list[ModelInfo]:
    """Get all models for a specific tool type."""
    return [m for m in MODELS.values() if m.tool_type == tool_type]


def get_model_for_i2v_with_attachment() -> ModelInfo:
    """Get a suitable image-to-video model when attachment is present."""
    models = get_models_by_tool_type("image_to_video")
    # Return the turbo model as default
    return next((m for m in models if m.model_key == "kling_25_turbo"), models[0])

