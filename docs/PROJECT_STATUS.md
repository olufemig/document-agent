# Project Status

## 1. Project Overview

Document Agent is a Python application that creates professional documents from a user specification, grounds them in a local fictional case-study library, reviews them, and revises them against deterministic quality thresholds.

It addresses the need to produce consistent, evidence-aware proposals and similar professional documents without manually assembling requirements, prior experience, and editorial feedback. Intended users are consultants, bid teams, analysts, and other professional writers who need a structured drafting workflow.

The current flow is: a Streamlit user enters a specification, the requirement analyzer extracts structured requirements, the application retrieves local case-study chunks, the case-study agent selects usable evidence, the writer drafts or revises, the reviewer scores the draft, Python applies the quality gate, and the final editor makes an editorial-only pass.

Main technologies are Python 3.12, Google ADK, Gemini, Pydantic, ChromaDB, LlamaIndex retrieval components, and Streamlit.

## 2. Current Architecture

The application uses five independent Google ADK `LlmAgent` instances. It does not use `SequentialAgent`, `LoopAgent`, graph workflows, a root workflow agent, or a coordinator agent. `agent.py` orchestrates each ADK agent through a fresh `Runner` using a shared `InMemorySessionService` session.

The orchestration, retrieval call, de-duplication, quality gate, maximum iteration rule, and error handling are normal Python code. Session state carries the document specification, structured agent outputs, current draft, review, and selected evidence between agent runs.

Case studies are Markdown files in `knowledge/`. `retrieval/ingest.py` parses them, creates paragraph-based chunks, calls Gemini embeddings through `google-genai`, and rebuilds a local Chroma collection. `retrieval/retriever.py` uses LlamaIndex's Chroma adapter and Gemini embedding adapter to query that collection.

The frontend is Streamlit in `app.py`. There is no A2UI, AG-UI, React, JavaScript frontend, HTTP backend service, authentication layer, or deployment configuration.

Gemini is the only external service. `GOOGLE_API_KEY` is loaded from `.env`; no secret is committed. Chroma persists locally under `vector_store/` and is ignored by Git apart from `.gitkeep`.

```text
Streamlit UI
  |-- Ingest Case Studies --> Markdown parser --> Gemini embeddings --> ChromaDB
  |
  '-- Generate Document --> ADK session / Python orchestrator
                               |
                               +--> requirement_analyzer
                               +--> LlamaIndex + Chroma retrieval
                               +--> case_study_agent
                               +--> writer_agent <---- reviewer_agent
                               |       ^                  |
                               |       '--- Python loop ---'
                               '--> final_editor --> Streamlit results
```

## 3. Agent Inventory

All agents use `model=MODEL_NAME`, currently `gemini-flash-latest`, `mode="single_turn"`, `include_contents="none"`, and no ADK tools. They receive their inputs through ADK session-state placeholders in their prompts.

| Agent | File | Purpose | State read | State written | Structured output | Interaction |
| --- | --- | --- | --- | --- | --- | --- |
| `requirement_analyzer` | `agents/requirement_analyzer.py` | Extracts only explicit document requirements. | `document_spec` | `requirements` | `DocumentRequirements` | Runs first; retrieval and all later agents use its result. |
| `case_study_agent` | `agents/case_study_agent.py` | Selects source-grounded case-study evidence, up to three items. | `requirements`, `retrieved_evidence` | `case_study_evidence` | `EvidencePack` | Runs only when retrieval returns results; its pack is passed to writer and reviewer. |
| `writer_agent` | `agents/writer.py` | Produces a Markdown draft or selective revision. | `document_spec`, `requirements`, `case_study_evidence`, optional `current_draft`, optional `review` | `current_draft` | None; Markdown text | Runs once per draft/review cycle. |
| `reviewer_agent` | `agents/reviewer.py` | Scores the draft against requirements and evidence and issues revision instructions. | `document_spec`, `requirements`, `case_study_evidence`, `current_draft` | `review` | `DocumentReview` | Runs after every writer pass. |
| `final_editor` | `agents/final_editor.py` | Makes a final readability-only Markdown edit without changing substance. | `current_draft` | `final_document` | None; Markdown text | Runs after approval or after the maximum cycle count. |

The Python coordinator is `generate_document()` in `agent.py`; it is a function, not an ADK agent. It creates the session, runs the agents, calls retrieval, maintains draft history, and applies the deterministic quality decision.

