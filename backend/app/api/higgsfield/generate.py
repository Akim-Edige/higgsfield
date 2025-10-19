# app/api/higgsfield/generate.py
"""
Универсальный эндпоинт генерации с использованием сохранённых параметров из Option
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.infra.db import get_db
from app.domain.models import Option, Message

# Импортируем существующие эндпоинты
from .text2image import generate_image, GenerateRequest as T2IRequest, Params as T2IParams
from .text2video import generate_video, GenerateVideoRequest, VideoParams
from .image2video import generate_image2video, Image2VideoRequest, Image2VideoParams, ImageReference, MotionRef

router = APIRouter(prefix="/higgsfield", tags=["higgsfield:generate"])


# ============================
# 📋 Модели запроса/ответа
# ============================
class GenerateRequest(BaseModel):
    option_id: str  # UUID опции с enhanced_prompt и style_id
    image_url: Optional[str] = None  # Для image2video режима
    mode: Literal["text-to-image", "image-to-video", "text-to-video"]
    model_name: Optional[str] = "nano-banana"  # Для text2image
    
    # Дополнительные параметры (опционально)
    aspect_ratio: Optional[str] = "16:9"
    duration: Optional[int] = 5  # Для video
    resolution: Optional[str] = "720"  # Для text2video
    quality: Optional[str] = "1080p"  # Для text2image
    style_strength: Optional[float] = 1.0  # Для text2image
    enhance_prompt: Optional[bool] = False  # Prompt уже enhanced
    seed: Optional[int] = None
    motion_strength: Optional[float] = 0.5  # Для image2video


# ============================
# 🎯 Универсальный эндпоинт
# ============================
@router.post("/generate")
async def generate(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Универсальный эндпоинт генерации:
    1. Получает option_id и вытаскивает enhanced_prompt и style_id
    2. В зависимости от mode вызывает соответствующий Higgsfield эндпоинт
    3. Возвращает job_id и URL результата
    """
    
    # 1️⃣ Получаем Option из БД
    try:
        option_uuid = uuid.UUID(request.option_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid option_id format")
    
    result = await db.execute(
        select(Option).where(Option.id == option_uuid)
    )
    option = result.scalar_one_or_none()
    
    if not option:
        raise HTTPException(status_code=404, detail=f"Option {request.option_id} not found")
    
    if option.result_url:
        return {
            "url": option.result_url
        }
    
    enhanced_prompt = option.enhanced_prompt
    style_id = option.style_id
    
    # 2️⃣ Вызываем соответствующий эндпоинт в зависимости от mode
    result = None
    
    if request.mode == "text-to-image":
        # Формируем запрос для text2image
        t2i_request = T2IRequest(
            params=T2IParams(
                prompt=enhanced_prompt,
                aspect_ratio=request.aspect_ratio,
                style_id=style_id,
                quality=request.quality,
                style_strength=request.style_strength,
                enhance_prompt=request.enhance_prompt,
                seed=request.seed,
                batch_size=1,
                input_images=[],
                model_name=request.model_name  # Передаём model_name
            )
        )
        result = await generate_image(t2i_request)
    
    elif request.mode == "image-to-video":
        if not request.image_url:
            raise HTTPException(
                status_code=400, 
                detail="image_url is required for image-to-video mode"
            )
        
        # Формируем запрос для image2video
        motions = None
        if style_id:  # style_id это motion_id для video
            motions = [MotionRef(id=style_id, strength=request.motion_strength)]
        
        i2v_request = Image2VideoRequest(
            params=Image2VideoParams(
                model="veo-3-fast",
                prompt=enhanced_prompt,
                input_image=ImageReference(
                    type="image_url",
                    image_url=request.image_url
                ),
                enhance_prompt=request.enhance_prompt,
                seed=request.seed,
                motions=motions,
                model_name=request.model_name or "veo3"  # Передаём model_name
            )
        )
        result = await generate_image2video(i2v_request)
    
    elif request.mode == "text-to-video":
        # Формируем запрос для text2video
        t2v_request = GenerateVideoRequest(
            params=VideoParams(
                prompt=enhanced_prompt,
                aspect_ratio=request.aspect_ratio,
                duration=request.duration,
                resolution=request.resolution,
                camera_fixed=False,
                model_name=request.model_name or "seedance-v1-lite-t2v"  # Передаём model_name
            )
        )
        result = await generate_video(t2v_request)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {request.mode}")
    
    # 3️⃣ Сохраняем URL результата в Option
    if result and "url" in result:
        option.result_url = result["url"]
        await db.commit()
        await db.refresh(option)
    
    return result
