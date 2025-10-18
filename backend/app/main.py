from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from .database.models import *

# from fastapi.staticfiles import StaticFiles


app = FastAPI()

# Настроим middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем папку для статики
# app.mount("/static", StaticFiles(directory="static"), name="static")



@app.get("/")
def read_root():
    return {"message": "Higgsfield api"}
