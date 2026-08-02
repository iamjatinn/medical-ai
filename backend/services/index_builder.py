import logging

from services.loader_service import load_documents
from services.chunking_service import chunk_text
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


def build_index():

    logger.info("Building medical knowledge index...")

    rag = RAGService()

    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    DOCUMENT_PATH = PROJECT_ROOT / "data" / "medical_docs"

    documents = load_documents(str(DOCUMENT_PATH))

    for document in documents:

        chunks = chunk_text(document)

        for chunk in chunks:

            rag.add_document(chunk)

    logger.info("Medical knowledge index built successfully.")

    return rag