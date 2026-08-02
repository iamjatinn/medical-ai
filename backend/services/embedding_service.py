import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

logger.info("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

logger.info("Embedding model loaded.")


def generate_embedding(text: str):

    logger.info("Generating embedding.")

    embedding = model.encode(text)

    return embedding