## 4. End-to-End Workflow

1. The user enters a document specification in `app.py`.
2. `generate_document()` verifies the specification and `GOOGLE_API_KEY`, then creates an in-memory ADK session with `document_spec` and the initial no-evidence message.
3. `requirement_analyzer` writes JSON for `DocumentRequirements` to `requirements`.
4. Python creates a search string from purpose, keywords, required topics, and evidence needs. It calls `retrieve_case_studies()` with sector, capabilities, and `TOP_K_CASE_STUDIES`.
5. Retrieval uses Chroma semantic search. Python keeps the first/highest-ranked chunk for each case-study title.
6. If evidence exists, the retrieved `RetrievedEvidence` data is serialized into `retrieved_evidence`; `case_study_agent` writes an `EvidencePack` to `case_study_evidence`. If no results are relevant, the initial no-evidence message remains in state.
7. The writer creates a Markdown draft. The reviewer creates a structured review. The pair repeats until approval or five draft/review cycles.
8. The final editor produces the final Markdown document. `WorkflowResult` returns the document, evidence, review, history, and any error to Streamlit.

The implemented flow differs from a fully ADK-native workflow graph: coordination is explicit Python rather than `SequentialAgent` or `LoopAgent`. This is intentional in the current code because threshold decisions and the iteration cap are deterministic Python logic.

## 5. Review and Self-Improvement Loop

`reviewer_agent` scores requirements, accuracy, clarity, conciseness, sentence quality, human tone, narrative flow, evidence quality, and case-study relevance. Each dimension, plus `content_score` and `style_score`, is constrained by Pydantic to 0.0 through 1.0.

`is_approved()` in `agent.py` is deterministic:

```python
content_score >= 0.85 and style_score >= 0.80
```

Configured values in `config.py` are:

| Setting | Value |
| --- | --- |
| `CONTENT_THRESHOLD` | `0.85` |
| `STYLE_THRESHOLD` | `0.80` |
| `MAX_ITERATIONS` | `5` |

One iteration is one writer/reviewer cycle. The writer reads the persisted `current_draft` and `review`, so reviewer `revision_instructions` are available for the next pass. If no draft reaches both thresholds in five cycles, the latest draft is still passed to the final editor and `max_iterations_reached=True` is returned.

The LLM determines document wording, evidence selection, scores, issues, and revision instructions. Python determines state flow, retrieval invocation, unique-case selection, approval, maximum iterations, and when final editing occurs.

## 6. Writing and Style Controls

The writer prompt requires Markdown and a knowledgeable, professional, consultative voice. It calls for direct language, mostly 12-to-18-word sentences, avoidance of sentences over 25 words where possible, one main idea per sentence, two-to-four-sentence paragraphs, active voice, limited jargon, limited headings and bullets, and varied sentence openings.

It explicitly discourages repetition, filler, generic AI phrasing, unsupported case-study claims, and terms such as "Furthermore", "Moreover", "Additionally", "Leveraging", "Robust", and "Transformative" unless genuinely appropriate. It requires a connected narrative rather than a checklist response and asks revisions to preserve strong content and accurate evidence.

The reviewer checks requirements coverage, accuracy, repeated or verbose content, sentence length and excessive clauses, natural human tone, narrative transitions, and whether evidence is relevant and integrated rather than dropped in. The final editor only improves readability and is instructed not to add information or alter facts, recommendations, metrics, evidence, or conclusions.

## 7. Case Study Knowledge Base

Case studies are stored in `knowledge/` as 25 Markdown files. Each current file includes an explicit fictional demonstration-content notice. The covered sectors are Construction, Energy and Utilities, Financial Services, Government, Healthcare, Higher Education, Housing, Legal Services, Life Sciences, Logistics, Manufacturing, Media and Entertainment, Nonprofit, Rail, Retail, and Telecommunications.

Each source contains YAML-fenced or plain YAML-style metadata and a short narrative. The parser accepts both formats. The expected metadata fields used by the current files are `title`, `sector`, `client_type`, `capabilities`, `problem`, `solution`, `technologies`, `outcomes`, and `lessons`.

Ingestion uses `parse_case_study()` and `chunk_narrative()` in `retrieval/ingest.py`. It removes headings, separators, and the fictional-content notice, then accumulates whole paragraphs until `CHUNK_SIZE` (1,200 characters) would be exceeded. It generates `gemini-embedding-001` document embeddings in batches of 50 and rebuilds the `case_studies` collection in local ChromaDB.

