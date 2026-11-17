import tempfile
import unittest
from pathlib import Path

import helpers

from services.chunking_service import chunk_text
from services.index_utils import (
    knowledge_base_changed,
    knowledge_fingerprint,
    write_fingerprint,
)
from services.rag_service import RAGService

DOCS = [
    "Low hemoglobin may indicate iron deficiency and anemia.",
    "High blood glucose can be a sign of diabetes.",
    "Vitamin D is produced in the skin from sunlight.",
]


class ChunkingTests(unittest.TestCase):

    def test_short_text_is_one_chunk(self):
        self.assertEqual(chunk_text("short text"), ["short text"])

    def test_long_text_is_split_without_cutting_words(self):

        text = " ".join(["alpha"] * 300)

        chunks = chunk_text(text, chunk_size=100, overlap=20)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))
        self.assertTrue(all(set(chunk.split()) == {"alpha"} for chunk in chunks))

    def test_bad_overlap_is_rejected_instead_of_looping_forever(self):
        with self.assertRaises(ValueError):
            chunk_text("abc", chunk_size=10, overlap=10)


class RAGServiceTests(unittest.TestCase):

    def setUp(self):
        helpers.patch_embeddings(self)
        self.rag = RAGService()
        self.rag.add_documents(DOCS)

    def test_search_returns_the_most_relevant_chunk_first(self):

        results = self.rag.search("hemoglobin iron anemia", k=3, min_score=0.0)

        self.assertEqual(results[0]["text"], DOCS[0])
        self.assertGreater(results[0]["score"], results[-1]["score"])

    def test_min_score_filters_unrelated_chunks(self):

        results = self.rag.search("zebra kitchen", k=3, min_score=0.3)

        self.assertEqual(results, [])

    def test_empty_index_returns_nothing(self):
        self.assertEqual(RAGService().search("anything"), [])

    def test_save_then_load_round_trip(self):
        """Regression test: save() used to write to the literal strings
        'VECTOR_INDEX_PATH' / ' DOCUMENT_STORE_PATH', so nothing was ever
        saved where load() looked."""

        with tempfile.TemporaryDirectory() as folder:

            index_path = Path(folder) / "store" / "medical.index"
            document_path = Path(folder) / "store" / "documents.json"

            self.rag.save(index_path, document_path)

            self.assertTrue(index_path.exists())
            self.assertTrue(document_path.exists())

            loaded = RAGService()
            loaded.load(index_path, document_path)

            self.assertEqual(loaded.documents, DOCS)
            self.assertEqual(
                loaded.search("hemoglobin iron", k=1, min_score=0.0)[0]["text"],
                DOCS[0],
            )


class FingerprintTests(unittest.TestCase):

    def test_index_is_rebuilt_only_when_knowledge_files_change(self):

        with tempfile.TemporaryDirectory() as folder:

            docs = Path(folder) / "docs"
            docs.mkdir()
            (docs / "a.txt").write_text("first document", encoding="utf-8")

            meta = Path(folder) / "meta.json"

            before = knowledge_fingerprint(docs)

            self.assertTrue(knowledge_base_changed(meta, before))  # nothing saved yet

            write_fingerprint(meta, before, 1)

            self.assertFalse(knowledge_base_changed(meta, knowledge_fingerprint(docs)))

            (docs / "b.txt").write_text("a new document", encoding="utf-8")

            self.assertTrue(knowledge_base_changed(meta, knowledge_fingerprint(docs)))


if __name__ == "__main__":
    unittest.main()
