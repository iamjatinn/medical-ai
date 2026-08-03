import logging

from config import CHUNK_SIZE

logger = logging.getLogger(__name__)

CHUNK_OVERLAP = 50


def chunk_text(text: str, chunk_size=CHUNK_SIZE):

    logger.info("Splitting document into chunks.")

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += (chunk_size - CHUNK_OVERLAP)

    logger.info(f"{len(chunks)} chunks created.")

    return chunks