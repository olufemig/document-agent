# Project Status

## Overview

Document Agent is a functional Python prototype for generating professional documents grounded in fictional local case studies. Streamlit provides the interface; Google ADK and Gemini provide the language-model agents; ChromaDB and LlamaIndex provide local semantic retrieval.

The application requires a valid `GOOGLE_API_KEY` for ingestion and generation. It has offline test coverage, but a full live generation through all agents has not been verified as part of the automated suite.

## Architecture

`agent.py` coordinates five independent ADK `LlmAgent` instances, each in `mode="task"`, through a shared in-memory ADK session. Python, rather than an ADK workflow graph, owns retrieval, de-duplication, iteration, error handling, and the deterministic quality gate.

```text
Streamlit
  |-- Ingest Case Studies --> Markdown parser --> Gemini embeddings --> ChromaDB
  '-- Generate Document --> Requirement Analyzer --> Retrieval --> Case Study Selector
                                              --> Writer <--> Reviewer
                                              '--> Final Editor --> Streamlit
```

| Agent | Input | Output | Responsibility |
| --- | --- | --- | --- |
| `requirement_analyzer` | `document_spec` | `requirements` | Extracts explicit document requirements. |
| `case_study_agent` | Requirements and retrieved chunks | `case_study_evidence` | Selects up to three source-grounded evidence items. |
| `writer_agent` | Specification, requirements, evidence, draft, review | `current_draft` | Writes or selectively revises Markdown. |
| `reviewer_agent` | Specification, requirements, evidence, draft | `review` | Scores the draft and supplies revision instructions. |
| `final_editor` | Current draft | `formatted_document` | Organises content semantically without changing substance. |

## Workflow

1. The user enters a specification and starts generation.
2. Requirement Analyzer extracts `DocumentRequirements`.
3. Python queries Chroma using the requirement purpose, keywords, topics, evidence needs, sector, and capabilities.
4. Python keeps one highest-ranked chunk per case-study title and reports every retrieved title.
5. Case Study Selector chooses supported evidence and reports every selected title.
6. Writer produces a draft; Reviewer scores it. The pair repeats for at most five iterations.
7. Python approves a draft only when content is at least `0.85` and style is at least `0.80`.
8. Final Editor returns a `FormattedDocument` containing a title, semantic sections, paragraphs, and lists.
9. Python renders that structure into Markdown with reliable heading, paragraph, and list spacing.

The UI displays green agent names in generation feedback. Writer and reviewer feedback includes `Iteration n/5`. A new generation clears the prior document and all prior generation and ingestion feedback.

## Final-Document Formatting

The final editor does not return free-form Markdown. It returns these Pydantic models from `schemas.py`:

| Model | Purpose |
| --- | --- |
| `FormattedDocument` | One title and an ordered list of sections. |
| `DocumentSection` | A semantic heading and related content blocks. |
| `DocumentBlock` | A paragraph, bulleted list, or numbered list. |

`_render_final_document()` in `agent.py` normalises whitespace and renders those blocks into Markdown. This guarantees blank lines between headings, paragraphs, and lists while keeping paragraph grouping semantic rather than based on fixed sentence counts.

## Data and Configuration

- `knowledge/` contains fictional Markdown case studies.
- `vector_store/` contains generated local Chroma persistence and is excluded from Git and Docker build contexts.
- `.env` supplies `GOOGLE_API_KEY` and is excluded from Git and Docker build contexts.
- `config.py` contains model names, retrieval limits, quality thresholds, and chunking settings.

Current core settings:

| Setting | Value |
| --- | --- |
| `MODEL_NAME` | `gemini-flash-latest` |
| `EMBEDDING_MODEL` | `gemini-embedding-001` |
| `CONTENT_THRESHOLD` | `0.85` |
| `STYLE_THRESHOLD` | `0.80` |
| `MAX_ITERATIONS` | `5` |
| `TOP_K_CASE_STUDIES` | `5` |
| `MAX_CASE_STUDIES_IN_DOCUMENT` | `3` |

## Running and Testing

See the root [README](../README.md) for setup, Streamlit, ingestion, testing, and Docker commands.

The current offline suite contains 16 tests across agent construction, workflow behaviour, document rendering, Streamlit controls, ingestion, and retrieval. It mocks external services and does not prove live Gemini, ADK, or Chroma interoperability.

## Docker

`Dockerfile` uses Python 3.12 slim, runs Streamlit as a non-root user, exposes port `8501`, and defines a healthcheck for `http://localhost:8501/_stcore/health`. Docker image creation requires a running Docker Linux daemon.

## Limitations

- Generation, ingestion, and retrieval require a valid Gemini API key.
- Chroma ingestion rebuilds the collection rather than incrementally updating it.
- Sessions are in memory; there is no authentication, persistent user history, background worker, or cancellation.
- The test suite does not execute live external API calls.
- `llama-index-embeddings-gemini` currently produces an upstream deprecation warning for `google.generativeai`.
