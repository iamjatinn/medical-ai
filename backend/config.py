"""Central configuration for the Medical AI backend.

All filesystem paths are resolved from this file's location, so the app
behaves the same no matter which directory it is started from.
"""

import os
import secrets
from pathlib import Path

# ---------------- Paths ---------------- #

BASE_DIR = Path(__file__).resolve().parent          # .../backend
PROJECT_ROOT = BASE_DIR.parent                      # repository root

UPLOAD_DIR = BASE_DIR / "uploads"

KNOWLEDGE_FOLDER = PROJECT_ROOT / "data" / "medical_docs"

VECTOR_STORE_DIR = BASE_DIR / "vector_store"
VECTOR_INDEX_PATH = VECTOR_STORE_DIR / "medical.index"
DOCUMENT_STORE_PATH = VECTOR_STORE_DIR / "documents.json"
INDEX_META_PATH = VECTOR_STORE_DIR / "meta.json"

# ---------------- Models ---------------- #

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence-transformers")   # or "fastembed" (no PyTorch)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")   # override per environment

# ---------------- RAG ---------------- #

TOP_K = 3                 # chunks returned per query
MIN_SIMILARITY = 0.45     # cosine similarity below this is treated as unrelated
                          # (tuned on the sample report: relevant chunks score
                          # 0.47-0.79, unrelated ones 0.25-0.40)
CHUNK_SIZE = 500          # characters per chunk
CHUNK_OVERLAP = 50        # characters shared between neighbouring chunks

# ---------------- Uploads ---------------- #

MAX_UPLOAD_MB = 10

# ---------------- Authentication ---------------- #

APP_ENV = os.getenv("APP_ENV", "development")           # set to "production" when deployed

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_SECRET_IS_EPHEMERAL = not JWT_SECRET
if JWT_SECRET_IS_EPHEMERAL:
    # Development convenience: a random secret that changes on every restart
    # (everyone is logged out after a restart). Production must set JWT_SECRET.
    JWT_SECRET = secrets.token_urlsafe(32)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "720"))

# ---------------- Rate limits (protect passwords and the AI quota) ---------------- #

LOGIN_FAILURES_PER_15_MIN = int(os.getenv("LOGIN_FAILURES_PER_15_MIN", "10"))
REGISTRATIONS_PER_HOUR_PER_IP = int(os.getenv("REGISTRATIONS_PER_HOUR_PER_IP", "10"))
UPLOADS_PER_HOUR_PER_USER = int(os.getenv("UPLOADS_PER_HOUR_PER_USER", "20"))
CHATS_PER_HOUR_PER_USER = int(os.getenv("CHATS_PER_HOUR_PER_USER", "60"))
