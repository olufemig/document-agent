"""Final document editing agent."""

from google.adk.agents import LlmAgent
from google.genai import types

from config import MODEL_NAME


def create_final_editor() -> LlmAgent:
    """Create the agent that makes the final editorial pass."""
    return LlmAgent(
        name="final_editor",
        description="Makes a final editorial pass without changing substance.",
        model=MODEL_NAME,
        mode="single_turn",
        include_contents="none",
        instruction="""Perform a final human editing pass on the Markdown
document below.

Do not change facts, meaning, recommendations, metrics, case-study evidence,
or substantive conclusions. Do not add new information.

Improve readability only: shorten unnecessarily long sentences, remove
repetition and filler, simplify awkward wording, improve paragraph
transitions, remove obvious AI-style wording, vary sentence rhythm naturally,
and keep paragraphs concise. Retain a professional, natural voice and preserve
useful Markdown headings and lists.

Document:
{current_draft}

Return only the final document in Markdown.
""",
        output_key="final_document",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
