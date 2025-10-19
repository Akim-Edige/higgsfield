# app/api/routes/higgsfield_text2video.py
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from app.core.config import settings
import asyncio

HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai"

HF_API_KEY = settings.HIGGSFIELD_API_KEY
HF_SECRET =  settings.HIGGSFIELD_SECRET

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
    model_name: Optional[str] = "seedance-v1-lite-t2v"  # Название модели

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
        # Initial generation request
        resp = await client.post(
            f"{HIGGSFIELD_BASE_URL}/generate/{request.params.model_name}",
            headers=headers,
            json=request.dict()
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        initial_data = resp.json()
        job_set_id = initial_data["id"]

        # Poll for results
        while True:
            resp = await client.get(f"{HIGGSFIELD_BASE_URL}/v1/job-sets/{job_set_id}", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
            data = resp.json()
            status = data["jobs"][0]["status"]
            
            if status in ["completed", "failed", "nsfw"]:
                if status == "completed":
                    return {
                        "url": data["jobs"][0]["results"]["raw"]["url"]
                    }
                else:
                    return {
                        "job_set_id": job_set_id,
                        "status": status,
                        "error": data["jobs"][0].get("error", "Generation failed")
                    }
            
            # Wait longer for video generation since it typically takes more time
            await asyncio.sleep(5)  # 5 second polling interval for videos

