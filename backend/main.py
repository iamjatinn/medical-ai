import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from database import init_db
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.reports import router as reports_router
from routers.upload import router as upload_router
from services.rag_knowledge_service import get_rag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if config.JWT_SECRET_IS_EPHEMERAL:
        if config.APP_ENV == "production":
            # A random secret would log everyone out on every restart and break
            # multiple servers. Refuse to run rather than run insecurely.
            raise RuntimeError("JWT_SECRET must be set when APP_ENV=production")
        logging.getLogger(__name__).warning(
            "JWT_SECRET is not set: using a random one (logins reset on restart)."
        )
    elif config.APP_ENV == "production" and len(config.JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters in production")

    init_db()                      # create the tables / add new columns if needed

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

app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(upload_router)
app.include_router(chat_router)


@app.get("/")
def home():

    return {"message": "Medical AI Backend Running"}
