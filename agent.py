"""Document-generation workflow orchestration."""

import json

from collections.abc import Callable
from typing import TypeVar
from uuid import uuid4

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from agents.case_study_agent import create_case_study_agent
from agents.final_editor import create_final_editor
from agents.requirement_analyzer import create_requirement_analyzer
from agents.reviewer import create_reviewer_agent
from agents.writer import create_writer_agent
from config import (
    CONTENT_THRESHOLD,
    GOOGLE_API_KEY,
    MAX_ITERATIONS,
    STYLE_THRESHOLD,
    TOP_K_CASE_STUDIES,
)
from retrieval.retriever import retrieve_case_studies
from schemas import (
    DocumentRequirements,
    DocumentReview,
    DraftCycle,
    EvidencePack,
    RetrievedEvidence,
    WorkflowResult,
)


APP_NAME = "document_agent"
USER_ID = "streamlit_user"
ProgressCallback = Callable[[str], None]
ModelT = TypeVar("ModelT", bound=BaseModel)


def is_approved(review: DocumentReview) -> bool:
    """Apply the deterministic document approval rule."""
    return (
        review.content_score >= CONTENT_THRESHOLD
        and review.style_score >= STYLE_THRESHOLD
    )


def _parse_state_model(value: object, model_type: type[ModelT]) -> ModelT:
    """Validate an ADK structured-output value read from session state."""
    if isinstance(value, str):
        return model_type.model_validate_json(value)
    return model_type.model_validate(value)


