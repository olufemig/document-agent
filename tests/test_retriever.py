"""Offline tests for LlamaIndex case-study retrieval."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from chromadb.errors import NotFoundError

from retrieval import retriever


class RetrieverTests(unittest.TestCase):
    def test_retrieves_evidence_with_sector_filter_and_capabilities(self) -> None:
        collection = Mock()
        collection.count.return_value = 1
        chroma_client = Mock()
        chroma_client.get_collection.return_value = collection
        node = Mock()
        node.metadata = {
            "title": "Retail Demand Forecasting Programme",
            "source_file": "retail-demand-forecast.md",
        }
        node.get_content.return_value = "Forecasting case-study content."
        match = SimpleNamespace(node=node, score=0.91)
        index = Mock()
        index.as_retriever.return_value.retrieve.return_value = [match]

        with tempfile.TemporaryDirectory() as temporary_directory:
            vector_store_dir = Path(temporary_directory)
            with (
                patch.object(retriever, "GOOGLE_API_KEY", "test-key"),
                patch.object(retriever, "VECTOR_STORE_DIR", vector_store_dir),
                patch.object(
                    retriever.chromadb,
                    "PersistentClient",
                    return_value=chroma_client,
                ),
                patch.object(retriever, "ChromaVectorStore"),
                patch.object(retriever, "GeminiEmbedding"),
                patch.object(
                    retriever.VectorStoreIndex,
                    "from_vector_store",
                    return_value=index,
                ),
            ):
                evidence = retriever.retrieve_case_studies(
                    "Improve retail forecasts",
                    sector="Retail",
                    capabilities=["Forecasting", "Analytics"],
                )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].case_study, "Retail Demand Forecasting Programme")
        self.assertEqual(evidence[0].source_file, "retail-demand-forecast.md")
        self.assertEqual(evidence[0].relevance_score, 0.91)
        filters = index.as_retriever.call_args.kwargs["filters"]
        self.assertEqual(filters.filters[0].key, "sector")
        self.assertEqual(filters.filters[0].value, "Retail")
        index.as_retriever.return_value.retrieve.assert_called_once_with(
            "Improve retail forecasts\nCapabilities: Forecasting, Analytics"
        )

    def test_returns_empty_list_for_missing_vector_store(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_store = Path(temporary_directory) / "missing"
            with (
                patch.object(retriever, "GOOGLE_API_KEY", "test-key"),
                patch.object(retriever, "VECTOR_STORE_DIR", missing_store),
            ):
                self.assertEqual(retriever.retrieve_case_studies("test"), [])

    def test_returns_empty_list_for_empty_collection(self) -> None:
        collection = Mock()
        collection.count.return_value = 0
        chroma_client = Mock()
        chroma_client.get_collection.return_value = collection

        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.object(retriever, "GOOGLE_API_KEY", "test-key"),
                patch.object(retriever, "VECTOR_STORE_DIR", Path(temporary_directory)),
                patch.object(
                    retriever.chromadb,
                    "PersistentClient",
                    return_value=chroma_client,
                ),
            ):
                self.assertEqual(retriever.retrieve_case_studies("test"), [])

    def test_requires_api_key(self) -> None:
        with patch.object(retriever, "GOOGLE_API_KEY", None):
            with self.assertRaisesRegex(RuntimeError, "GOOGLE_API_KEY"):
                retriever.retrieve_case_studies("test")

    def test_reports_uninitialised_collection(self) -> None:
        chroma_client = Mock()
        chroma_client.get_collection.side_effect = NotFoundError("missing")

        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.object(retriever, "GOOGLE_API_KEY", "test-key"),
                patch.object(retriever, "VECTOR_STORE_DIR", Path(temporary_directory)),
                patch.object(
                    retriever.chromadb,
                    "PersistentClient",
                    return_value=chroma_client,
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "not initialised"):
                    retriever.retrieve_case_studies("test")


if __name__ == "__main__":
    unittest.main()
