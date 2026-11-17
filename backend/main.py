import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers.chat import router as chat_router
from routers.upload import router as upload_router
from services.rag_knowledge_service import get_rag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()                      # create the tables if they do not exist yet

    # Build / load the FAISS index once at startup (shared by every request).
    app.state.rag = get_rag()
    yield


app = FastAPI(
    title="Medical AI API",
    description="AI-powered Medical Report Analyzer",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------- CORS ---------------- #

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------- #

app.include_router(upload_router)
app.include_router(chat_router)


@app.get("/")
def home():

    return {"message": "Medical AI Backend Running"}
