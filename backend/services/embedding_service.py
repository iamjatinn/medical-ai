import logging
import threading

import numpy as np

from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _get_model():
    """Load the sentence-transformer lazily (once) so importing this module
    stays cheap and tests can run without downloading a model."""

    global _model

    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model: %s", EMBEDDING_MODEL)

                try:
                    # Use the cached copy first: it skips ~20 network checks
                    # against huggingface.co, so startup is much faster.
                    _model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
                except OSError:
                    logger.info("Model not cached yet - downloading it (one time only).")
                    _model = SentenceTransformer(EMBEDDING_MODEL)

                logger.info("Embedding model loaded.")

    return _model


def get_embedding_dimension() -> int:

    return int(_get_model().get_sentence_embedding_dimension())


def generate_embeddings(texts):
    """Embed many texts at once. Vectors are L2-normalised, so the inner
    product between two vectors equals their cosine similarity."""

    vectors = _get_model().encode(
        list(texts),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return np.asarray(vectors, dtype="float32")


def generate_embedding(text: str):

    return generate_embeddings([text])[0]
