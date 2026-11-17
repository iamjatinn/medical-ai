import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from config import LOGIN_FAILURES_PER_15_MIN, REGISTRATIONS_PER_HOUR_PER_IP
from models.auth_models import RegisterRequest, TokenResponse, UserOut
from services import auth_service
from services.auth_service import CurrentUser, EmailAlreadyRegistered, get_current_user
from services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

login_failures = RateLimiter(LOGIN_FAILURES_PER_15_MIN, window_seconds=15 * 60)
registrations = RateLimiter(REGISTRATIONS_PER_HOUR_PER_IP, window_seconds=60 * 60)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _token_response(user: CurrentUser) -> TokenResponse:

    return TokenResponse(
        access_token=auth_service.create_access_token(user.id),
        user=UserOut(id=user.id, email=user.email),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, request: Request):

    if not registrations.try_acquire(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many sign-ups from this address. Try again later.")

    try:
        user = auth_service.create_user(body.email, body.password)
    except EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    logger.info("New user registered (id=%s)", user.id)

    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 form login: the form field `username` holds the email address."""

    email = form.username.strip().lower()
    key = f"{email}|{_client_ip(request)}"

    if login_failures.is_limited(key):
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(login_failures.retry_after(key))},
        )

    user = auth_service.authenticate(email, form.password)

    if user is None:
        login_failures.record(key)
        # Same message for "unknown email" and "wrong password" on purpose.
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_failures.reset(key)

    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email)
