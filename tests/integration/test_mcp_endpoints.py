"""Integration tests for MCP endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.agent.clo_agent import CLOAgent
from src.retrieval.vector_store import RetrievalResult, RetrievedChunk
from src.llm.mock import MockLLMProvider
from src.embedding.mock import MockEmbeddingProvider


@pytest.mark.integration
class TestMCPEndpoints:
    """Test the MCP tool endpoints via the agent layer."""

    @pytest.mark.asyncio
    async def test_analyze_legal_risk_full_flow(self):
        """E2E: query → retrieve → LLM → decision → audit."""
        # Mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        # Real embedding + mock LLM (real retriever needs real DB)
        embed = MockEmbeddingProvider()
        mock_retriever = AsyncMock()

        mock_retriever.retrieve_for_risk_analysis = AsyncMock(
            return_value=RetrievalResult(
                query=MagicMock(),
                chunks=[
                    RetrievedChunk(
                        chunk_id="c1",
                        document_id="doc-uuid-1",
                        legal_doc_id="gov-gdpr-2016-679",
                        chunk_index=5,
                        content="Article 33 GDPR: 72-hour breach notification obligation to supervisory authority.",
                        section="Article 33",
                        section_ref="Art. 33",
                        title="GDPR (EU) 2016/679",
                        jurisdiction="EU",
                        domain="regulatory",
                        law_type="GDPR",
                        effective_date=None,
                        source_url=None,
                        similarity=0.97,
                        token_count=30,
                    ),
                    RetrievedChunk(
                        chunk_id="c2",
                        document_id="doc-uuid-2",
                        legal_doc_id="gov-ccpa-2018",
                        chunk_index=3,
                        content="CCPA § 1798.150: Private right of action for data breaches. $100-$750 per consumer per incident.",
                        section="§ 1798.150",
                        section_ref="§ 1798.150",
                        title="California Consumer Privacy Act",
                        jurisdiction="US-CA",
                        domain="regulatory",
                        law_type="CCPA",
                        effective_date=None,
                        source_url=None,
                        similarity=0.91,
                        token_count=25,
                    ),
                ],
            )
        )

        llm = MockLLMProvider()
        agent = CLOAgent(llm_provider=llm, retriever=mock_retriever)

        with patch("src.storage.audit.write_audit_record", new_callable=AsyncMock):
            decision, retrieval = await agent.analyze_legal_risk(
                session=mock_session,
                query="We discovered a data breach affecting 10,000 EU customers. What are our obligations?",
                jurisdiction="EU",
                domain="regulatory",
            )

        # Assertions
        assert decision.decision_id is not None
        assert decision.exposure_level in ("HIGH", "MEDIUM", "LOW", "CRITICAL")
        assert decision.priority_rank >= 1
        assert decision.confidence > 0
        assert len(decision.legal_sources) >= 1
        assert decision.confidence > 0

        # Verify retrieval was called
        mock_retriever.retrieve_for_risk_analysis.assert_called_once()
        call_args = mock_retriever.retrieve_for_risk_analysis.call_args
        assert "data breach" in call_args.kwargs["situation_description"]

    @pytest.mark.asyncio
    async def test_prioritize_risk_full_flow(self):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        llm = MockLLMProvider()
        mock_retriever = AsyncMock()

        agent = CLOAgent(llm_provider=llm, retriever=mock_retriever)

        risks = [
            {
                "risk_id": "r1",
                "description": "GDPR Art. 33 breach notification failure",
                "exposure_level": "HIGH",
                "material_exposure": 5_000_000,
                "urgency_score": 9,
                "legal_basis": "GDPR Art. 33",
            },
            {
                "risk_id": "r2",
                "description": "CCPA opt-out mechanism missing",
                "exposure_level": "MEDIUM",
                "material_exposure": 750_000,
                "urgency_score": 6,
                "legal_basis": "CCPA § 1798.120",
            },
            {
                "risk_id": "r3",
                "description": "OSHA injury log not updated",
                "exposure_level": "LOW",
                "material_exposure": 25_000,
                "urgency_score": 3,
                "legal_basis": "OSHA 29 CFR 1904.29",
            },
        ]

        with patch("src.storage.audit.write_audit_record", new_callable=AsyncMock):
            result, sources = await agent.prioritize_risk(
                session=mock_session,
                risks=risks,
            )

        assert len(result.risks) == 3
        assert result.critical_count >= 0
        assert result.high_count >= 0
        # Risks should be sorted by priority score descending
        if len(result.risks) > 1:
            assert result.risks[0].combined_priority_score >= result.risks[1].combined_priority_score

    @pytest.mark.asyncio
    async def test_generate_remediation_full_flow(self):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        llm = MockLLMProvider()
        mock_retriever = AsyncMock()

        agent = CLOAgent(llm_provider=llm, retriever=mock_retriever)

        risk = {
            "decision_id": "test-decision-001",
            "description": "GDPR breach notification failure",
            "exposure_level": "HIGH",
            "priority_rank": 9,
            "material_exposure": 5_000_000,
            "legal_rationale": "Company failed to notify supervisory authority within 72 hours of a personal data breach.",
        }

        context = [
            {
                "document_id": "gov-gdpr-2016-679",
                "chunk_id": "chunk-042",
                "section": "Art. 33",
                "excerpt": "The controller shall notify the supervisory authority within 72 hours...",
            }
        ]

        with patch("src.storage.audit.write_audit_record", new_callable=AsyncMock):
            result = await agent.generate_remediation(
                session=mock_session,
                risk=risk,
                retrieved_context=context,
            )

        assert result.remediation_id is not None
        assert len(result.steps) >= 1
        # IMMEDIATE steps must have short timelines
        for step in result.steps:
            if step.priority == "IMMEDIATE":
                assert step.timeline_days <= 7
        assert "informational purposes" in result.disclaimer.lower()
        assert "legal advice" in result.disclaimer.lower()

    @pytest.mark.asyncio
    async def test_explain_decision_full_flow(self):
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        llm = MockLLMProvider()
        mock_retriever = AsyncMock()

        agent = CLOAgent(llm_provider=llm, retriever=mock_retriever)

        decision = {
            "decision_id": "test-decision-001",
            "priority_rank": 9,
            "exposure_level": "HIGH",
            "legal_rationale": "GDPR Article 33 requires notification within 72 hours.",
            "confidence": 0.88,
        }

        context = [
            {
                "document_id": "gov-gdpr-2016-679",
                "chunk_id": "chunk-042",
                "section": "Art. 33",
                "excerpt": "The controller shall notify the supervisory authority within 72 hours...",
            }
        ]

        with patch("src.storage.audit.write_audit_record", new_callable=AsyncMock):
            result = await agent.explain_decision(
                session=mock_session,
                decision=decision,
                retrieved_context=context,
            )

        assert result.decision_id == "test-decision-001"
        assert len(result.explanation) > 0
        assert len(result.decision_factors) >= 1
        assert len(result.sources_cited) >= 1

    def test_get_agent_status(self):
        llm = MockLLMProvider()
        mock_retriever = MagicMock()
        agent = CLOAgent(llm_provider=llm, retriever=mock_retriever)

        status = agent.get_status()
        assert status["status"] == "healthy"
        assert status["version"] == "0.1.0"
        assert set(status["capabilities"]) == {
            "analyze_legal_risk",
            "prioritize_risk",
            "generate_remediation",
            "explain_decision",
            "get_agent_status",
        }
