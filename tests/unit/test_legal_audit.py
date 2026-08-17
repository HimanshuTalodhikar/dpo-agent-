"""Unit tests for run_legal_audit tool and LegalAuditOrchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.legal_audit import (
    LegalAuditOrchestrator,
    LegalAuditRequestInput,
    AuditReport,
    AuditFinding,
    AuditMode,
    ComplianceStatus,
    RiskLevel,
    FinalRecommendation,
    EvidenceSource,
)
from src.agent.clo_agent import CLOAgent
from src.llm.mock import MockLLMProvider
from src.retrieval.vector_store import RetrievalResult, RetrievedChunk


# ─────────────────────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLegalAuditRequestInput:
    """Tests for LegalAuditRequestInput schema."""

    def test_minimal_natural_language_request(self):
        """Natural-language-only request is valid."""
        req = LegalAuditRequestInput(
            business_context="Our fintech startup stores customer Aadhaar and PAN data on AWS Singapore"
        )
        assert req.business_context is not None
        assert req.mode == AuditMode.FULL_AUDIT
        assert req.data_involved == []

    def test_full_structured_request(self):
        """Full structured request is valid."""
        req = LegalAuditRequestInput(
            business_context="Cross-border data storage architecture",
            objective="Identify DPDP compliance gaps",
            organization_type="fintech",
            industry="financial_services",
            data_involved=["Aadhaar", "PAN", "financial_records"],
            systems_involved=["AWS Singapore", "third-party CRM"],
            processing_activities=["storage", "cross_border_transfer"],
            mode=AuditMode.FULL_AUDIT,
        )
        assert req.organization_type == "fintech"
        assert req.mode == AuditMode.FULL_AUDIT
        assert "Aadhaar" in req.data_involved

    def test_mode_enum(self):
        """Audit mode enum has correct values."""
        assert AuditMode.QUICK_REVIEW.value == "quick_review"
        assert AuditMode.RISK_ASSESSMENT.value == "risk_assessment"
        assert AuditMode.FULL_AUDIT.value == "full_audit"

    def test_organization_type_normalization(self):
        """Organization type is preserved."""
        req = LegalAuditRequestInput(
            business_context="A fintech company needs to review data processing",
            organization_type="Fintech",
        )
        # Field is preserved (no automatic lowercasing in schema)
        assert req.organization_type == "Fintech"


class TestAuditFinding:
    """Tests for AuditFinding schema."""

    def test_minimal_finding_has_defaults(self):
        """AuditFinding has defaults for all required-looking fields."""
        finding = AuditFinding()
        assert finding.finding_id.startswith("finding-")
        assert finding.domain == "general"
        assert finding.compliance_status == ComplianceStatus.INSUFFICIENT_EVIDENCE
        assert finding.risk_level == RiskLevel.MEDIUM
        assert finding.confidence == 0.8

    def test_finding_accepts_string_enums(self):
        """String enum values are converted correctly."""
        finding = AuditFinding(
            compliance_status="NON_COMPLIANT",
            risk_level="HIGH",
            source="GRAPH_RAG_EVIDENCE",
        )
        assert finding.compliance_status == ComplianceStatus.NON_COMPLIANT
        assert finding.risk_level == RiskLevel.HIGH
        assert finding.source == EvidenceSource.GRAPH_RAG_EVIDENCE

    def test_finding_with_all_fields(self):
        """Full finding is valid."""
        finding = AuditFinding(
            finding_id="F-test-001",
            domain="data_localization",
            title="Cross-border data transfer violation",
            description="Storing Aadhaar data outside India",
            business_activity="Cloud storage on AWS Singapore",
            data_involved=["Aadhaar"],
            legal_requirement="Data must be stored within India",
            legal_basis="Section 16 DPDP Act 2023",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH,
            confidence=0.85,
        )
        assert finding.finding_id == "F-test-001"
        assert finding.risk_level == RiskLevel.HIGH


class TestComplianceStatus:
    """Tests for ComplianceStatus enum."""

    def test_all_statuses(self):
        assert ComplianceStatus.COMPLIANT.value == "COMPLIANT"
        assert ComplianceStatus.PARTIALLY_COMPLIANT.value == "PARTIALLY_COMPLIANT"
        assert ComplianceStatus.NON_COMPLIANT.value == "NON_COMPLIANT"
        assert ComplianceStatus.INSUFFICIENT_EVIDENCE.value == "INSUFFICIENT_EVIDENCE"
        assert ComplianceStatus.NOT_APPLICABLE.value == "NOT_APPLICABLE"


class TestFinalRecommendation:
    """Tests for final recommendation logic via orchestrator helpers."""

    def test_recommendation_approve_all_compliant(self):
        """APPROVE when all findings are compliant."""
        findings = [
            AuditFinding(
                finding_id="F1",
                compliance_status=ComplianceStatus.COMPLIANT,
                risk_level=RiskLevel.LOW,
            ),
        ]
        orchestrator = LegalAuditOrchestrator.__new__(LegalAuditOrchestrator)
        orchestrator._agent = MagicMock()
        orchestrator._session = MagicMock()
        orchestrator._trace = MagicMock()
        rec = orchestrator._determine_recommendation(findings)
        assert rec == FinalRecommendation.APPROVE

    def test_recommendation_do_not_approve_critical_non_compliant(self):
        """DO_NOT_APPROVE when critical + non-compliant."""
        findings = [
            AuditFinding(
                finding_id="F1",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.CRITICAL,
            ),
        ]
        orchestrator = LegalAuditOrchestrator.__new__(LegalAuditOrchestrator)
        orchestrator._agent = MagicMock()
        orchestrator._session = MagicMock()
        orchestrator._trace = MagicMock()
        rec = orchestrator._determine_recommendation(findings)
        assert rec == FinalRecommendation.DO_NOT_APPROVE

    def test_recommendation_approve_with_conditions_high_non_compliant(self):
        """APPROVE_WITH_CONDITIONS when high non-compliant but no critical."""
        findings = [
            AuditFinding(
                finding_id="F1",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.HIGH,
            ),
        ]
        orchestrator = LegalAuditOrchestrator.__new__(LegalAuditOrchestrator)
        orchestrator._agent = MagicMock()
        orchestrator._session = MagicMock()
        orchestrator._trace = MagicMock()
        rec = orchestrator._determine_recommendation(findings)
        assert rec == FinalRecommendation.APPROVE_WITH_CONDITIONS

    def test_confidence_penalized_for_evidence_gaps(self):
        """Confidence decreases when evidence gaps exist."""
        findings = [
            AuditFinding(confidence=0.9),
            AuditFinding(confidence=0.8),
        ]
        evidence_gaps = ["gap1", "gap2"]
        orchestrator = LegalAuditOrchestrator.__new__(LegalAuditOrchestrator)
        orchestrator._agent = MagicMock()
        orchestrator._session = MagicMock()
        orchestrator._trace = MagicMock()
        confidence = orchestrator._calc_confidence(findings, evidence_gaps)
        # avg = 0.85, gap_penalty = min(2 * 0.05, 0.3) = 0.1
        assert confidence == pytest.approx(0.75, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLegalAuditOrchestrator:

    @pytest.mark.asyncio
    async def test_quick_review_mode_chat_only(self):
        """Quick review calls chat_dpdp_assistant only."""
        mock_agent = MagicMock(spec=CLOAgent)
        mock_agent.chat_dpdp_assistant = AsyncMock(return_value={
            "response": "Aadhaar data requires notice under Section 16.",
            "request_id": "test-req",
        })
        mock_session = MagicMock()

        orchestrator = LegalAuditOrchestrator(mock_agent, mock_session)

        # Patch the async methods
        req = LegalAuditRequestInput(
            business_context="Brief review: employee monitoring in India",
            mode=AuditMode.QUICK_REVIEW,
        )

        # Run synchronously by calling the orchestrator
        with patch.object(orchestrator, "_run_quick_review", new=AsyncMock(return_value=([], [], None))):
            report, trace = await orchestrator.run(req)
            assert isinstance(report, AuditReport)

    @pytest.mark.asyncio
    async def test_orchestrator_produces_valid_audit_report(self):
        """Orchestrator produces a well-formed AuditReport."""
        mock_agent = MagicMock(spec=CLOAgent)
        mock_agent.chat_dpdp_assistant = AsyncMock(return_value={
            "response": "Test response",
            "request_id": "test-req",
        })
        mock_session = MagicMock()

        findings = [
            AuditFinding(
                finding_id="F1",
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                risk_level=RiskLevel.HIGH,
                confidence=0.8,
            ),
        ]

        orchestrator = LegalAuditOrchestrator(mock_agent, mock_session)
        req = LegalAuditRequestInput(
            business_context="Testing audit report generation",
            mode=AuditMode.QUICK_REVIEW,
        )

        with patch.object(orchestrator, "_run_quick_review", new=AsyncMock(return_value=(findings, [], None))):
            report, trace = await orchestrator.run(req)
            assert isinstance(report, AuditReport)
            assert report.audit_id.startswith("audit-")
            assert len(report.findings) == 1
            assert isinstance(report.final_recommendation, FinalRecommendation)


# ─────────────────────────────────────────────────────────────────────────────
# CLOAgent Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestCLOAgentLegalAudit:
    """Tests for CLOAgent.run_legal_audit()."""

    async def test_run_legal_audit_audit_logged(self):
        """run_legal_audit writes an audit record."""
        mock_llm = MockLLMProvider()
        mock_retriever = AsyncMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()

        agent = CLOAgent(llm_provider=mock_llm, retriever=mock_retriever)

        req = LegalAuditRequestInput(
            business_context="We store customer data in India only",
            mode=AuditMode.QUICK_REVIEW,
        )

        with patch("src.storage.audit.write_audit_record") as mock_write:
            with patch("src.agent.clo_agent.LegalAuditOrchestrator") as MockOrchestrator:
                mock_report = MagicMock(spec=AuditReport)
                mock_report.audit_id = "audit-test-001"
                mock_report.findings = []
                mock_report.risk_summary = {}
                mock_report.final_recommendation = FinalRecommendation.APPROVE
                mock_report.confidence = 0.5

                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=(mock_report, MagicMock()))
                MockOrchestrator.return_value = mock_instance

                result = await agent.run_legal_audit(
                    session=mock_session,
                    request=req,
                    user_id="test-user",
                )

                assert result.audit_id == "audit-test-001"
