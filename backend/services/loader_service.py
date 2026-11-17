import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_documents(folder_path):
    """Read every .txt knowledge file in a folder (sorted, so the order is
    deterministic)."""

    documents = []

    for path in sorted(Path(folder_path).glob("*.txt")):

        text = path.read_text(encoding="utf-8").strip()

        if text:
            documents.append(text)

    logger.info("%d knowledge documents loaded from %s.", len(documents), folder_path)

    return documents
