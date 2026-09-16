from fastapi import APIRouter

from models.chat_models import ChatRequest, ChatResponse
from services.chat_service import ask_question

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    answer = ask_question(
        request.report_id,
        request.question
    )

    return {
        "answer": answer
    }