import logging

from config import (
    DOCUMENT_STORE_PATH,
    INDEX_META_PATH,
    KNOWLEDGE_FOLDER,
    VECTOR_INDEX_PATH,
)

from services.chunking_service import chunk_text
from services.index_utils import (
    knowledge_base_changed,
    knowledge_fingerprint,
    write_fingerprint,
)
from services.loader_service import load_documents
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


def build_index() -> RAGService:
    """Return a ready RAGService.

    A saved index is re-used only when it exists AND the knowledge files,
    chunking settings and embedding model are unchanged. Otherwise the
    index is rebuilt from the documents and saved again.
    """

    fingerprint = knowledge_fingerprint(KNOWLEDGE_FOLDER)

    saved_index_exists = VECTOR_INDEX_PATH.exists() and DOCUMENT_STORE_PATH.exists()

    if saved_index_exists and not knowledge_base_changed(INDEX_META_PATH, fingerprint):

        try:
            rag = RAGService()
            rag.load()
            logger.info("Loaded saved FAISS index (%d chunks).", len(rag.documents))
            return rag

        except Exception:
            logger.exception("Saved FAISS index could not be loaded; rebuilding it.")

    logger.info("Building a new FAISS index from %s ...", KNOWLEDGE_FOLDER)

    rag = RAGService()

    chunks, sources = [], []

    for document in load_documents(KNOWLEDGE_FOLDER):

        source = {
            "name": document.name,
            "title": document.title,
            "url": document.url,
            "credit": document.source,
        }

        for chunk in chunk_text(document.text):
            # Put the document title in front of every chunk. A chunk such as
            # "What do the results mean?" is otherwise ambiguous: it does not
            # say which test it is about, and the search cannot tell either.
            chunks.append(f"{document.title}: {chunk}")
            sources.append(source)

    rag.add_documents(chunks, sources)

    rag.save()

    write_fingerprint(INDEX_META_PATH, fingerprint, len(rag.documents))

    logger.info("FAISS index built and saved (%d chunks).", len(rag.documents))

    return rag
