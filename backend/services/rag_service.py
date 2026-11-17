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

    Every chunk can carry a `source` (title, url, credit) so answers can say
    where the information came from.
    """

    def __init__(self, dimension: int | None = None):

        self.dimension = dimension or embedding_service.get_embedding_dimension()

        self.index = faiss.IndexFlatIP(self.dimension)

        self.documents: list[str] = []
        self.sources: list[dict] = []          # parallel to documents

    # ---------------- indexing ---------------- #

    def add_documents(self, texts, sources=None):
        """Index chunks. `sources` (optional) is a list of dicts, one per text."""

        texts = list(texts)
        sources = list(sources) if sources is not None else [{} for _ in texts]

        if len(sources) != len(texts):
            raise ValueError("sources must have one entry per text")

        keep = [i for i, text in enumerate(texts) if text and text.strip()]

        if not keep:
            return

        texts = [texts[i] for i in keep]
        sources = [sources[i] for i in keep]

        embeddings = embedding_service.generate_embeddings(texts)

        embeddings = np.ascontiguousarray(embeddings, dtype="float32")

        self.index.add(embeddings)

        self.documents.extend(texts)
        self.sources.extend(sources)

        logger.info("Added %d chunks to the FAISS index.", len(texts))

    def add_document(self, text: str, source: dict | None = None):

        self.add_documents([text], [source or {}])

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
                "source": self.sources[idx],
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
            json.dump({"documents": self.documents, "sources": self.sources}, file, ensure_ascii=False)

        logger.info("Saved FAISS index to %s", index_path)

    def load(
        self,
        index_path: Path = VECTOR_INDEX_PATH,
        document_path: Path = DOCUMENT_STORE_PATH,
    ):

        self.index = faiss.read_index(str(index_path))
        self.dimension = self.index.d

        with open(document_path, "r", encoding="utf-8") as file:
            stored = json.load(file)

        if isinstance(stored, list):               # older format: just the texts
            self.documents, self.sources = stored, [{} for _ in stored]
        else:
            self.documents = stored["documents"]
            self.sources = stored.get("sources") or [{} for _ in self.documents]

        if not (self.index.ntotal == len(self.documents) == len(self.sources)):
            raise ValueError(
                "Vector index and document store are out of sync "
                f"({self.index.ntotal} vectors, {len(self.documents)} documents, "
                f"{len(self.sources)} sources)."
            )
