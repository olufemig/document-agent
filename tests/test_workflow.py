"""Offline tests for retrieval and evidence selection in the workflow."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import agent
from schemas import (
    CaseStudyEvidence,
    DocumentRequirements,
    DocumentReview,
    EvidencePack,
    FormattedDocument,
    RetrievedEvidence,
)


def review() -> DocumentReview:
    dimensions = [
        "requirements",
        "accuracy",
        "clarity",
        "conciseness",
        "sentence_quality",
        "human_tone",
        "narrative_flow",
        "evidence_quality",
        "case_study_relevance",
    ]
    return DocumentReview.model_validate(
        {
            "content_score": 0.9,
            "style_score": 0.9,
            "scores": {dimension: 0.9 for dimension in dimensions},
        }
    )


def formatted_document() -> FormattedDocument:
    return FormattedDocument.model_validate(
        {
            "title": "Final document",
            "sections": [
                {
                    "heading": "Summary",
                    "blocks": [{"kind": "paragraph", "text": "Ready."}],
                }
            ],
        }
    )


class WorkflowEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_retrieves_distinct_cases_and_selects_evidence(self) -> None:
        requirements = DocumentRequirements(
            purpose="Improve demand planning",
            sector="Retail",
            keywords=["demand forecast"],
            required_topics=["stock planning"],
            evidence_needed=["relevant delivery experience"],
            capabilities=["Forecasting"],
        )
        selected_evidence = EvidencePack(
            evidence=[
                CaseStudyEvidence(
                    case_study="Retail Demand Forecasting Programme",
                    source_file="retail-demand-forecast.md",
                    retrieved_chunk="Forecasting narrative.",
                    relevance=0.9,
                    problem="Inconsistent forecasts",
                    approach="Built a forecasting pipeline",
                    outcome="More consistent forecasts",
                    reusable_fact="The pipeline accounted for seasonal patterns.",
                    recommended_section="Relevant previous experience",
                )
            ]
        )
        retrieved = [
            RetrievedEvidence(
                case_study="Retail Demand Forecasting Programme",
                source_file="retail-demand-forecast.md",
                content="Best forecasting chunk.",
                relevance_score=0.9,
            ),
            RetrievedEvidence(
                case_study="Retail Demand Forecasting Programme",
                source_file="retail-demand-forecast.md",
                content="Second forecasting chunk.",
                relevance_score=0.8,
            ),
            RetrievedEvidence(
                case_study="Retail Customer Analytics Hub",
                source_file="retail-customer-analytics.md",
                content="Customer analytics chunk.",
                relevance_score=0.7,
            ),
        ]
        requirement_agent = SimpleNamespace(name="requirement")
        case_agent = SimpleNamespace(name="case")
        writer_agent = SimpleNamespace(name="writer")
        reviewer_agent = SimpleNamespace(name="reviewer")
        editor_agent = SimpleNamespace(name="editor")
        case_state_deltas: list[dict[str, object] | None] = []

        async def run_agent(
            current_agent: object,
            _session_service: object,
            _session_id: str,
            state_delta: dict[str, object] | None = None,
        ) -> dict[str, object]:
            if current_agent is requirement_agent:
                return {"requirements": requirements.model_dump_json()}
            if current_agent is case_agent:
                case_state_deltas.append(state_delta)
                return {"case_study_evidence": selected_evidence.model_dump_json()}
            if current_agent is writer_agent:
                return {"current_draft": "Draft document."}
            if current_agent is reviewer_agent:
                return {"review": review().model_dump_json()}
            return {"formatted_document": formatted_document().model_dump_json()}

        progress: list[str] = []
        with (
            patch.object(agent, "GOOGLE_API_KEY", "test-key"),
            patch.object(agent, "create_requirement_analyzer", return_value=requirement_agent),
            patch.object(agent, "create_case_study_agent", return_value=case_agent),
            patch.object(agent, "create_writer_agent", return_value=writer_agent),
            patch.object(agent, "create_reviewer_agent", return_value=reviewer_agent),
            patch.object(agent, "create_final_editor", return_value=editor_agent),
            patch.object(agent, "retrieve_case_studies", return_value=retrieved) as search,
            patch.object(agent, "_run_agent", side_effect=run_agent),
        ):
            result = await agent.generate_document("Create a retail proposal.", progress.append)

        self.assertEqual(result.final_document, "# Final document\n\n## Summary\n\nReady.")
        self.assertEqual(len(result.retrieved_evidence), 2)
        self.assertEqual(result.evidence_pack, selected_evidence)
        search.assert_called_once_with(
            "Improve demand planning demand forecast stock planning relevant delivery experience",
            sector="Retail",
            capabilities=["Forecasting"],
            top_k=5,
        )
        selected_chunks = json.loads(case_state_deltas[0]["retrieved_evidence"])
        self.assertEqual(len(selected_chunks), 2)
        self.assertIn(
            ":green[Case Study Retriever]: found Retail Demand Forecasting Programme",
            progress,
        )
        self.assertIn(
            ":green[Case Study Retriever]: found Retail Customer Analytics Hub", progress
        )
        self.assertIn(
            ":green[Case Study Selector]: selected Retail Demand Forecasting Programme",
            progress,
        )
        self.assertIn(":green[Requirement Analyzer]: requirements analysed", progress)
        self.assertIn(
            "Iteration 1/5 | :green[Document Writer]: draft generated", progress
        )
        self.assertIn(
            "Iteration 1/5 | :green[Document Reviewer]: quality threshold reached",
            progress,
        )
        self.assertIn(":green[Final Editor]: final document ready", progress)

    async def test_continues_without_case_study_evidence(self) -> None:
        requirements = DocumentRequirements(purpose="Write a proposal")
        requirement_agent = SimpleNamespace(name="requirement")
        writer_agent = SimpleNamespace(name="writer")
        reviewer_agent = SimpleNamespace(name="reviewer")
        editor_agent = SimpleNamespace(name="editor")

        async def run_agent(
            current_agent: object,
            _session_service: object,
            _session_id: str,
            state_delta: dict[str, object] | None = None,
        ) -> dict[str, object]:
            if current_agent is requirement_agent:
                return {"requirements": requirements.model_dump_json()}
            if current_agent is writer_agent:
                return {"current_draft": "Draft document."}
            if current_agent is reviewer_agent:
                return {"review": review().model_dump_json()}
            return {"formatted_document": formatted_document().model_dump_json()}

        with (
            patch.object(agent, "GOOGLE_API_KEY", "test-key"),
            patch.object(agent, "create_requirement_analyzer", return_value=requirement_agent),
            patch.object(agent, "create_writer_agent", return_value=writer_agent),
            patch.object(agent, "create_reviewer_agent", return_value=reviewer_agent),
            patch.object(agent, "create_final_editor", return_value=editor_agent),
            patch.object(agent, "retrieve_case_studies", return_value=[]),
            patch.object(agent, "create_case_study_agent") as case_agent,
            patch.object(agent, "_run_agent", side_effect=run_agent),
        ):
            result = await agent.generate_document("Create a proposal.")

        self.assertEqual(result.final_document, "# Final document\n\n## Summary\n\nReady.")
        self.assertEqual(result.retrieved_evidence, [])
        self.assertEqual(result.evidence_pack, EvidencePack())
        case_agent.assert_not_called()

    def test_renders_semantic_blocks_as_spaced_markdown(self) -> None:
        document = FormattedDocument.model_validate(
            {
                "title": "  Delivery  plan ",
                "sections": [
                    {
                        "heading": "Approach",
                        "blocks": [
                            {
                                "kind": "paragraph",
                                "text": "First line\ncontinues here.",
                            },
                            {
                                "kind": "bulleted_list",
                                "items": ["Clarify scope", "Deliver outcomes"],
                            },
                            {
                                "kind": "numbered_list",
                                "items": ["Plan", "Deliver"],
                            },
                        ],
                    }
                ],
            }
        )

        self.assertEqual(
            agent._render_final_document(document),
            "# Delivery plan\n\n## Approach\n\nFirst line continues here.\n\n"
            "- Clarify scope\n- Deliver outcomes\n\n1. Plan\n2. Deliver",
        )

    async def test_returns_error_when_retrieval_requires_ingestion(self) -> None:
        requirements = DocumentRequirements(purpose="Write a proposal")
        requirement_agent = SimpleNamespace(name="requirement")
        run_agent = AsyncMock(return_value={"requirements": requirements.model_dump_json()})

        with (
            patch.object(agent, "GOOGLE_API_KEY", "test-key"),
            patch.object(agent, "create_requirement_analyzer", return_value=requirement_agent),
            patch.object(
                agent,
                "retrieve_case_studies",
                side_effect=RuntimeError("The knowledge base is not initialised."),
            ),
            patch.object(agent, "_run_agent", run_agent),
        ):
            result = await agent.generate_document("Create a proposal.")

        self.assertEqual(result.requirements, requirements)
        self.assertIn("Case-study retrieval failed", result.error or "")
        self.assertEqual(run_agent.await_count, 1)


if __name__ == "__main__":
    unittest.main()
