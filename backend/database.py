"""Database connection (SQLAlchemy).

DATABASE_URL decides which database is used:
  - Docker / production:  postgresql+psycopg://user:password@db:5432/medical_ai
  - not set (local dev):  a SQLite file next to the backend, so the app runs
                          without installing Postgres.
"""

import os

from sqlalchemy import create_engine, inspect, text
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


# Columns added after the first release. create_all() never alters an existing
# table, so these are added by hand when missing: (table, column, SQL type).
ADDED_COLUMNS = [
    ("reports", "analysis", "JSON"),
]


def _add_missing_columns(target_engine):

    inspector = inspect(target_engine)

    with target_engine.begin() as connection:

        for table, column, sql_type in ADDED_COLUMNS:

            if not inspector.has_table(table):
                continue

            existing = {c["name"] for c in inspector.get_columns(table)}

            if column not in existing:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def init_db(target_engine=None):
    """Create the tables if they do not exist yet, and add any new columns.
    (A migration tool such as Alembic would replace this in a larger project.)"""

    from models import db_models  # noqa: F401  (registers the tables on Base)

    target_engine = target_engine or engine

    Base.metadata.create_all(target_engine)

    _add_missing_columns(target_engine)
