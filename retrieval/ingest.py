"""Knowledge-base ingestion into Chroma."""

import re
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

import chromadb
from google import genai
from google.genai import types

from config import (
    CHROMA_COLLECTION_NAME,
    CHUNK_SIZE,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    GOOGLE_API_KEY,
    KNOWLEDGE_DIR,
    VECTOR_STORE_DIR,
)


def parse_case_study(markdown: str) -> tuple[dict[str, str | list[str]], str]:
    """Parse the simple YAML-style metadata and narrative from a case study."""
    fenced_metadata = re.search(r"```yaml\s*\n(.*?)```", markdown, re.DOTALL)
    if fenced_metadata:
        metadata_text = fenced_metadata.group(1)
        narrative = markdown[: fenced_metadata.start()] + markdown[fenced_metadata.end() :]
    else:
        metadata_text, _, narrative = markdown.partition("\n\n")

    metadata: dict[str, str | list[str]] = {}
    current_list: str | None = None
    for raw_line in metadata_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- ") and current_list:
            values = metadata.setdefault(current_list, [])
            if isinstance(values, list):
                values.append(line[2:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            metadata[key] = value
            current_list = None
        else:
            metadata[key] = []
            current_list = key

    if not metadata.get("title"):
        raise ValueError("Case study metadata must include a title.")
    return metadata, narrative


def chunk_narrative(narrative: str, max_size: int = CHUNK_SIZE) -> list[str]:
    """Create paragraph-based chunks without splitting normal paragraphs."""
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", narrative):
        paragraph = paragraph.strip()
        if (
            not paragraph
            or paragraph.startswith("#")
            or paragraph == "---"
            or "fictional demonstration content" in paragraph.lower()
        ):
            continue
        paragraphs.append(paragraph)

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if current and len(candidate) > max_size:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _chroma_metadata(
    metadata: dict[str, str | list[str]],
    source_file: str,
) -> dict[str, str]:
    """Convert all source metadata into Chroma-compatible scalar values."""
    chroma_metadata = {
        key: " | ".join(value) if isinstance(value, list) else value
        for key, value in metadata.items()
    }
    capabilities = metadata.get("capabilities", [])
    chroma_metadata["capability"] = (
        " | ".join(capabilities) if isinstance(capabilities, list) else capabilities
    )
    chroma_metadata["source_file"] = source_file
    return chroma_metadata


def _embed_documents(client: genai.Client, documents: list[str]) -> list[list[float]]:
    """Generate retrieval-document embeddings in manageable batches."""
    embeddings: list[list[float]] = []
    for start in range(0, len(documents), EMBEDDING_BATCH_SIZE):
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=documents[start : start + EMBEDDING_BATCH_SIZE],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        if not response.embeddings:
            raise RuntimeError("Gemini returned no embeddings.")
        embeddings.extend(embedding.values for embedding in response.embeddings)
    return embeddings


def ingest_knowledge_base(status: Callable[[str], None] | None = None) -> int:
    """Rebuild the local Chroma collection from all case-study Markdown files."""
    def report(message: str) -> None:
        if status:
            status(message)

    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is required to ingest the knowledge base.")

    files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not files:
        raise RuntimeError(f"No Markdown case studies were found in {KNOWLEDGE_DIR}.")
    report(f"Reading {len(files)} case studies from {KNOWLEDGE_DIR.name}.")

    document_ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    for path in files:
        metadata, narrative = parse_case_study(path.read_text(encoding="utf-8"))
        chunks = chunk_narrative(narrative)
        if not chunks:
            raise ValueError(f"{path.name} has no narrative content to ingest.")
        for index, chunk in enumerate(chunks):
            document_ids.append(
                sha256(f"{path.name}:{index}".encode()).hexdigest()
            )
            documents.append(chunk)
            metadatas.append(_chroma_metadata(metadata, path.name))

    report(f"Prepared {len(documents)} case-study chunks.")
    report("Generating Gemini embeddings.")
    client = genai.Client(api_key=GOOGLE_API_KEY)
    embeddings = _embed_documents(client, documents)
    if len(embeddings) != len(documents):
        raise RuntimeError("Gemini returned an unexpected number of embeddings.")

    VECTOR_STORE_DIR.mkdir(exist_ok=True)
    report("Rebuilding the local Chroma collection.")
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    try:
        chroma_client.delete_collection(CHROMA_COLLECTION_NAME)
    except ValueError:
        pass
    collection = chroma_client.get_or_create_collection(
        CHROMA_COLLECTION_NAME,
        embedding_function=None,
    )
    collection.add(
        ids=document_ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    report(f"Ingestion complete: {len(documents)} chunks are ready for retrieval.")
    return len(documents)


if __name__ == "__main__":
    try:
        ingest_knowledge_base(print)
    except (RuntimeError, ValueError) as error:
        raise SystemExit(f"Ingestion failed: {error}") from error
