# Document Agent

Document Agent creates professional, evidence-grounded documents from a plain-language specification. It retrieves relevant material from the local fictional case-study library, drafts and reviews the document, then returns a semantically structured final document rendered as readable Markdown.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key in `GOOGLE_API_KEY`

## Setup

Create a local environment file from the template and add the API key:

```powershell
Copy-Item .env.example .env
```

```dotenv
GOOGLE_API_KEY=your-api-key
```

Install the locked dependencies:

```powershell
uv sync
```

## Run the App

```powershell
uv run streamlit run app.py
```

Open the local address displayed by Streamlit, normally `http://localhost:8501`.

## Use the Workflow

1. Click **Ingest Case Studies** to build the local Chroma vector store from `knowledge/`.
2. Enter a document specification describing the audience, sections, length, tone, and required evidence.
3. Click **Generate Document**.
4. Follow the workflow feedback. Agent names are green, drafting and review feedback includes `Iteration n/5`, and retrieved and selected case studies are named.
5. Review the final document, quality scores, case studies used, reviewer feedback, and the detailed workflow expander.

Starting a new generation clears the previous document, workflow feedback, and ingestion feedback.

## Document Generation

The workflow is coordinated in Python and uses five Google ADK agents:

| Agent | Responsibility |
| --- | --- |
| Requirement Analyzer | Extracts structured requirements from the specification. |
| Case Study Selector | Selects source-grounded evidence from retrieved case studies. |
| Document Writer | Creates the draft and applies review-driven revisions. |
| Document Reviewer | Scores content and style against the requirements. |
| Final Editor | Groups content into semantic sections, paragraphs, and lists. |

The writer and reviewer repeat for up to five iterations. Approval requires content at least `0.85` and style at least `0.80`. The final editor returns semantic content blocks; the application renders those blocks into consistently spaced Markdown with a title, section headings, paragraphs, and lists.

## Case Studies

The Markdown case studies in `knowledge/` are fictional demonstration content. Ingestion creates or rebuilds the local Chroma store in `vector_store/`. Re-ingest after changing a case study.

## Tests

Run the complete offline test suite:

```powershell
uv run python -m unittest tests.test_agents tests.test_workflow tests.test_app tests.test_ingest tests.test_retriever
```

The suite mocks external Gemini, ADK, Chroma, and LlamaIndex interactions. It does not make API calls.

## Docker

Build and run the app with Docker:

```powershell
docker build -t document-agent .
docker run --rm -p 8501:8501 --env-file .env document-agent
```

The container exposes port `8501` and has a healthcheck against Streamlit's `/_stcore/health` endpoint. `.env` and the local `vector_store/` are excluded from the image. Ingest the included case studies after starting the container.

## Project Layout

```text
agents/       ADK agent definitions
knowledge/    Fictional source case studies
retrieval/    Ingestion and semantic retrieval
tests/        Offline unit and Streamlit UI tests
agent.py      Workflow coordinator
app.py        Streamlit application
schemas.py    Structured workflow and final-document models
```

For implementation detail and current limitations, see [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).
