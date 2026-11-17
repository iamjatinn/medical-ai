import unittest
from unittest import mock

import helpers  # noqa: F401

import numpy as np

from services import embedding_service


class FakeSentenceTransformer:
    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        return np.array([[3.0, 4.0, 0.0] for _ in texts])        # length 5, not normalised


class FakeFastEmbed:
    def embed(self, texts, batch_size=256):
        return (np.array([0.0, 6.0, 8.0]) for _ in texts)         # a generator, length 10


class EmbeddingBackendTests(unittest.TestCase):

    def use(self, backend, model):
        for patcher in (
            mock.patch.object(embedding_service, "EMBEDDING_BACKEND", backend),
            mock.patch.object(embedding_service, "_model", model),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_sentence_transformers_vectors_are_normalised(self):
        self.use("sentence-transformers", FakeSentenceTransformer())

        vectors = embedding_service.generate_embeddings(["a", "b"])

        self.assertEqual(vectors.shape, (2, 3))
        self.assertEqual(vectors.dtype, np.float32)
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), [1.0, 1.0], rtol=1e-6)

    def test_fastembed_generator_output_is_converted_and_normalised(self):
        self.use("fastembed", FakeFastEmbed())

        vectors = embedding_service.generate_embeddings(["a", "b", "c"])

        self.assertEqual(vectors.shape, (3, 3))
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), [1.0] * 3, rtol=1e-6)

    def test_dimension_comes_from_the_model(self):
        self.use("fastembed", FakeFastEmbed())
        self.assertEqual(embedding_service.get_embedding_dimension(), 3)

    def test_unknown_backend_is_rejected(self):
        with mock.patch.object(embedding_service, "EMBEDDING_BACKEND", "magic"), \
             mock.patch.object(embedding_service, "_model", None):
            with self.assertRaises(ValueError):
                embedding_service.generate_embeddings(["x"])

    def test_changing_the_backend_changes_the_index_fingerprint(self):
        """A saved index built with one backend must not be reused with another."""

        import tempfile
        from pathlib import Path

        from services import index_utils

        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "a.txt").write_text("doc", encoding="utf-8")

            with mock.patch.object(index_utils, "EMBEDDING_BACKEND", "fastembed"):
                one = index_utils.knowledge_fingerprint(Path(folder))
            with mock.patch.object(index_utils, "EMBEDDING_BACKEND", "sentence-transformers"):
                two = index_utils.knowledge_fingerprint(Path(folder))

        self.assertNotEqual(one, two)


if __name__ == "__main__":
    unittest.main()
