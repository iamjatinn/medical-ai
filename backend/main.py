import logging

from fastapi import FastAPI
from routers.upload import router
from services.index_builder import build_index

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

app = FastAPI(
    title="Medical AI API",
    description="AI-powered medical report analyzer",
    version="0.1.0"
)
app.state.rag = build_index()
app.include_router(router)


@app.get("/")
def home():
    logging.getLogger(__name__).info("Home endpoint accessed")

    return {
        "message": "Welcome to Medical AI"
    }