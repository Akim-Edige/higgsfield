# app/api/routes/higgsfield_text2video.py
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai"
HF_API_KEY = os.getenv("HF_API_KEY", "782be287-7c12-4e39-bdde-879b28fe3a5d")
HF_SECRET = os.getenv("HF_SECRET", "76afa0e573c958ee271f9781f3152c0ad5911b5ce7e42d3b5beffef0861f4508")

router = APIRouter(prefix="/higgsfield/text2video", tags=["higgsfield:text2video"])

# ============================
# 🎥 Модели
# ============================
class VideoParams(BaseModel):
    prompt: str = "jon jones vs cormier"
    aspect_ratio: str = "16:9"
    duration: int = 5
    resolution: str = "720"
    camera_fixed: bool = False

class GenerateVideoRequest(BaseModel):
    params: VideoParams = VideoParams()
    webhook: Optional[Dict[str, str]] = None

# ============================
# 🎬 Эндпоинт генерации видео
# ============================
@router.post("/generate")
async def generate_video(request: Optional[GenerateVideoRequest] = None):
    if request is None:
        request = GenerateVideoRequest()

    headers = {
        "Content-Type": "application/json",
        "hf-api-key": HF_API_KEY,
        "hf-secret": HF_SECRET
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{HIGGSFIELD_BASE_URL}/generate/seedance-v1-lite-t2v",
            headers=headers,
            json=request.dict()
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
