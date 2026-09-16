from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.upload import router as upload_router
from routers.chat import router as chat_router

from services.index_builder import build_index

app = FastAPI(
    title="Medical AI API",
    description="AI-powered Medical Report Analyzer",
    version="1.0.0"
)

# ---------------- CORS ---------------- #

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------- #

app.include_router(upload_router)
app.include_router(chat_router)

app.state.rag = build_index()


@app.get("/")
def home():

    return {
        "message": "Medical AI Backend Running"
    }