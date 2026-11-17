import json
import logging
from pathlib import Path

import faiss
import numpy as np

from config import (
    DOCUMENT_STORE_PATH,
    MIN_SIMILARITY,
    TOP_K,
    VECTOR_INDEX_PATH,
)
from services import embedding_service

logger = logging.getLogger(__name__)


class RAGService:
    """A small FAISS-backed semantic search over text chunks.

    Embeddings are normalised, so an inner-product index (IndexFlatIP)
    returns cosine similarity: higher score = more similar.
    """

    def __init__(self, dimension: int | None = None):

        self.dimension = dimension or embedding_service.get_embedding_dimension()

        self.index = faiss.IndexFlatIP(self.dimension)

        self.documents: list[str] = []

    # ---------------- indexing ---------------- #

    def add_documents(self, texts):

        texts = [text for text in texts if text and text.strip()]

        if not texts:
            return

        embeddings = embedding_service.generate_embeddings(texts)

        embeddings = np.ascontiguousarray(embeddings, dtype="float32")

        self.index.add(embeddings)

        self.documents.extend(texts)

        logger.info("Added %d chunks to the FAISS index.", len(texts))

    def add_document(self, text: str):

        self.add_documents([text])

    # ---------------- search ---------------- #

    def search(self, query: str, k: int = TOP_K, min_score: float = MIN_SIMILARITY):

        if self.index.ntotal == 0:
            return []

        query_embedding = embedding_service.generate_embeddings([query])

        scores, indices = self.index.search(
            np.ascontiguousarray(query_embedding, dtype="float32"),
            min(k, self.index.ntotal),
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):

            if idx == -1 or score < min_score:
                continue

            results.append({
                "text": self.documents[idx],
                "score": float(score),
            })

        return results

    # ---------------- persistence ---------------- #

    def save(
        self,
        index_path: Path = VECTOR_INDEX_PATH,
        document_path: Path = DOCUMENT_STORE_PATH,
    ):

        index_path = Path(index_path)
        document_path = Path(document_path)

        index_path.parent.mkdir(parents=True, exist_ok=True)
        document_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(index_path))

        with open(document_path, "w", encoding="utf-8") as file:
            json.dump(self.documents, file, ensure_ascii=False)

        logger.info("Saved FAISS index to %s", index_path)

    def load(
        self,
        index_path: Path = VECTOR_INDEX_PATH,
        document_path: Path = DOCUMENT_STORE_PATH,
    ):

        self.index = faiss.read_index(str(index_path))
        self.dimension = self.index.d

        with open(document_path, "r", encoding="utf-8") as file:
            self.documents = json.load(file)

        if self.index.ntotal != len(self.documents):
            raise ValueError(
                "Vector index and document store are out of sync "
                f"({self.index.ntotal} vectors vs {len(self.documents)} documents)."
            )
