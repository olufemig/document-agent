"""Case-study evidence selection agent."""

from google.adk.agents import LlmAgent
from google.genai import types

from config import MODEL_NAME
from schemas import EvidencePack


def create_case_study_agent() -> LlmAgent:
    """Create the agent that selects retrieved case-study evidence."""
    return LlmAgent(
        name="case_study_agent",
        description="Selects relevant, source-grounded case-study evidence.",
        model=MODEL_NAME,
        mode="task",
        include_contents="none",
        instruction="""You are a case study research agent.

Your job is to identify evidence from the supplied case study material that
could strengthen the document. Only use evidence contained in the retrieved
material. Do not invent clients, metrics, technologies, outcomes, dates, or
project details.

Select only genuinely relevant evidence. For every selected item, preserve the
provided case-study title, source file, and exact retrieved chunk. Describe
the problem, approach, outcome when present, a reusable fact, and the most
appropriate document section. Return no evidence if the material is not
relevant. Select at most three items.

Document requirements:
{requirements}

Retrieved case study material:
{retrieved_evidence}
""",
        output_schema=EvidencePack,
        output_key="case_study_evidence",
        generate_content_config=types.GenerateContentConfig(temperature=0.1),
    )
