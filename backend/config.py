"""Central configuration for the Medical AI backend.

All filesystem paths are resolved from this file's location, so the app
behaves the same no matter which directory it is started from.
"""

from pathlib import Path

# ---------------- Paths ---------------- #

BASE_DIR = Path(__file__).resolve().parent          # .../backend
PROJECT_ROOT = BASE_DIR.parent                      # repository root

UPLOAD_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"

KNOWLEDGE_FOLDER = PROJECT_ROOT / "data" / "medical_docs"

VECTOR_STORE_DIR = BASE_DIR / "vector_store"
VECTOR_INDEX_PATH = VECTOR_STORE_DIR / "medical.index"
DOCUMENT_STORE_PATH = VECTOR_STORE_DIR / "documents.json"
INDEX_META_PATH = VECTOR_STORE_DIR / "meta.json"

# ---------------- Models ---------------- #

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GEMINI_MODEL = "gemini-2.5-flash"

# ---------------- RAG ---------------- #

TOP_K = 3                 # chunks returned per query
MIN_SIMILARITY = 0.45     # cosine similarity below this is treated as unrelated
                          # (tuned on the sample report: relevant chunks score
                          # 0.47-0.79, unrelated ones 0.25-0.40)
CHUNK_SIZE = 500          # characters per chunk
CHUNK_OVERLAP = 50        # characters shared between neighbouring chunks

# ---------------- Uploads ---------------- #

MAX_UPLOAD_MB = 10
