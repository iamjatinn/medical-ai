import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size=500):

    logger.info("Splitting document into chunks.")

    chunks = []

    start = 0

    while start < len(text):

        chunk = text[start:start + chunk_size]

        chunks.append(chunk)

        start += chunk_size

    logger.info(f"{len(chunks)} chunks created.")

    return chunks