Every Chroma chunk stores text, a deterministic SHA-256 ID based on filename and chunk index, and scalar metadata. This includes all parsed metadata converted to strings plus `capability` and `source_file`.

Retrieval defaults to `top_k=5`. LlamaIndex wraps the Chroma collection and uses `GeminiEmbedding` for a query embedding. It applies an exact sector metadata filter when a sector is available. Capabilities are appended to the semantic query rather than metadata-filtered because the stored capability value is a combined string. The workflow then keeps one best chunk per case-study title before evidence selection.

`case_study_agent` is instructed to use only supplied chunks, preserve title/source/chunk traceability, select no more than three items, and return no evidence rather than invent facts. The writer and reviewer repeat the prohibition on inventing case-study clients, metrics, technologies, outcomes, dates, or details.

Live ingestion has rebuilt the collection with 25 chunks, and a live retail retrieval query returned the expected demand forecasting and customer analytics studies. Full document generation through all Gemini agents remains unverified.

## 8. Data Models and Pydantic Schemas

All models are in `schemas.py` and use `extra="forbid"`. `Score` constrains numeric scores to 0.0 through 1.0.

| Model | Fields | Produced by | Consumed by |
| --- | --- | --- | --- |
| `DocumentRequirements` | document type, audience, sector, purpose, sections, topics, capabilities, word count, tone, evidence needs, keywords | Requirement analyzer | Coordinator, retrieval, writer, reviewer, UI |
| `RetrievedEvidence` | case study, source file, content, optional relevance score | Retriever | Coordinator, case-study agent, UI |
| `CaseStudyEvidence` | case study, source file, retrieved chunk, relevance, problem, approach, optional outcome, reusable fact, recommended section | Case-study agent | Writer, reviewer, UI |
| `EvidencePack` | up to three `CaseStudyEvidence` items | Case-study agent | Coordinator, writer, reviewer, UI |
| `ReviewScores` | nine detailed score dimensions | Reviewer | `DocumentReview`, UI |
| `DocumentReview` | content/style scores, detailed scores, strengths, issues, revision instructions | Reviewer | Quality gate, writer, UI |
| `DraftCycle` | iteration, draft, review | Coordinator | `WorkflowResult`, UI |
| `WorkflowResult` | final document, optional requirements/review, retrieved evidence, evidence pack, iteration data, approval flags, history, optional error | Coordinator | Streamlit UI |

## 9. User Interface

`app.py` implements a Streamlit interface with a 300-pixel document-specification text area prefilled with an NHS proposal example. It has `Ingest Case Studies` and `Generate Document` buttons.

The ingestion button invokes `ingest_knowledge_base()` and displays its status callback messages. The generation button calls `asyncio.run(generate_document(...))` and sends workflow progress messages to `st.status`.

For a result, the UI shows errors, an iteration-cap warning, final Markdown, content/style/iteration metrics, selected case-study titles, and reviewer issues plus revision instructions. The `View Agent Reasoning and Reviews` expander contains requirements JSON, retrieved evidence and source file names, selected evidence JSON, drafts, and reviews. It does not intentionally expose hidden chain-of-thought.

## 10. A2UI / AG-UI

Neither A2UI nor AG-UI is implemented. The repository has no A2UI renderer, A2A transport, AG-UI package, or frontend package manifest. Streamlit is the only current UI.

## 11. Project Structure

```text
document-agent/
├── agents/                 # Five Google ADK agent definitions and prompts
├── retrieval/              # Markdown ingestion and LlamaIndex/Chroma retrieval
├── knowledge/              # 25 fictional Markdown case studies
├── vector_store/           # Local Chroma persistence; generated internals ignored by Git
├── tests/                  # Offline unittest coverage
├── app.py                  # Streamlit UI entry point
├── agent.py                # Python workflow coordinator and quality loop
├── config.py               # Paths, environment loading, model and threshold constants
├── schemas.py              # Shared Pydantic models
├── pyproject.toml          # Project metadata and direct dependencies
├── requirements.txt        # uv-exported locked requirements
├── uv.lock                 # uv lockfile
├── .env.example            # Non-secret environment template
└── README.md               # Currently empty
```

`docs/` contains this status document. It was not present before this update.

## 12. Dependencies

