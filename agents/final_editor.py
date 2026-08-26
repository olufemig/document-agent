"""Final document editing agent."""

from google.adk.agents import LlmAgent
from google.genai import types

from config import MODEL_NAME
from schemas import FormattedDocument


def create_final_editor() -> LlmAgent:
    """Create the agent that makes the final editorial pass."""
    return LlmAgent(
        name="final_editor",
        description="Makes a final editorial pass without changing substance.",
        model=MODEL_NAME,
        mode="task",
        include_contents="none",
        instruction="""Perform a final human editing and semantic formatting
pass on the Markdown document below.

Do not change facts, meaning, recommendations, metrics, case-study evidence,
or substantive conclusions. Do not add new information.

Improve readability only: shorten unnecessarily long sentences, remove
repetition and filler, simplify awkward wording, improve paragraph
transitions, remove obvious AI-style wording, vary sentence rhythm naturally,
and keep paragraphs concise. Group sentences into paragraphs by their shared
idea, argument, or transition, never by a fixed sentence count. Split the
document into logical sections. Use a list only for genuinely related items or
a sequence, not for ordinary prose.

Return the required structured output. Use a concise document title and
meaningful section headings. Each paragraph block must contain one coherent
idea. Each list block must contain only its list items. Do not include Markdown
markers, HTML, tables, a contents section, or commentary in any field.

Document:
{current_draft}

""",
        output_schema=FormattedDocument,
        output_key="formatted_document",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
