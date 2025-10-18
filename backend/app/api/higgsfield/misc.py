# app/api/routes/higgsfield_misc.py
import os
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import settings

HIGGSFIELD_BASE_URL = "https://platform.higgsfield.ai/v1"
HF_API_KEY = settings.HIGGSFIELD_API_KEY

HF_SECRET =  settings.HIGGSFIELD_SECRET

router = APIRouter(prefix="/higgsfield", tags=["higgsfield:misc"])

# ============================
# 🔹 MOTIONS
# ============================
@router.get("/motions")
async def get_motions():
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HIGGSFIELD_BASE_URL}/motions", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

# ============================
# 🔹 RESULTS
# ============================
@router.get("/results/{job_set_id}")
async def get_generation_result(job_set_id: str):
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HIGGSFIELD_BASE_URL}/job-sets/{job_set_id}", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()

# ============================
# 🔹 Вебхук
# ============================
@router.post("/webhook/higgsfield")
async def webhook_higgsfield(request: Request):
    data = await request.json()
    secret_key = request.headers.get("X-Webhook-Secret-Key")
    if secret_key != HF_SECRET:
        return JSONResponse(status_code=403, content={"error": "Invalid webhook secret"})
    print("Webhook received:", data)
    return {"status": "ok"}

# ============================
# 🔹 Фоновый поллинг
# ============================
async def poll_job_set(job_set_id: str):
    headers = {"hf-api-key": HF_API_KEY, "hf-secret": HF_SECRET}
    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(f"{HIGGSFIELD_BASE_URL}/job-sets/{job_set_id}", headers=headers)
            data = resp.json()
            status = data["jobs"][0]["status"]
            print(f"Job {job_set_id} status: {status}")
            if status in ["completed", "failed", "nsfw"]:
                print("Final result:", data)
                break
            await asyncio.sleep(10)

@router.post("/generate-and-poll")
async def generate_and_poll(payload: dict, background_tasks: BackgroundTasks):
    headers = {
        "Content-Type": "application/json",
        "hf-api-key": HF_API_KEY,
        "hf-secret": HF_SECRET
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{HIGGSFIELD_BASE_URL}/text2image/soul", headers=headers, json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    job_set_id = data["id"]
    background_tasks.add_task(poll_job_set, job_set_id)
    return {"message": "generation started", "job_set_id": job_set_id}
