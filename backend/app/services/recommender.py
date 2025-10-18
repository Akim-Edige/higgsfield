"""Recommender service that generates generation options based on user input."""
from __future__ import annotations

import uuid
from typing import Any

from app.services import model_catalog, prompt_enhance


class GenerationOption:
    """A generation option to present to the user."""

    def __init__(
        self,
        rank: int,
        tool_type: str,
        model_key: str,
        parameters: dict,
        enhanced_prompt: str,
        reason: str,
        confidence: float | None = None,
        est_cost: Any = None,
        est_latency_ms: int | None = None,
        requires_attachment: bool = False,
    ):
        self.rank = rank
        self.tool_type = tool_type
        self.model_key = model_key
        self.parameters = parameters
        self.enhanced_prompt = enhanced_prompt
        self.reason = reason
        self.confidence = confidence
        self.est_cost = est_cost
        self.est_latency_ms = est_latency_ms
        self.requires_attachment = requires_attachment


class Recommender:
    """Recommends generation options based on user input."""

    @staticmethod
    def generate_options(
        text: str | None,
        has_attachment: bool = False,
        attachment_meta: dict | None = None,
    ) -> list[GenerationOption]:
        """
        Generate ≥2 diverse options.
        
        Args:
            text: User's text prompt
            has_attachment: Whether user provided an image/video attachment
            attachment_meta: Metadata about the attachment (if present)
        
        Returns:
            List of GenerationOption objects
        """
        options: list[GenerationOption] = []
        rank = 0

        # If attachment present, prioritize image-to-video
        if has_attachment:
            i2v_model = model_catalog.get_model_for_i2v_with_attachment()
            enhanced_prompt, params = prompt_enhance.enhance_prompt(
                "image_to_video",
                text or "",
                dict(i2v_model.defaults),
            )
            options.append(
                GenerationOption(
                    rank=rank,
                    tool_type="image_to_video",
                    model_key=i2v_model.model_key,
                    parameters=params,
                    enhanced_prompt=enhanced_prompt,
                    reason=f"Animate your uploaded image with {i2v_model.display_name}",
                    confidence=0.9,
                    est_cost=i2v_model.est_cost,
                    est_latency_ms=i2v_model.avg_latency_ms,
                    requires_attachment=True,
                )
            )
            rank += 1

        # Always offer fast text-to-image
        t2i_fast = model_catalog.get_model("nano_banana")
        if t2i_fast:
            enhanced_prompt, params = prompt_enhance.enhance_prompt(
                "text_to_image",
                text or "cinematic scene",
                dict(t2i_fast.defaults),
            )
            options.append(
                GenerationOption(
                    rank=rank,
                    tool_type="text_to_image",
                    model_key=t2i_fast.model_key,
                    parameters=params,
                    enhanced_prompt=enhanced_prompt,
                    reason="Fast & low-cost photorealistic image generation",
                    confidence=0.85,
                    est_cost=t2i_fast.est_cost,
                    est_latency_ms=t2i_fast.avg_latency_ms,
                    requires_attachment=False,
                )
            )
            rank += 1

        # Offer cinematic text-to-video
        t2v_cinematic = model_catalog.get_model("kling_21_master")
        if t2v_cinematic:
            enhanced_prompt, params = prompt_enhance.enhance_prompt(
                "text_to_video",
                text or "cinematic scene",
                dict(t2v_cinematic.defaults),
            )
            options.append(
                GenerationOption(
                    rank=rank,
                    tool_type="text_to_video",
                    model_key=t2v_cinematic.model_key,
                    parameters=params,
                    enhanced_prompt=enhanced_prompt,
                    reason="Cinematic video with smooth motion, higher cost & latency",
                    confidence=0.8,
                    est_cost=t2v_cinematic.est_cost,
                    est_latency_ms=t2v_cinematic.avg_latency_ms,
                    requires_attachment=False,
                )
            )
            rank += 1

        # Optionally add another T2V option for diversity
        t2v_fast = model_catalog.get_model("seedance_1_lite")
        if t2v_fast and len(options) < 4:
            enhanced_prompt, params = prompt_enhance.enhance_prompt(
                "text_to_video",
                text or "cinematic scene",
                dict(t2v_fast.defaults),
            )
            options.append(
                GenerationOption(
                    rank=rank,
                    tool_type="text_to_video",
                    model_key=t2v_fast.model_key,
                    parameters=params,
                    enhanced_prompt=enhanced_prompt,
                    reason="Faster text-to-video with lower cost",
                    confidence=0.75,
                    est_cost=t2v_fast.est_cost,
                    est_latency_ms=t2v_fast.avg_latency_ms,
                    requires_attachment=False,
                )
            )
            rank += 1

        return options