async def _run_agent(
    agent: LlmAgent,
    session_service: InMemorySessionService,
    session_id: str,
    state_delta: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run one ADK agent and return its updated session state."""
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    message = types.Content(
        role="user",
        parts=[types.Part(text="Complete your assigned task using the session state.")],
    )
    async for _ in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
        state_delta=state_delta,
    ):
        pass

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    if session is None:
        raise RuntimeError("The ADK session was not available after the agent run.")
    return dict(session.state)


async def generate_document(
    document_spec: str,
    progress: ProgressCallback | None = None,
) -> WorkflowResult:
    """Generate, review, and iteratively improve a document specification."""
    def report(message: str) -> None:
        if progress:
            progress(message)

    if not document_spec.strip():
        return WorkflowResult(error="Enter a document specification before generating.")
    if not GOOGLE_API_KEY:
        return WorkflowResult(
            error="GOOGLE_API_KEY is missing. Add it to your local .env file before generating."
        )

    session_service = InMemorySessionService()
    session_id = str(uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
        state={
            "document_spec": document_spec,
            "case_study_evidence": "No relevant case study evidence was identified.",
        },
    )

    requirements: DocumentRequirements | None = None
    retrieved_evidence: list[RetrievedEvidence] = []
    evidence_pack = EvidencePack()
    current_draft = ""
    review: DocumentReview | None = None
    history: list[DraftCycle] = []

    try:
        state = await _run_agent(
            create_requirement_analyzer(),
            session_service,
            session_id,
        )
        requirements = _parse_state_model(state["requirements"], DocumentRequirements)
        report("Requirements analysed")
    except (KeyError, ValueError, TypeError) as error:
        return WorkflowResult(error=f"Could not analyse the requirements: {error}")
    except Exception as error:
        return WorkflowResult(error=f"Requirement analysis failed: {error}")

    try:
        query = " ".join(
            [
                requirements.purpose,
                *requirements.keywords,
                *requirements.required_topics,
                *requirements.evidence_needed,
            ]
        )
        seen_case_studies: set[str] = set()
        for evidence in retrieve_case_studies(
            query,
            sector=requirements.sector,
            capabilities=requirements.capabilities,
            top_k=TOP_K_CASE_STUDIES,
        ):
            if evidence.case_study in seen_case_studies:
                continue
            seen_case_studies.add(evidence.case_study)
            retrieved_evidence.append(evidence)

        if retrieved_evidence:
            report(f"{len(retrieved_evidence)} relevant case studies found")
            state = await _run_agent(
                create_case_study_agent(),
                session_service,
                session_id,
                state_delta={
                    "retrieved_evidence": json.dumps(
                        [item.model_dump() for item in retrieved_evidence]
                    )
                },
            )
            evidence_pack = _parse_state_model(state["case_study_evidence"], EvidencePack)
            report(f"{len(evidence_pack.evidence)} case studies selected")
        else:
            report("No relevant case study evidence was identified")
    except (KeyError, ValueError, TypeError) as error:
        return WorkflowResult(
            requirements=requirements,
            retrieved_evidence=retrieved_evidence,
            error=f"Could not select case-study evidence: {error}",
        )
    except Exception as error:
        return WorkflowResult(
            requirements=requirements,
            retrieved_evidence=retrieved_evidence,
            error=f"Case-study retrieval failed: {error}",
        )

    for iteration in range(1, MAX_ITERATIONS + 1):
        try:
            state = await _run_agent(create_writer_agent(), session_service, session_id)
            current_draft = str(state["current_draft"])
            report(f"Draft {iteration} generated")
        except (KeyError, ValueError, TypeError) as error:
            return WorkflowResult(
                final_document=current_draft,
                requirements=requirements,
                retrieved_evidence=retrieved_evidence,
                evidence_pack=evidence_pack,
                review=review,
                iterations=len(history),
                history=history,
                error=f"Could not generate draft {iteration}: {error}",
            )
        except Exception as error:
            return WorkflowResult(
                final_document=current_draft,
                requirements=requirements,
                retrieved_evidence=retrieved_evidence,
                evidence_pack=evidence_pack,
                review=review,
                iterations=len(history),
                history=history,
                error=f"Draft {iteration} generation failed: {error}",
            )

        try:
            state = await _run_agent(create_reviewer_agent(), session_service, session_id)
            review = _parse_state_model(state["review"], DocumentReview)
            history.append(DraftCycle(iteration=iteration, draft=current_draft, review=review))
            report(
                f"Draft {iteration} review: content {review.content_score:.2f} / "
                f"style {review.style_score:.2f}"
            )
        except (KeyError, ValueError, TypeError) as error:
            return WorkflowResult(
                final_document=current_draft,
                requirements=requirements,
                retrieved_evidence=retrieved_evidence,
                evidence_pack=evidence_pack,
                iterations=len(history),
                history=history,
                error=f"Could not review draft {iteration}: {error}",
            )
        except Exception as error:
            return WorkflowResult(
                final_document=current_draft,
                requirements=requirements,
                retrieved_evidence=retrieved_evidence,
                evidence_pack=evidence_pack,
                iterations=len(history),
                history=history,
                error=f"Draft {iteration} review failed: {error}",
            )

        if is_approved(review):
            report("Quality threshold reached")
            break

    approved = review is not None and is_approved(review)
    max_iterations_reached = not approved

    try:
        state = await _run_agent(create_final_editor(), session_service, session_id)
        final_document = str(state["final_document"])
        report("Final editing complete")
    except (KeyError, ValueError, TypeError) as error:
        return WorkflowResult(
            final_document=current_draft,
            requirements=requirements,
            retrieved_evidence=retrieved_evidence,
            evidence_pack=evidence_pack,
            review=review,
            iterations=len(history),
            approved=approved,
            max_iterations_reached=max_iterations_reached,
            history=history,
            error=f"Final editing could not be completed: {error}",
        )
    except Exception as error:
        return WorkflowResult(
            final_document=current_draft,
            requirements=requirements,
            retrieved_evidence=retrieved_evidence,
            evidence_pack=evidence_pack,
            review=review,
            iterations=len(history),
            approved=approved,
            max_iterations_reached=max_iterations_reached,
            history=history,
            error=f"Final editing failed: {error}",
        )

    return WorkflowResult(
        final_document=final_document,
        requirements=requirements,
        retrieved_evidence=retrieved_evidence,
        evidence_pack=evidence_pack,
        review=review,
        iterations=len(history),
        approved=approved,
        max_iterations_reached=max_iterations_reached,
        history=history,
    )
