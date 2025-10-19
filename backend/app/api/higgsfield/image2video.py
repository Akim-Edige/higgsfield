# app/api/routes/higgsfield_image2video.py
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.config import settings
import asyncio

HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai/v1"
HIGGSFIELD_BASE_URL2 = "https://platform.higgsfield.ai"

HF_API_KEY = settings.HIGGSFIELD_API_KEY

HF_SECRET =  settings.HIGGSFIELD_SECRET

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/higgsfield/image2video", tags=["higgsfield:image2video"])

# ============================
# 🔹 Модели
# ============================
class ImageReference(BaseModel):
    type: str = Field("image_url", description="Type of image reference")
    image_url: str = Field(..., description="URL of the input image")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "image_url",
                "image_url": "https://example.com/image.jpg"
            }
        }

class MotionRef(BaseModel):
    id: str
    strength: float = 0.5

class Webhook(BaseModel):
    url: Optional[str] = None
    secret: Optional[str] = None

class Image2VideoParams(BaseModel):
    model: Optional[str] = Field(None, description="For specific models like kling-v2-5-turbo")
    prompt: str = "A cinematic portrait of a woman turning her head slightly"
    prompts: Optional[List[str]] = None
    seed: Optional[int] = 1
    duration: int = 5
    resolution: Optional[str] = "720"
    input_image: ImageReference
    enhance_prompt: bool = True
    model_name: str = "seedance"
    negative_prompt: Optional[str] = ""
    input_audio: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "seedance",
                "prompt": "A cinematic portrait",
                "duration": 5,
                "resolution": "720",
                "input_image": {
                    "type": "image_url",
                    "image_url": "https://example.com/image.jpg"
                },
                "enhance_prompt": True
            }
        }

class Image2VideoRequest(BaseModel):
    webhook: Optional[Webhook] = None
    params: Image2VideoParams


# ============================
# 🔹 Генерация видео
# ============================
@router.post("/generate")
async def generate_image2video(request: Image2VideoRequest):
    params = request.params
    headers = {
        "Content-Type": "application/json",
        "hf-api-key": HF_API_KEY,
        "hf-secret": HF_SECRET,
    }

    if not params.input_image or not params.input_image.image_url:
        raise HTTPException(status_code=400, detail="input_image is required")
    
    request_data = request.dict()
    model_name = params.model_name.lower()
    
    # Define base URLs and endpoints based on model
    if model_name in ["kling-2-5", "wan-25-fast"]:
        base_url = f"{HIGGSFIELD_BASE_URL2}/generate/{model_name}"
        
        if model_name == "kling-2-5":
            cleaned_params = {
                "params": {  # Wrap in params object
                    "model": "kling-v2-5-turbo",
                    "prompt": params.prompt,
                    "duration": params.duration,
                    "input_image": params.input_image.dict(),
                    "enhance_prompt": params.enhance_prompt
                }
            }
        else:  # wan-25-fast
            cleaned_params = {
                "seed": params.seed,
                "prompt": params.prompt,
                "duration": params.duration,
                "resolution": "720p",  # Must be "720p" not "720"
                "input_audio": None,
                "input_image": params.input_image.dict(),
                "enhance_prompt": False,  # Must be False for wan-25-fast
                "negative_prompt": ""  # Empty string by default
            }

    elif model_name == "minimax":
        base_url = f"{HIGGSFIELD_BASE_URL}/image2video/minimax"
        cleaned_params = {
            "prompt": params.prompt,
            "duration": 6,  # Must be 6
            "resolution": "768",
            "input_image": params.input_image.dict(),
            "input_image_end": params.input_image.dict(),  # Required by minimax
            "enhance_prompt": True
        }

    elif model_name == "seedance":
        base_url = f"{HIGGSFIELD_BASE_URL}/image2video/seedance"
        cleaned_params = {
            "model": "seedance_pro",
            "prompts": [params.prompt],  # Must be array
            "duration": params.duration,
            "resolution": "1080",  # Using 1080 as default for seedance
            "input_image": params.input_image.dict(),
            "enhance_prompt": params.enhance_prompt
        }

    # Construct final request payload
    request_data = {
        "webhook": request.webhook.dict() if request.webhook else None,
        "params": cleaned_params
    }

    async with httpx.AsyncClient() as client:
        # Initial generation request
        resp = await client.post(
            base_url,
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
                        "url": data["jobs"][0]["results"]["raw"]["url"]
                    }
                else:
                    return data
            
            # Wait between polls since image2video generation can take time
            await asyncio.sleep(5)  # 5 second polling interval
