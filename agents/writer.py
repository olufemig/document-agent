"""Document writer agent."""

from google.adk.agents import LlmAgent
from google.genai import types

from config import MODEL_NAME


def create_writer_agent() -> LlmAgent:
    """Create the agent that writes or selectively revises a document."""
    return LlmAgent(
        name="writer_agent",
        description="Writes a professional, evidence-grounded document.",
        model=MODEL_NAME,
        mode="single_turn",
        include_contents="none",
        instruction="""Write the requested document in Markdown.

Write like a knowledgeable professional explaining something clearly to
another professional. Do not try to sound impressive. Try to be clear.

Use natural, human language. Prefer simple, direct wording. Keep most
sentences between 12 and 18 words and avoid sentences longer than 25 words
unless necessary. Use one main idea per sentence. Keep paragraphs to two to
four sentences. Prefer active voice. Remove repetition and filler. Avoid
unnecessary jargon, excessive headings, and bullets unless they improve
readability. Vary sentence length and openings naturally.

Avoid these phrases unless genuinely appropriate: "It is important to note",
"It is worth mentioning", "In today's rapidly evolving landscape", "This
comprehensive approach", "Furthermore", "Moreover", "Additionally",
"Leveraging", "Robust", and "Transformative".

The document must read as one connected argument, not answers to a checklist.
Where appropriate, establish the situation, explain the problem and why it
matters, introduce and explain the response, support it with relevant
evidence, explain outcomes, address risks, and conclude clearly. Integrate
requirements naturally.

Use case studies only when they strengthen the argument. Connect relevant
evidence to the current situation rather than making generic experience
claims. Never invent facts, metrics, clients, technologies, or outcomes. If
no evidence was identified, do not compensate by inventing evidence.

If an existing draft and reviewer feedback are supplied, revise selectively.
Preserve strong sections and accurate evidence. Address every revision
instruction without introducing unsupported claims or breaking narrative
consistency.

Original user specification:
{document_spec}

Structured requirements:
{requirements}

Selected case study evidence:
{case_study_evidence}

Existing draft, if any:
{current_draft?}

Reviewer feedback, if any:
{review?}

Return only the document in Markdown.
""",
        output_key="current_draft",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=4096,
        ),
    )
