"""Offline tests for case-study ingestion."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from retrieval import ingest


FENCED_CASE_STUDY = """# Example Case Study

```yaml
title: Example Data Platform
sector: Retail
client_type: Retailer
capabilities:
  - Data engineering
  - Analytics
problem: Fragmented reporting data.
solution: Created a shared data platform.
technologies:
  - BigQuery
  - dbt
outcomes:
  - Consistent reporting
lessons:
  - Agree metric definitions early
```

All content in this case study is fictional demonstration content.

The retailer had fragmented reporting data across several systems.

We created a shared data platform and common reporting definitions.
"""


class IngestionTests(unittest.TestCase):
    def test_parse_fenced_metadata_and_narrative(self) -> None:
        metadata, narrative = ingest.parse_case_study(FENCED_CASE_STUDY)

        self.assertEqual(metadata["title"], "Example Data Platform")
        self.assertEqual(metadata["capabilities"], ["Data engineering", "Analytics"])
        self.assertEqual(metadata["technologies"], ["BigQuery", "dbt"])
        self.assertIn("fragmented reporting data", narrative)

    def test_parse_plain_metadata(self) -> None:
        markdown = """title: Plain Metadata Case
sector: Healthcare
capabilities:
  - Data governance

The case-study narrative starts here.
"""

        metadata, narrative = ingest.parse_case_study(markdown)

        self.assertEqual(metadata["title"], "Plain Metadata Case")
        self.assertEqual(metadata["capabilities"], ["Data governance"])
        self.assertEqual(narrative.strip(), "The case-study narrative starts here.")

    def test_chunk_narrative_excludes_headers_and_notice(self) -> None:
        narrative = """# Heading

All content in this case study is fictional demonstration content.

First paragraph.

Second paragraph.
"""

        self.assertEqual(
            ingest.chunk_narrative(narrative),
            ["First paragraph.\n\nSecond paragraph."],
        )

    def test_ingestion_rebuilds_collection_with_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            knowledge_dir = root / "knowledge"
            vector_store_dir = root / "vector_store"
            knowledge_dir.mkdir()
            (knowledge_dir / "example.md").write_text(
                FENCED_CASE_STUDY,
                encoding="utf-8",
            )

            collection = Mock()
            chroma_client = Mock()
            chroma_client.delete_collection.side_effect = ValueError("Not found")
            chroma_client.get_or_create_collection.return_value = collection
            gemini_client = Mock()
            gemini_client.models.embed_content.side_effect = lambda **kwargs: SimpleNamespace(
                embeddings=[
                    SimpleNamespace(values=[0.1, 0.2]) for _ in kwargs["contents"]
                ]
            )
            status_messages: list[str] = []

            with (
                patch.object(ingest, "GOOGLE_API_KEY", "test-key"),
                patch.object(ingest, "KNOWLEDGE_DIR", knowledge_dir),
                patch.object(ingest, "VECTOR_STORE_DIR", vector_store_dir),
                patch.object(ingest.genai, "Client", return_value=gemini_client),
                patch.object(
                    ingest.chromadb,
                    "PersistentClient",
                    return_value=chroma_client,
                ),
            ):
                count = ingest.ingest_knowledge_base(status_messages.append)

        self.assertEqual(count, 1)
        self.assertIn("Reading 1 case studies from knowledge.", status_messages)
        self.assertIn("Generating Gemini embeddings.", status_messages)
        self.assertIn(
            "Ingestion complete: 1 chunks are ready for retrieval.",
            status_messages,
        )
        chroma_client.delete_collection.assert_called_once_with("case_studies")
        collection.add.assert_called_once()
        metadata = collection.add.call_args.kwargs["metadatas"][0]
        self.assertEqual(metadata["title"], "Example Data Platform")
        self.assertEqual(metadata["capability"], "Data engineering | Analytics")
        self.assertEqual(metadata["technologies"], "BigQuery | dbt")
        self.assertEqual(metadata["source_file"], "example.md")

    def test_ingestion_requires_api_key(self) -> None:
        with patch.object(ingest, "GOOGLE_API_KEY", None):
            with self.assertRaisesRegex(RuntimeError, "GOOGLE_API_KEY"):
                ingest.ingest_knowledge_base()


if __name__ == "__main__":
    unittest.main()
