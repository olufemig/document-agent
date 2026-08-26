"""Application configuration values."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
CHROMA_COLLECTION_NAME = "case_studies"

load_dotenv(PROJECT_ROOT / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-flash-latest"
EMBEDDING_MODEL = "gemini-embedding-001"

CONTENT_THRESHOLD = 0.85
STYLE_THRESHOLD = 0.80
MAX_ITERATIONS = 5
TOP_K_CASE_STUDIES = 5
MAX_CASE_STUDIES_IN_DOCUMENT = 3
WORD_COUNT_TOLERANCE = 0.10
CHUNK_SIZE = 1_200
EMBEDDING_BATCH_SIZE = 50
