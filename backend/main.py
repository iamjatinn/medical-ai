from fastapi import FastAPI
from routers.upload import router

app = FastAPI(
    title="Medical AI API",
    description="AI-powered medical report analyzer",
    version="0.1"
)

app.include_router(router)

@app.get("/")
def home():
    return {
        "message": "Welcome to Medical AI"
    }