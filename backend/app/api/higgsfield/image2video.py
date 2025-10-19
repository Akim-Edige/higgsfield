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
    model: str = "veo-3-fast"
    prompt: str = "A cinematic portrait of a woman turning her head slightly"
    seed: Optional[int] = 500000
    motions: Optional[List[MotionRef]] = None
    input_image: ImageReference
    enhance_prompt: bool = True
    model_name: Optional[str] = "veo3"  # Название модели для эндпоинта
    duration: int = 5
    resolution: Optional[str] = "720" 

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
    elif model_name in ["seedance", "minimax"]:
        base_url = f"{HIGGSFIELD_BASE_URL}/image2video/{model_name}"

    if model_name == "seedance":
        if params.prompt and not params.prompts:
            request_data["params"]["prompts"] = [params.prompt]
    elif model_name in ["kling-2-5", "wan-25-fast"]:
        if params.resolution == "720":
            request_data["params"]["resolution"] = "720p"

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
