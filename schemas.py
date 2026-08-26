"""Shared Pydantic models for the document workflow."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


Score = Annotated[float, Field(ge=0.0, le=1.0)]


class DocumentRequirements(BaseModel):
    """Requirements extracted from the user's document specification."""

    model_config = ConfigDict(extra="forbid")

    document_type: str | None = None
    audience: str | None = None
    sector: str | None = None
    purpose: str
    required_sections: list[str] = Field(default_factory=list)
    required_topics: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    word_count: int | None = Field(default=None, gt=0)
    tone: str | None = None
    evidence_needed: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class RetrievedEvidence(BaseModel):
    """A chunk returned by semantic retrieval."""

    model_config = ConfigDict(extra="forbid")

    case_study: str
    source_file: str
    content: str
    relevance_score: Score | None = None


class CaseStudyEvidence(BaseModel):
    """A retrieved fact selected for use in a document."""

    model_config = ConfigDict(extra="forbid")

    case_study: str
    source_file: str
    retrieved_chunk: str
    relevance: Score
    problem: str
    approach: str
    outcome: str | None = None
    reusable_fact: str
    recommended_section: str


class EvidencePack(BaseModel):
    """The selected case-study evidence available to the writer."""

    model_config = ConfigDict(extra="forbid")

    evidence: list[CaseStudyEvidence] = Field(default_factory=list, max_length=3)


class ReviewScores(BaseModel):
    """Detailed scoring dimensions used by the reviewer."""

    model_config = ConfigDict(extra="forbid")

    requirements: Score
    accuracy: Score
    clarity: Score
    conciseness: Score
    sentence_quality: Score
    human_tone: Score
    narrative_flow: Score
    evidence_quality: Score
    case_study_relevance: Score


class DocumentReview(BaseModel):
    """The reviewer decision and instructions for a potential revision."""

    model_config = ConfigDict(extra="forbid")

    content_score: Score
    style_score: Score
    scores: ReviewScores
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    revision_instructions: list[str] = Field(default_factory=list)


class DraftCycle(BaseModel):
    """A draft and its review, retained for the Streamlit progress view."""

    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=1)
    draft: str
    review: DocumentReview


class WorkflowResult(BaseModel):
    """The final data returned to the Streamlit interface."""

    model_config = ConfigDict(extra="forbid")

    final_document: str
    requirements: DocumentRequirements
    evidence_pack: EvidencePack
    review: DocumentReview
    iterations: int = Field(ge=1)
    approved: bool
    max_iterations_reached: bool
    history: list[DraftCycle] = Field(default_factory=list)
