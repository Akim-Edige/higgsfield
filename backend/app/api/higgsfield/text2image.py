# app/api/routes/higgsfield_text2image.py
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio

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
    model_name: Optional[str] = "nano-banana"  # Название модели

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
    request_data = request.dict()
    model_name = request.params.model_name.lower()

    # Model-specific parameter handling
    if model_name == "seedream":
        # Remove unused parameters and set required ones
        cleaned_params = {
            "prompt": request_data["params"]["prompt"],
            "quality": "high",  # Always "high" for seedream
            "aspect_ratio": request_data["params"]["aspect_ratio"],
            "input_images": request_data["params"]["input_images"]
        }
        request_data["params"] = cleaned_params
    elif model_name == "nano-banana":
        # Keep only required parameters
        cleaned_params = {
            "prompt": request_data["params"]["prompt"],
            "aspect_ratio": request_data["params"]["aspect_ratio"],
            "input_images": request_data["params"]["input_images"]
        }
        request_data["params"] = cleaned_params

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{HIGGSFIELD_BASE_URL}/text2image/{request.params.model_name}",
            headers=headers,
            json=request_data
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        initial_data = resp.json()
        job_set_id = initial_data["id"]

        # Poll for results
        while True:
            resp = await client.get(f"{HIGGSFIELD_BASE_URL}/job-sets/{job_set_id}", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
            data = resp.json()
            status = data["jobs"][0]["status"]
            
            if status in ["completed", "failed", "nsfw"]:
                if status == "completed":
                    return {
                        "url": data["jobs"][0]["results"]["raw"]["url"],
                        "preview_url": data["jobs"][0]["results"]["min"]["url"]
                    }
                else:
                    return {
                        "job_set_id": job_set_id,
                        "status": status,
                        "error": data["jobs"][0].get("error", "Generation failed")
                    }
                
            await asyncio.sleep(2)  # Wait 2 seconds before next poll


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
