"""Document reviewer agent."""

from google.adk.agents import LlmAgent
from google.genai import types

from config import MODEL_NAME
from schemas import DocumentReview


def create_reviewer_agent() -> LlmAgent:
    """Create the agent that reviews a document against its requirements."""
    return LlmAgent(
        name="reviewer_agent",
        description="Scores a draft for content and writing quality.",
        model=MODEL_NAME,
        mode="single_turn",
        include_contents="none",
        instruction="""Review the draft against the original specification,
structured requirements, and supplied case-study evidence. Score every field
from 0.0 to 1.0. Be evidence-led and specific.

Assess requirements coverage, appropriate length, supported claims, fidelity
to case-study facts, clarity, conciseness, sentence quality, human tone,
narrative flow, evidence quality, and case-study relevance. Flag sentences
over 25 words and excessive clauses when they materially affect readability.
Identify repetition, filler, generic AI-style wording, abrupt transitions, and
evidence that is dropped in without explaining relevance.

The content score reflects requirements coverage, accuracy, and evidence
quality. The style score reflects clarity, conciseness, sentence quality,
human tone, and narrative flow. Give selective, actionable revision
instructions that preserve strong sections and accurate evidence. Do not ask
for unsupported additions.

Original user specification:
{document_spec}

Structured requirements:
{requirements}

Selected case study evidence:
{case_study_evidence}

Draft to review:
{current_draft}
""",
        output_schema=DocumentReview,
        output_key="review",
        generate_content_config=types.GenerateContentConfig(temperature=0.1),
    )
