"""Requirement analysis agent."""

from google.adk.agents import LlmAgent
from google.genai import types

from config import MODEL_NAME
from schemas import DocumentRequirements


def create_requirement_analyzer() -> LlmAgent:
    """Create the agent that extracts document requirements."""
    return LlmAgent(
        name="requirement_analyzer",
        description="Converts a document specification into structured requirements.",
        model=MODEL_NAME,
        mode="single_turn",
        include_contents="none",
        instruction="""You analyse document specifications.

Extract only requirements explicitly stated or clearly named in the user's
specification. Do not invent an audience, sector, tone, word count, section,
topic, capability, evidence need, or keyword.

For capabilities, include only named professional or technical capabilities
that will help retrieve relevant case studies. Leave lists empty when the
specification does not provide relevant information.

User specification:
{document_spec}
""",
        output_schema=DocumentRequirements,
        output_key="requirements",
        generate_content_config=types.GenerateContentConfig(temperature=0.1),
    )
