import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from models.response_models import ReportResult

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 254 or not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("password")
    @classmethod
    def strong_enough(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(value.encode("utf-8")) > 72:          # a hard limit of the bcrypt algorithm
            raise ValueError("Password must be at most 72 bytes.")
        return value


class UserOut(BaseModel):
    id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReportSummary(BaseModel):
    report_id: str
    filename: str
    created_at: str
    overall_risk: Optional[str] = None
    abnormal_count: int


class ChatTurn(BaseModel):
    role: str
    content: str


class ReportDetail(ReportResult):
    chat_history: List[ChatTurn] = []
