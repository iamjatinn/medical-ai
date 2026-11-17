"""Text -> vector (embeddings), with two interchangeable backends.

  sentence-transformers   default. Needs PyTorch (about 1 GB RAM).
  fastembed               same MiniLM model through ONNX Runtime. No PyTorch,
                          a few hundred MB of RAM: use it on small servers.

Select with EMBEDDING_BACKEND. Vectors are L2-normalised either way, so the
inner product of two vectors is their cosine similarity.
"""

import logging
import os
import threading

import numpy as np

from config import EMBEDDING_BACKEND, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _load_sentence_transformers():

    from sentence_transformers import SentenceTransformer

    try:
        # Use the cached copy first: it skips ~20 network checks against
        # huggingface.co, so startup is much faster.
        return SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
    except OSError:
        logger.info("Model not cached yet - downloading it (one time only).")
        return SentenceTransformer(EMBEDDING_MODEL)


def _load_fastembed():

    from fastembed import TextEmbedding

    # FASTEMBED_CACHE_PATH lets the Docker build and the running container
    # share the same downloaded model files.
    return TextEmbedding(
        model_name=f"sentence-transformers/{EMBEDDING_MODEL}",
        cache_dir=os.getenv("FASTEMBED_CACHE_PATH") or None,
    )


def _get_model():
    """Load the model lazily (once) so importing this module stays cheap and
    tests can run without downloading anything."""

    global _model

    if _model is None:
        with _lock:
            if _model is None:
                logger.info("Loading embedding model %s (backend: %s)", EMBEDDING_MODEL, EMBEDDING_BACKEND)

                if EMBEDDING_BACKEND == "fastembed":
                    _model = _load_fastembed()
                elif EMBEDDING_BACKEND == "sentence-transformers":
                    _model = _load_sentence_transformers()
                else:
                    raise ValueError(f"Unknown EMBEDDING_BACKEND: {EMBEDDING_BACKEND!r}")

                logger.info("Embedding model loaded.")

    return _model


def _encode(texts) -> np.ndarray:

    model = _get_model()

    if EMBEDDING_BACKEND == "fastembed":
        vectors = np.array(list(model.embed(list(texts), batch_size=32)), dtype="float32")
    else:
        vectors = np.asarray(
            model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False),
            dtype="float32",
        )

    # Normalise ourselves so both backends behave identically.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    return vectors / norms


def get_embedding_dimension() -> int:

    return int(_encode(["dimension probe"]).shape[1])


def generate_embeddings(texts):
    """Embed many texts at once -> float32 array of shape (n, dimension)."""

    return _encode(texts)


def generate_embedding(text: str):

    return generate_embeddings([text])[0]
