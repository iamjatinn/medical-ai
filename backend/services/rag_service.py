import logging
import pickle
import faiss
import numpy as np

from services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)

class RAGService:

    def __init__(self):

        logger.info("Initializing FAISS index...")

        self.dimension = 384

        self.index = faiss.IndexFlatL2(self.dimension)

        self.documents = []

        logger.info("FAISS index initialized.")


    def add_document(self, text: str):

        logger.info("Adding document to FAISS.")

        embedding = generate_embedding(text)

        embedding = np.array(
            [embedding],
            dtype="float32"
        )

        self.index.add(embedding)

        self.documents.append(text)

    def search(self, query: str, k=3):

        logger.info(f"Searching FAISS for query: {query}")

        query_embedding = generate_embedding(query)

        query_embedding = np.array(
        [query_embedding],
        dtype="float32"
        )

        distances, indices = self.index.search(
        query_embedding,
        k
        )

        results = []

        for distance, idx in zip(distances[0], indices[0]):

            if idx != -1:

                results.append({
                "text": self.documents[idx],
                "score": float(distance)
            })

        return results

    def save(self):

        faiss.write_index(
            self.index,
            "vector_store/medical.index"
        )

        with open(
            "vector_store/documents.pkl",
            "wb"
        ) as file:

            pickle.dump(
            self.documents,
            file
        )

    def load(self):

        self.index = faiss.read_index(
        "vector_store/medical.index"
        )

        with open(
        "vector_store/documents.pkl",
        "rb"
        ) as file:

            self.documents = pickle.load(file)

