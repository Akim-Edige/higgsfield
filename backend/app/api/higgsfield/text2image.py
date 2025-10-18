# app/api/routes/higgsfield_text2image.py
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from app.core.config import settings

HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai/v1"
HF_API_KEY = settings.HIGGSFIELD_API_KEY
HF_SECRET =  settings.HIGGSFIELD_SECRET

router = APIRouter(prefix="/higgsfield/text2image", tags=["higgsfield:text2image"])

# ============================
# 🔹 Модели
# ============================
class ImageReference(BaseModel):
    type: Optional[str] = None
    image_url: Optional[str] = None

class Params(BaseModel):
    prompt: str = "A cinematic portrait of a woman"
    aspect_ratio: str = "16:9"
    input_images: List[ImageReference] = []
    width_and_height: str = "1152x2048"
    batch_size: int = 1
    style_id: str = "524be50a-4388-4ff5-a843-a73d2dd7ef87"
    enhance_prompt: Optional[bool] = False
    quality: Optional[str] = "1080p"
    style_strength: Optional[float] = 1.0
    seed: Optional[int] = None

class GenerateRequest(BaseModel):
    webhook: Optional[Dict[str, str]] = None
    params: Params = Params()

# ============================
# 🔹 Генерация изображения
# ============================
@router.post("/generate")
async def generate_image(request: Optional[GenerateRequest] = None):
    if request is None:
        request = GenerateRequest()

    headers = {
        "Content-Type": "application/json",
        "hf-api-key": HF_API_KEY,
        "hf-secret": HF_SECRET
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{HIGGSFIELD_BASE_URL}/text2image/nano-banana",
            headers=headers,
            json=request.dict()
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ============================
# 🔹 Получение стилей
# ============================
@router.get("/styles")
async def get_styles():
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HIGGSFIELD_BASE_URL}/text2image/soul-styles", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
