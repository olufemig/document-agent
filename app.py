"""Streamlit entry point for the document agent."""

import asyncio

import streamlit as st

from agent import generate_document
from retrieval.ingest import ingest_knowledge_base
from schemas import WorkflowResult


EXAMPLE_SPECIFICATION = """Create a 500-word proposal for an NHS organisation.

The document must include:

- Executive summary
- Problem statement
- Proposed solution
- Three measurable benefits
- Delivery approach
- Risks and mitigations
- Relevant previous experience

Use a professional consultancy tone."""


def main() -> None:
    """Render the document-generation interface."""
    st.set_page_config(page_title="Document Agent", layout="wide")
    st.title("Document Agent")
    st.write("Create, review, and improve evidence-grounded professional documents.")

    document_spec = st.text_area(
        "Document specification",
        value=EXAMPLE_SPECIFICATION,
        height=300,
        help="Describe the document, audience, required sections, length, and tone.",
    )

    ingest_column, generate_column = st.columns(2)
    with ingest_column:
        ingest_status = st.empty()
        ingest_message = st.empty()
        if st.button("Ingest Case Studies"):
            with ingest_status.status("Ingesting case studies", expanded=True) as status:
                try:
                    count = ingest_knowledge_base(status.write)
                except (RuntimeError, ValueError) as error:
                    status.update(label="Ingestion failed", state="error")
                    ingest_message.error(str(error))
                else:
                    status.update(label="Case studies are ready", state="complete")
                    ingest_message.success(f"Ingested {count} case-study chunks.")

    with generate_column:
        if st.button("Generate Document", type="primary"):
            ingest_status.empty()
            ingest_message.empty()
            st.session_state.pop("workflow_result", None)
            with st.status("Generating document", expanded=True) as status:
                try:
                    result = asyncio.run(generate_document(document_spec, status.markdown))
                except Exception as error:
                    status.update(label="Generation failed", state="error")
                    st.error(f"Document generation failed: {error}")
                else:
                    st.session_state["workflow_result"] = result
                    if result.error:
                        status.update(label="Generation stopped", state="error")
                    else:
                        status.update(label="Document generation complete", state="complete")

    result = st.session_state.get("workflow_result")
    if not isinstance(result, WorkflowResult):
        return

    if result.error:
        st.error(result.error)
    if result.max_iterations_reached:
        st.warning("The maximum revision count was reached. Showing the latest edited draft.")
    if result.final_document:
        st.subheader("Final Document")
        with st.container(border=True):
            st.markdown(result.final_document)

    if result.review:
        st.subheader("Quality")
        content, style, iterations = st.columns(3)
        content.metric("Content score", f"{result.review.content_score:.2f}")
        style.metric("Style score", f"{result.review.style_score:.2f}")
        iterations.metric("Iterations", result.iterations)

    if result.evidence_pack.evidence:
        st.subheader("Case Studies Used")
        for evidence in result.evidence_pack.evidence:
            st.markdown(f"- {evidence.case_study}")

    if result.review:
        st.subheader("Reviewer Feedback")
        for issue in result.review.issues:
            st.markdown(f"- {issue}")
        for instruction in result.review.revision_instructions:
            st.markdown(f"- {instruction}")

    with st.expander("View Agent Reasoning and Reviews"):
        if result.requirements:
            st.markdown("**Requirements**")
            st.json(result.requirements.model_dump())
        if result.retrieved_evidence:
            st.markdown("**Retrieved Evidence**")
            for evidence in result.retrieved_evidence:
                st.markdown(
                    f"**{evidence.case_study}** from `{evidence.source_file}` "
                    f"(relevance: {evidence.relevance_score or 0:.2f})"
                )
                st.write(evidence.content)
        if result.evidence_pack.evidence:
            st.markdown("**Selected Evidence**")
            st.json(result.evidence_pack.model_dump())
        for cycle in result.history:
            st.markdown(f"**Draft {cycle.iteration}**")
            st.markdown(cycle.draft)
            st.json(cycle.review.model_dump())


if __name__ == "__main__":
    main()
