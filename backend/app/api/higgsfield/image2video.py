# app/api/routes/higgsfield_image2video.py
import os
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.config import settings

HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai/v1"
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

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{HIGGSFIELD_BASE_URL}/image2video/{params.model_name}",
            headers=headers,
            json=request.dict(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
