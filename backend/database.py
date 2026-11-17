"""Database connection (SQLAlchemy).

DATABASE_URL decides which database is used:
  - Docker / production:  postgresql+psycopg://user:password@db:5432/medical_ai
  - not set (local dev):  a SQLite file next to the backend, so the app runs
                          without installing Postgres.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import BASE_DIR

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(BASE_DIR / 'medical_ai.db').as_posix()}"


class Base(DeclarativeBase):
    """Parent class of every table model."""


def make_engine(url: str = DATABASE_URL):

    options = {"pool_pre_ping": True}   # re-connects if the database restarted

    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}

    return create_engine(url, **options)


engine = make_engine()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    """Create the tables if they do not exist yet.
    (A migration tool such as Alembic would replace this in a larger project.)"""

    from models import db_models  # noqa: F401  (registers the tables on Base)

    Base.metadata.create_all(engine)
