# app/api/routes/higgsfield_image2video.py
import os
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
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
    type: str = Field("image_url")
    image_url: str

class MotionRef(BaseModel):
    id: str
    strength: float = 0.5

class Webhook(BaseModel):
    url: Optional[str] = None
    secret: Optional[str] = None

class Image2VideoParams(BaseModel):
    model: Optional[str] = None  # For specific models like "kling-v2-5-turbo"
    prompt: str = "A cinematic portrait of a woman turning her head slightly"
    prompts: Optional[List[str]] = None  # For seedance
    seed: Optional[int] = -1  # For wan-25-fast
    duration: int = 5
    resolution: Optional[str] = "720"
    input_image: ImageReference
    enhance_prompt: bool = True
    model_name: str = "seedance"  # Default model name for endpoint
    negative_prompt: Optional[str] = ""  # For wan-25-fast
    input_audio: Optional[dict] = None  # For wan-25-fast

class Image2VideoRequest(BaseModel):
    webhook: Optional[Webhook] = None
    params: Image2VideoParams

# ============================
# 🔹 Загрузка изображений
# ============================
@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"url": f"http://127.0.0.1:8000/uploads/{file.filename}"}

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
                "model": "kling-v2-5-turbo",
                "prompt": params.prompt,
                "duration": params.duration,
                "input_image": params.input_image.dict(),
                "enhance_prompt": params.enhance_prompt
            }
        else:  # wan-25-fast
            cleaned_params = {
                "seed": params.seed,
                "prompt": params.prompt,
                "duration": params.duration,
                "resolution": "720p",
                "input_audio": None,
                "input_image": params.input_image.dict(),
                "enhance_prompt": False,
                "negative_prompt": params.negative_prompt or ""
            }
    elif model_name == "minimax":
        base_url = f"{HIGGSFIELD_BASE_URL}/image2video/minimax"
        cleaned_params = {
            "prompt": params.prompt,
            "duration": 6,
            "resolution": "768",
            "enhance_prompt": True,
            "input_image": params.input_image.dict()
        }
    elif model_name == "seedance":
        base_url = f"{HIGGSFIELD_BASE_URL}/image2video/seedance"
        cleaned_params = {
            "model": "seedance_pro",
            "prompts": [params.prompt] if params.prompt else [],
            "duration": params.duration,
            "resolution": params.resolution,
            "input_image": params.input_image.dict(),
            "enhance_prompt": params.enhance_prompt
        }

    request_data["params"] = cleaned_params

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
                    return {
                        "job_set_id": job_set_id,
                        "status": status,
                        "error": data["jobs"][0].get("error", "Generation failed")
                    }
            
            # Wait between polls since image2video generation can take time
            await asyncio.sleep(5)  # 5 second polling interval
