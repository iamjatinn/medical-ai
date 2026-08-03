import logging

from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

logger.info("Loading embedding model...")

model = SentenceTransformer(EMBEDDING_MODEL)

logger.info("Embedding model loaded.")


def generate_embedding(text: str):

    logger.info("Generating embedding.")

    embedding = model.encode(text)

    return embedding