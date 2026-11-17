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

def normalize_url(url: str) -> str:
    """Hosting providers (Neon, Render, Heroku...) give URLs that start with
    postgres:// or postgresql://. SQLAlchemy needs the driver named explicitly."""

    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]

    return url


DATABASE_URL = normalize_url(
    os.getenv("DATABASE_URL") or f"sqlite:///{(BASE_DIR / 'medical_ai.db').as_posix()}"
)


class Base(DeclarativeBase):
    """Parent class of every table model."""


def make_engine(url: str = DATABASE_URL):

    url = normalize_url(url)
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
    ("reports", "user_id", "INTEGER REFERENCES users(id) ON DELETE CASCADE"),
]

# Indexes for those columns (new databases get them from the model).
ADDED_INDEXES = [
    ("ix_reports_user_id", "reports", "user_id"),
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

        for index_name, table, column in ADDED_INDEXES:
            if inspector.has_table(table):
                connection.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"))


def init_db(target_engine=None):
    """Create the tables if they do not exist yet, and add any new columns.
    (A migration tool such as Alembic would replace this in a larger project.)"""

    from models import db_models  # noqa: F401  (registers the tables on Base)

    target_engine = target_engine or engine

    Base.metadata.create_all(target_engine)

    _add_missing_columns(target_engine)