The project requires Python `>=3.12` and uses uv. Direct dependencies from `pyproject.toml` are:

| Dependency | Purpose |
| --- | --- |
| `google-adk` | ADK agents, runners, and in-memory sessions |
| `google-genai` | Gemini generation configuration and ingestion embeddings |
| `chromadb` | Local persistent vector database |
| `llama-index-core` | Native index/retriever abstraction |
| `llama-index-vector-stores-chroma` | LlamaIndex adapter for Chroma |
| `llama-index-embeddings-gemini` | LlamaIndex Gemini query embedding adapter |
| `pydantic` | Structured outputs and workflow data validation |
| `python-dotenv` | Loading `.env` configuration |
| `streamlit` | User interface and native `AppTest` support |

There are no Node, React, or other frontend package files. `requirements.txt` is generated from uv's locked environment; `uv.lock` is the reproducibility source.

## 13. Configuration

`config.py` calls `load_dotenv(PROJECT_ROOT / ".env")` and reads `GOOGLE_API_KEY`. `.env.example` also documents `GOOGLE_GENAI_USE_VERTEXAI=FALSE`; the application code does not read that variable directly.

| Setting | Current value |
| --- | --- |
| `MODEL_NAME` | `gemini-flash-latest` |
| `EMBEDDING_MODEL` | `gemini-embedding-001` |
| `CONTENT_THRESHOLD` | `0.85` |
| `STYLE_THRESHOLD` | `0.80` |
| `MAX_ITERATIONS` | `5` |
| `TOP_K_CASE_STUDIES` | `5` |
| `MAX_CASE_STUDIES_IN_DOCUMENT` | `3` |
| `WORD_COUNT_TOLERANCE` | `0.10` |
| `CHUNK_SIZE` | `1,200` characters |
| `EMBEDDING_BATCH_SIZE` | `50` |

No API key value is documented here.

## 14. Commands Used to Run the Application

Install dependencies using uv:

```bash
uv venv
uv sync
```

Alternatively, install the exported requirements:

```bash
uv pip install -r requirements.txt
```

Create `.env` from `.env.example` and set `GOOGLE_API_KEY`, then ingest case studies:

```bash
uv run python -m retrieval.ingest
```

Run Streamlit:

```bash
uv run streamlit run app.py
```

Run all tests:

```bash
uv run python -m unittest discover -s tests -v
```

There is no separate backend process, frontend build command, formatter, or linter configured.

## 15. What Has Been Completed

- [x] uv-managed Python 3.12 project with locked dependencies
- [x] Environment template and ignored local secrets/vector-store contents
- [x] Five single-turn Google ADK agents with local prompts
- [x] Pydantic requirements, evidence, review, history, and result models
- [x] Deterministic approval gate and five-cycle writer/reviewer loop
- [x] Final editorial pass after approval or iteration exhaustion
- [x] Fictional local case-study knowledge base with 25 files
- [x] Markdown metadata parsing, paragraph chunking, Gemini embedding code, and Chroma rebuild code
- [x] LlamaIndex-backed Chroma semantic retrieval with sector filtering
- [x] Evidence selection, source traceability, and writer/reviewer evidence inputs
- [x] Streamlit document-generation and ingestion interface
- [x] Offline unit tests for ingestion, retrieval, workflow evidence integration, and initial UI controls

## 16. Work In Progress

The Streamlit UI and its initial `AppTest` are present in the working tree but are currently uncommitted. `app.py` is modified, and `tests/test_app.py` plus this status document are untracked according to the current Git status.

Live case-study ingestion and a live semantic retrieval query have been verified with a real API key. Full document generation still needs all five Gemini agents, revision cycles, final editing, and Streamlit interaction exercised together.

## 17. Not Yet Implemented

- A populated `README.md`; it is currently empty.
- Live end-to-end document-generation tests through all five Gemini agents.
- Automated CI, linting, formatting, type checking, or coverage configuration.
- Persistent application sessions, user accounts, authentication, authorization, audit storage, or production deployment configuration.
- A2UI, AG-UI, A2A, MCP, and any non-Streamlit frontend.
- Chroma incremental ingestion or change detection; ingestion deliberately rebuilds the collection.

## 18. Important Design Decisions

