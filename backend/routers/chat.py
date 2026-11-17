from fastapi import APIRouter, HTTPException

from models.chat_models import ChatRequest, ChatResponse
from services.chat_service import ask_question
from services.report_storage_service import ReportNotFoundError

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    try:
        return ask_question(request.report_id, request.question.strip())

    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found.")
