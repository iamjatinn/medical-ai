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