- Google ADK `LlmAgent` instances and Pydantic `output_schema` are used for agent roles and structured outputs.
- Orchestration is ordinary Python with `InMemorySessionService` and `Runner`, not ADK template workflow agents, so quality gates remain deterministic.
- `uv` is used for dependency and lockfile management.
- The quality gate is Python-controlled with thresholds of 0.85 content and 0.80 style.
- The loop is capped at five draft/review cycles.
- Retrieval is separated from document generation and only grounded evidence is supplied to the writer.
- Case-study prompts prohibit invented source facts and preserve source file/chunk traceability.
- Markdown parsing is deliberately small and supports the two metadata layouts present in the repository.
- LlamaIndex was introduced specifically for native Chroma retrieval and Gemini query embeddings.
- Streamlit was chosen as the current fixed UI; A2UI was discussed but not added.

## 19. Known Issues and Technical Debt

- `README.md` is empty despite being declared as the project readme in `pyproject.toml`.
- `llama-index-embeddings-gemini` emits an upstream warning because it imports the deprecated `google.generativeai` package. The current code uses it for retrieval query embeddings while ingestion uses the newer `google-genai` SDK. Live compatibility with `gemini-embedding-001` still needs verification.
- The local `case_studies` collection was rebuilt successfully with 25 chunks. Generation still intentionally fails with an ingestion instruction when the collection is absent.
- Tests mock ADK, Gemini, LlamaIndex, and Chroma interactions; they do not validate real API responses, embedding dimensions, or ADK session-state output behavior end to end.
- Retrieval filters only sector as Chroma metadata. Capabilities are appended to the semantic query because stored capability metadata is combined text.
- The metadata parser only requires a title. It does not validate every expected case-study metadata field before ingestion.
- Ingestion now catches both `ValueError` and Chroma's `NotFoundError` when rebuilding an empty collection. This was corrected after the first live ingestion attempt exposed the missing exception path.
- The UI calls `asyncio.run()` directly during the Streamlit request and does not use a background worker. It provides status updates but does not support cancellation or concurrent runs.
- There are no TODO, FIXME, XXX, HACK, or `NotImplemented` markers in tracked source/document files found by the repository search.

## 20. Testing and Verification

The current suite uses standard-library `unittest` plus Streamlit's native `AppTest`.

| Test file | Coverage |
| --- | --- |
| `tests/test_ingest.py` | Fenced/plain metadata parsing, chunk cleanup, mocked embedding/Chroma rebuild, metadata preservation, status messages, missing key |
| `tests/test_retriever.py` | Mocked native LlamaIndex retrieval, sector filter, capability query terms, missing store/key, empty/uninitialised collection |
| `tests/test_workflow.py` | Mocked retrieval-to-evidence integration, duplicate case removal, no-evidence route, ingestion-required error |
| `tests/test_app.py` | Streamlit title, specification text area, and primary buttons render |

The suite was run during this status update using `uv run python -m unittest discover -s tests -v`: 14 tests passed. The test process emits a harmless Streamlit bare-mode warning and the upstream LlamaIndex Gemini deprecation warning.

Still required are live tests for all Gemini agent calls, score-driven looping, final editing, and Streamlit button actions using a real key and the populated Chroma collection.

## 21. Development Timeline

Git history is also available and all listed commits are dated 2026-08-26:

1. `2d00395` `first push`
2. `37041c2` `second push`
3. `b17b738` `application scaffolding`
4. `05e5392` `configuration and schema`
5. `5086494` `adk agents`
6. `b44f1b0` `workflow orchestrator`
7. `392aab3` `case studies`
8. `89a3cca` `case study ingestion`
9. `0dc7b7f` `agent retrieval`

The current UI implementation and `tests/test_app.py` are not yet represented in a commit. No earlier dated milestones can be reliably reconstructed from the repository.

## 22. Current State Summary

**Current maturity:** Functional prototype with offline tests, live ingestion, live retrieval, and an implemented local UI; document generation is not yet live-validated.

**Current working flow:** Streamlit input and ingestion controls feed a Python-orchestrated ADK drafting workflow with local Chroma retrieval, evidence selection, review, revisions, and final editing.

**Most important completed capability:** Grounded, traceable case-study retrieval is integrated into the deterministic document self-improvement loop.

**Largest outstanding gap:** A real API-key end-to-end document-generation run has not verified all five agent calls, revision behavior, final editing, and UI results together.

**Recommended next development task:** Run the Streamlit UI with the populated collection and execute one end-to-end document-generation workflow before writing the README.
