"""Shared test setup: puts backend/ on sys.path and provides a tiny fake
embedding model, so the tests never download or load the real one."""

import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SAMPLE_PDF = ROOT / "data" / "sample_reports" / "sample_medical_report.pdf"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

FAKE_DIMENSION = 64


def fake_embeddings(texts):
    """Bag-of-words hashing: texts that share words get similar vectors."""

    vectors = np.zeros((len(texts), FAKE_DIMENSION), dtype="float32")

    for row, text in enumerate(texts):
        for word in text.lower().split():
            word = word.strip(".,:;()")
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % FAKE_DIMENSION
            vectors[row, bucket] += 1.0

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    return vectors / norms


def patch_embeddings(test_case):
    """Replace the real embedding functions for the duration of a test."""

    from services import embedding_service

    originals = (
        embedding_service.generate_embeddings,
        embedding_service.get_embedding_dimension,
    )

    embedding_service.generate_embeddings = fake_embeddings
    embedding_service.get_embedding_dimension = lambda: FAKE_DIMENSION

    def restore():
        (
            embedding_service.generate_embeddings,
            embedding_service.get_embedding_dimension,
        ) = originals

    test_case.addCleanup(restore)


# ---------------- shared database / auth helpers ---------------- #

def patch_database(test_case):
    """Point the app at a throw-away SQLite database for one test."""

    import tempfile
    from pathlib import Path
    from unittest import mock

    from sqlalchemy.orm import sessionmaker

    import database
    from models import db_models  # noqa: F401  (registers the tables)

    folder = tempfile.TemporaryDirectory()
    test_case.addCleanup(folder.cleanup)

    engine = database.make_engine(f"sqlite:///{Path(folder.name, 'test.db').as_posix()}")
    database.Base.metadata.create_all(engine)
    test_case.addCleanup(engine.dispose)       # runs before folder.cleanup (LIFO)

    patcher = mock.patch.object(
        database, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False)
    )
    patcher.start()
    test_case.addCleanup(patcher.stop)

    return engine


def fresh_limiters(test_case):
    """Give every test empty rate limiters (they are module-level state)."""

    from unittest import mock

    from routers import auth as auth_router
    from routers import chat as chat_router
    from routers import upload as upload_router
    from services.rate_limit import RateLimiter

    for module, name, calls, window in (
        (auth_router, "login_failures", 10, 900),
        (auth_router, "registrations", 100, 3600),
        (upload_router, "upload_limiter", 100, 3600),
        (chat_router, "chat_limiter", 100, 3600),
    ):
        patcher = mock.patch.object(module, name, RateLimiter(calls, window))
        patcher.start()
        test_case.addCleanup(patcher.stop)


def register(client, email="alice@example.com", password="correct-horse-1"):
    """Create an account through the API; returns (headers, user_id)."""

    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    body = response.json()

    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]
