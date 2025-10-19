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
    enable_prompt_optimizier: Optional[bool] = None  # For minimax-t2v

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


    # Prepare request data based on model
    request_data = request.dict()
    model_name = request.params.model_name.lower()

    # Model-specific parameter handling
    if model_name == "minimax-t2v":
        # Keep only required parameters for minimax
        cleaned_params = {
            "prompt": request_data["params"]["prompt"],
            "duration": 6,  # Fixed value for minimax
            "enable_prompt_optimizier": True,
            "resolution": "768"  # Fixed value for minimax
        }
        request_data["params"] = cleaned_params
        base_url = f"{HIGGSFIELD_BASE_URL}/generate"
    elif model_name == "seedance-v1-lite-t2v":
        # Keep all required parameters for seedance
        cleaned_params = {
            "prompt": request_data["params"]["prompt"],
            "duration": request_data["params"]["duration"],
            "resolution": request_data["params"]["resolution"],
            "aspect_ratio": request_data["params"]["aspect_ratio"],
            "camera_fixed": request_data["params"]["camera_fixed"]
        }
        request_data["params"] = cleaned_params
        base_url = f"{HIGGSFIELD_BASE_URL}/generate"

    async with httpx.AsyncClient() as client:
        # Initial generation request
        resp = await client.post(
            f"{base_url}/{model_name}",
            headers=headers,
            json=request_data
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
            
            await asyncio.sleep(5)