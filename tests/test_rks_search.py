"""Checks for the existing PGVector tool contract after source-aware retrieval changes."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from rag.vector_store import fetch_full_document, fetch_relevant_documents


class ExistingVectorSearchTest(unittest.TestCase):
    def test_relevant_chunks_keep_page_and_score_and_respect_filter(self):
        doc = SimpleNamespace(metadata={"file_name": "RKS-unit.pdf", "document_id": "id1",
                                        "page": 4, "version": "2", "year": 2025},
                              page_content="Pelat tangki 6 mm")
        class Store:
            def similarity_search_with_relevance_scores(self, query, k, filter=None):
                self.filter = filter
                return [(doc, .9), (doc, .2)]
        store = Store()
        with patch("rag.vector_store._get_vector_store", return_value=store):
            result = fetch_relevant_documents.func("pelat tangki", top_k=2,
                                                    score_threshold=.5, document_type="RKS")
        self.assertEqual({"document_type": "RKS"}, store.filter)
        self.assertEqual(1, len(result))
        self.assertEqual(4, result[0]["page"])
        self.assertEqual("id1", result[0]["source_id"])
        self.assertEqual(.9, result[0]["relevance_score"])

    def test_empty_and_search_failure_never_substitute_unrelated_rks(self):
        empty = SimpleNamespace(similarity_search_with_relevance_scores=lambda query, k: [])
        with patch("rag.vector_store._get_vector_store", return_value=empty):
            result = fetch_full_document("dokumen yang tidak ada")
        self.assertTrue(result["error"])
        self.assertIn("ambang", result["full_docs"])
        failing = SimpleNamespace(similarity_search_with_relevance_scores=lambda *a, **kw: 1 / 0)
        with patch("rag.vector_store._get_vector_store", return_value=failing):
            self.assertEqual([], fetch_relevant_documents.func("pelat"))
            self.assertTrue(fetch_full_document("pelat")["error"])


if __name__ == "__main__":
    unittest.main()
