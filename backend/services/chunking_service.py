import logging

from config import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
):
    """Split text into overlapping chunks, preferring to cut at whitespace
    so words are not sliced in half."""

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()

    chunks = []

    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        if end < len(text):

            cut = max(
                text.rfind(" ", start + overlap + 1, end),
                text.rfind("\n", start + overlap + 1, end),
            )

            if cut != -1:
                end = cut

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

        # Begin the next chunk at the start of a word, not in the middle of one.
        while start < end and not text[start - 1].isspace():
            start += 1

    logger.debug("%d chunks created.", len(chunks))

    return chunks
