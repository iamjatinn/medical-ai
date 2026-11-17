from fastapi import APIRouter, Depends, HTTPException

from config import CHATS_PER_HOUR_PER_USER
from models.chat_models import ChatRequest, ChatResponse
from services.auth_service import CurrentUser, get_current_user
from services.chat_service import ask_question
from services.rate_limit import RateLimiter
from services.report_storage_service import ReportNotFoundError

router = APIRouter()

chat_limiter = RateLimiter(CHATS_PER_HOUR_PER_USER, window_seconds=60 * 60)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: CurrentUser = Depends(get_current_user)):

    # Each message costs AI quota, so limit how many one user can send.
    if not chat_limiter.try_acquire(user.id):
        raise HTTPException(status_code=429, detail="Message limit reached. Please try again later.")

    try:
        return ask_question(request.report_id, request.question.strip(), user_id=user.id)

    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found.")
