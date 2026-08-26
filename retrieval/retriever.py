"""Semantic retrieval over the case-study knowledge base."""

import chromadb
from chromadb.errors import NotFoundError
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import (
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
    GOOGLE_API_KEY,
    TOP_K_CASE_STUDIES,
    VECTOR_STORE_DIR,
)
from schemas import RetrievedEvidence


def retrieve_case_studies(
    query: str,
    sector: str | None = None,
    capabilities: list[str] | None = None,
    top_k: int = TOP_K_CASE_STUDIES,
) -> list[RetrievedEvidence]:
    """Return the most relevant case-study chunks from the local Chroma store."""
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is required to search case studies.")
    if top_k < 1:
        return []
    if not VECTOR_STORE_DIR.exists():
        raise RuntimeError(
            "The knowledge base is not initialised. Run `python -m retrieval.ingest`."
        )

    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    try:
        collection = chroma_client.get_collection(
            CHROMA_COLLECTION_NAME,
            embedding_function=None,
        )
    except (ValueError, NotFoundError) as error:
        raise RuntimeError(
            "The knowledge base is not initialised. Run `python -m retrieval.ingest`."
        ) from error
    if collection.count() == 0:
        return []

    filters = (
        MetadataFilters(filters=[MetadataFilter(key="sector", value=sector)])
        if sector
        else None
    )
    embedding = GeminiEmbedding(
        model_name=f"models/{EMBEDDING_MODEL}",
        task_type="retrieval_query",
        api_key=GOOGLE_API_KEY,
    )
    index = VectorStoreIndex.from_vector_store(
        ChromaVectorStore(chroma_collection=collection),
        embed_model=embedding,
    )
    capability_terms = ", ".join(capabilities or [])
    search_query = f"{query}\nCapabilities: {capability_terms}" if capability_terms else query
    matches = index.as_retriever(
        similarity_top_k=top_k,
        filters=filters,
    ).retrieve(search_query)

    return [
        RetrievedEvidence(
            case_study=str(match.node.metadata["title"]),
            source_file=str(match.node.metadata["source_file"]),
            content=match.node.get_content(),
            relevance_score=match.score,
        )
        for match in matches
    ]
