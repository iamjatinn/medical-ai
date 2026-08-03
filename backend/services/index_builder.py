import logging
from pathlib import Path

from config import (
    KNOWLEDGE_FOLDER,
    VECTOR_INDEX_PATH,
    DOCUMENT_STORE_PATH
)

from services.loader_service import load_documents
from services.chunking_service import chunk_text
from services.rag_service import RAGService
from services.index_utils import knowledge_base_changed

logger = logging.getLogger(__name__)


def build_index():

    rag = RAGService()

    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    index_path = PROJECT_ROOT / VECTOR_INDEX_PATH
    document_store = PROJECT_ROOT / DOCUMENT_STORE_PATH

    # Load existing FAISS index if available
    if (not knowledge_base_changed(index_path) and document_store.exists()):
        logger.info("Loading existing FAISS index...")

        rag.load()

        logger.info("FAISS index loaded successfully.")

        return rag

    logger.info("No existing index found. Building a new FAISS index...")

    document_path = PROJECT_ROOT / KNOWLEDGE_FOLDER

    documents = load_documents(str(document_path))

    for document in documents:

        chunks = chunk_text(document)

        for chunk in chunks:

            rag.add_document(chunk)

    # Create vector_store folder if needed
    index_path.parent.mkdir(parents=True, exist_ok=True)

    rag.save()

    logger.info("FAISS index built and saved successfully.")

    return rag