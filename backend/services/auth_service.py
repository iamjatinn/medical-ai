"""Passwords, tokens and the "who is calling?" dependency.

- Passwords are hashed with bcrypt (slow on purpose, salted). The plain
  password is never stored or logged.
- A login returns a signed JWT. The token holds only the user id and an
  expiry time; the server verifies the signature on every request.
- get_current_user() is a FastAPI dependency: add it to a route and the route
  is automatically protected (401 without a valid token).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import database
from config import ACCESS_TOKEN_MINUTES, JWT_ALGORITHM, JWT_SECRET
from models.db_models import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str


class EmailAlreadyRegistered(Exception):
    pass


# ---------------- passwords ---------------- #

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Used when the email is unknown, so a wrong email takes as long as a wrong
# password (otherwise response time would reveal which emails are registered).
_DUMMY_HASH = hash_password("not-a-real-password")


# ---------------- users ---------------- #

def create_user(email: str, password: str) -> CurrentUser:

    user = User(email=email, password_hash=hash_password(password))

    with database.SessionLocal() as session:
        session.add(user)

        try:
            session.commit()
        except IntegrityError as error:           # unique email
            session.rollback()
            raise EmailAlreadyRegistered(email) from error

        return CurrentUser(id=user.id, email=user.email)


def authenticate(email: str, password: str) -> Optional[CurrentUser]:
    """Return the user if the credentials are right, otherwise None."""

    with database.SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email.strip().lower()))

    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, user.password_hash):
        return None

    return CurrentUser(id=user.id, email=user.email)


# ---------------- tokens ---------------- #

def create_access_token(user_id: int, expires_minutes: int = ACCESS_TOKEN_MINUTES) -> str:

    now = datetime.now(timezone.utc)

    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=expires_minutes)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[int]:
    """The user id inside a valid, unexpired token - otherwise None."""

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],            # never accept the algorithm named by the token
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])

    except (jwt.PyJWTError, ValueError):
        return None


# ---------------- the FastAPI dependency ---------------- #

def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:

    unauthorized = HTTPException(
        status_code=401,
        detail="Not authenticated. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)

    if user_id is None:
        raise unauthorized

    with database.SessionLocal() as session:
        user = session.get(User, user_id)

    if user is None:                               # e.g. the account was deleted
        raise unauthorized

    return CurrentUser(id=user.id, email=user.email)
