"""
Legal Audit Orchestration — run_legal_audit MCP tool implementation.

Produces a structured legal audit by orchestrating the existing 6 MCP tools:
    chat_dpdp_assistant → analyze_legal_risk → prioritize_risk →
    generate_remediation → explain_decision → structured audit report
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditMode(str, Enum):
    QUICK_REVIEW = "quick_review"
    RISK_ASSESSMENT = "risk_assessment"
    FULL_AUDIT = "full_audit"


class FinalRecommendation(str, Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_CONDITIONS = "APPROVE_WITH_CONDITIONS"
    DO_NOT_APPROVE = "DO_NOT_APPROVE"


class EvidenceSource(str, Enum):
    GRAPH_RAG_EVIDENCE = "GRAPH_RAG_EVIDENCE"
    AGENT_INFERENCE = "AGENT_INFERENCE"
    RETRIEVAL_ENGINE = "RETRIEVAL_ENGINE"


# ─────────────────────────────────────────────────────────────────────────────
# Input schema
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field


class LegalAuditRequestInput(BaseModel):
    """Input to the run_legal_audit tool.

    All fields are optional except business_context. The agent can accept
    natural language alone or highly structured input.
    """

    business_context: str = Field(
        description=(
            "Business scenario requiring legal audit — free text describing the data "
            "processing activity, infrastructure, and jurisdiction. "
            "Example: 'Our fintech startup stores customer Aadhaar and PAN data on AWS "
            "Singapore. What are our DPDP Act compliance obligations?'"
        ),
        min_length=10,
    )

    objective: str | None = Field(
        default=None,
        description="Specific audit objective if narrowing scope (e.g. 'identify DPDP Act gaps').",
    )

    organization_type: str | None = Field(
        default=None,
        description="Type of organization (e.g. 'fintech', 'healthcare_provider', 'ecommerce').",
    )

    industry: str | None = Field(
        default=None,
        description="Industry sector for context (e.g. 'financial_services', 'healthcare').",
    )

    jurisdiction: str | None = Field(
        default="India",
        description="Primary legal jurisdiction for this audit (default: India).",
    )

    data_involved: list[str] = Field(
        default_factory=list,
        description="Specific data types involved (e.g. ['Aadhaar', 'PAN', 'financial_records']).",
    )

    systems_involved: list[str] | None = Field(
        default=None,
        description="Systems or infrastructure involved (e.g. ['AWS Singapore', 'third-party CRM']).",
    )

    processing_activities: list[str] | None = Field(
        default=None,
        description="Data processing activities (e.g. ['storage', 'cross_border_transfer', 'third_party_sharing']).",
    )

    user_id: str | None = Field(default=None, description="User performing this audit.")
    mode: AuditMode = Field(default=AuditMode.FULL_AUDIT, description="Audit depth mode.")


# ─────────────────────────────────────────────────────────────────────────────
# Audit Finding (individual finding within the report)
# ─────────────────────────────────────────────────────────────────────────────

class AuditFinding(BaseModel):
    """A single finding within the audit report."""

    finding_id: str = Field(default_factory=lambda: f"finding-{uuid.uuid4().hex[:8]}")
    domain: str = Field(
        default="general",
        description="Domain category (e.g. 'data_localization', 'consent', 'breach_notification', 'third_party')",
    )
    title: str = Field(default="", description="Short, descriptive finding title")
    description: str = Field(default="", description="Detailed description of the finding")
    business_activity: str = Field(default="", description="The specific business activity this finding relates to")
    data_involved: list[str] = Field(default_factory=list, description="Data types relevant to this finding")
    legal_requirement: str = Field(default="", description="What Indian law requires for this finding")
    legal_basis: str = Field(
        default="",
        description="Specific Indian statutory provision (e.g. 'Section 16 DPDP Act 2023')",
    )
    source: EvidenceSource = Field(
        default=EvidenceSource.GRAPH_RAG_EVIDENCE,
        description="Provenance of the legal basis",
    )
    evidence: str = Field(
        default="",
        description=(
            "Retrieved legal text or 'INSUFFICIENT_EVIDENCE' if Graph RAG "
            "did not retrieve relevant content for this finding"
        ),
    )
    compliance_status: ComplianceStatus = Field(
        default=ComplianceStatus.INSUFFICIENT_EVIDENCE,
        description="Current compliance status for this finding",
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Risk level for this finding",
    )
    reasoning: str = Field(
        default="",
        description="Concise, decision-relevant reasoning (not internal chain-of-thought)",
    )
    remediation_id: str | None = Field(
        default=None,
        description="Links to a remediation step in the remediation_plan if applicable",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in this finding (0.0-1.0)",
    )

    def model_post_init(self, __context: Any) -> None:
        # Auto-convert string enums
        if isinstance(self.compliance_status, str):
            try:
                self.compliance_status = ComplianceStatus(self.compliance_status)
            except ValueError:
                self.compliance_status = ComplianceStatus.INSUFFICIENT_EVIDENCE
        if isinstance(self.risk_level, str):
            try:
                self.risk_level = RiskLevel(self.risk_level)
            except ValueError:
                self.risk_level = RiskLevel.MEDIUM
        if isinstance(self.source, str):
            try:
                self.source = EvidenceSource(self.source)
            except ValueError:
                self.source = EvidenceSource.AGENT_INFERENCE


# ─────────────────────────────────────────────────────────────────────────────
# Remediation Plan (references existing RemediationOutput)
# ─────────────────────────────────────────────────────────────────────────────

# Forward reference — imported at runtime to avoid circular import
_RemediationOutput: Any = None


def _get_remediation_output() -> Any:
    global _RemediationOutput
    if _RemediationOutput is None:
        from ..agent.remediation import RemediationOutput
        _RemediationOutput = RemediationOutput
    return _RemediationOutput


# ─────────────────────────────────────────────────────────────────────────────
# Audit Execution Trace (internal)
# ─────────────────────────────────────────────────────────────────────────────

class AuditExecutionTrace(BaseModel):
    """Internal trace of what the orchestrator did."""

    audit_id: str = ""
    mode: AuditMode = AuditMode.FULL_AUDIT
    started_at: str = ""
    status: str = "running"  # running | success | partial | failed
    tools_invoked: list[str] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    retrieved_evidence: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Audit Report (final output)
# ─────────────────────────────────────────────────────────────────────────────

class AuditReport(BaseModel):
    """Final structured audit report returned by run_legal_audit."""

    audit_id: str = Field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:12]}")
    mode: AuditMode | None = Field(
        default=None,
        description="Audit mode used for this report",
    )
    executive_summary: str = Field(
        description="2-3 sentence executive summary of the audit",
    )
    business_context: str = Field(
        description="The business scenario that was audited",
    )
    identified_data_processing: list[str] = Field(
        default_factory=list,
        description="Data types and processing activities identified in the audit",
    )
    applicable_indian_requirements: list[str] = Field(
        default_factory=list,
        description="Key Indian statutory requirements applicable to this audit",
    )
    findings: list[AuditFinding] = Field(
        default_factory=list,
        description="Individual findings with compliance status and risk level",
    )
    risk_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings by risk level (e.g. {'CRITICAL': 1, 'HIGH': 2})",
    )
    prioritized_actions: list[str] = Field(
        default_factory=list,
        description="Top 5 prioritized remediation actions",
    )
    remediation_plan: dict[str, Any] | None = Field(
        default=None,
        description="Full remediation plan (references RemediationOutput schema)",
    )
    final_recommendation: FinalRecommendation = Field(
        description="Overall audit recommendation",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall audit confidence based on evidence quality",
    )
    evidence_gaps: list[str] = Field(
        default_factory=list,
        description="Areas where INSUFFICIENT_EVIDENCE was marked",
    )
    tools_invoked: list[str] = Field(
        default_factory=list,
        description="Which MCP tools were invoked during this audit",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of report generation",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Audit Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class LegalAuditOrchestrator:
    """Orchestrates the 6 MCP tools to produce a structured legal audit report.

    Usage:
        orchestrator = LegalAuditOrchestrator(agent=clo_agent, session=db_session)
        report, trace = await orchestrator.run(request)
    """

    def __init__(self, agent: Any, session: Any) -> None:
        self._agent = agent
        self._session = session
        self._trace = AuditExecutionTrace()

    async def run(
        self, request: LegalAuditRequestInput
    ) -> tuple[AuditReport, AuditExecutionTrace]:
        """Run the audit based on the specified mode."""
        audit_id = f"audit-{uuid.uuid4().hex[:12]}"
        self._trace.audit_id = audit_id
        self._trace.mode = request.mode
        self._trace.started_at = datetime.now(timezone.utc).isoformat()

        start = time.perf_counter()

        logger.info(
            "legal_audit.start",
            audit_id=audit_id,
            mode=request.mode.value,
            business_context=request.business_context[:100],
        )

        # Route to appropriate mode
        match request.mode:
            case AuditMode.QUICK_REVIEW:
                findings, prio, rem = await self._run_quick_review(
                    request.business_context, request
                )
            case AuditMode.RISK_ASSESSMENT:
                findings, prio, rem = await self._run_risk_assessment(
                    request.business_context, request
                )
            case AuditMode.FULL_AUDIT:
                findings, prio, rem = await self._run_full_audit(
                    request.business_context, request
                )
            case _:
                findings, prio, rem = await self._run_full_audit(
                    request.business_context, request
                )

        exec_time_ms = int((time.perf_counter() - start) * 1000)

        # ── Post-processing: build report ─────────────────────────────────────
        risk_summary = self._build_risk_summary(findings)
        prioritized_actions = self._build_prioritized_actions(findings, prio)
        exec_summary = self._build_executive_summary(findings, request)
        recommendation = self._determine_recommendation(findings)
        evidence_gaps = self._collect_evidence_gaps(findings)
        confidence = self._calc_confidence(findings, evidence_gaps)

        # Handle RemediationOutput schema
        try:
            remediation_output_cls = _get_remediation_output()
            if rem and isinstance(rem, dict):
                remediation_result = rem
            else:
                remediation_result = rem.model_dump(mode="json") if rem else None
        except Exception:
            remediation_result = rem if isinstance(rem, dict) else None

        self._trace.status = "failed" if self._trace.errors and not findings else (
            "partial" if self._trace.errors else "success"
        )

        report = AuditReport(
            audit_id=audit_id,
            mode=request.mode,
            executive_summary=exec_summary,
            business_context=request.business_context,
            identified_data_processing=self._identify_data_processing(request),
            applicable_indian_requirements=self._identify_requirements(findings),
            findings=findings,
            risk_summary=risk_summary,
            prioritized_actions=prioritized_actions,
            remediation_plan=remediation_result,
            final_recommendation=recommendation,
            confidence=confidence,
            evidence_gaps=evidence_gaps,
            tools_invoked=self._trace.tools_invoked,
        )

        logger.info(
            "legal_audit.done",
            audit_id=audit_id,
            findings=len(findings),
            recommendation=recommendation.value,
            exec_time_ms=exec_time_ms,
        )

        return report, self._trace

    # ─── Mode runners ──────────────────────────────────────────────────────

    async def _run_quick_review(
        self,
        business_context: str,
        request: LegalAuditRequestInput,
    ) -> tuple[list[AuditFinding], list[dict[str, Any]], dict[str, Any] | None]:
        """Quick review: chat_dpdp_assistant only."""
        self._trace.tools_invoked.append("chat_dpdp_assistant")

        try:
            result = await self._agent.chat_dpdp_assistant(
                session=self._session,
                message=business_context,
                user_id=request.user_id,
            )
            self._trace.tool_results["chat_dpdp_assistant"] = result

            # Convert chat response to a single finding
            finding = self._chat_response_to_finding(
                response=result.get("response", ""),
                context=business_context,
                request=request,
            )
            return [finding], [], None
        except Exception as exc:
            logger.warning("legal_audit.chat_failed", error=str(exc))
            self._trace.errors.append(f"chat_dpdp_assistant failed: {str(exc)}")
            return [], [], None

    async def _run_risk_assessment(
        self,
        business_context: str,
        request: LegalAuditRequestInput,
    ) -> tuple[list[AuditFinding], list[dict[str, Any]], dict[str, Any] | None]:
        """Risk assessment: chat + analyze_legal_risk + explain_decision."""
        self._trace.tools_invoked.extend(["chat_dpdp_assistant", "analyze_legal_risk"])

        findings: list[AuditFinding] = []

        # Chat for context
        try:
            chat_result = await self._agent.chat_dpdp_assistant(
                session=self._session,
                message=business_context,
                user_id=request.user_id,
            )
            self._trace.tool_results["chat_dpdp_assistant"] = chat_result
        except Exception as exc:
            logger.warning("legal_audit.chat_failed", error=str(exc))
            self._trace.errors.append(f"chat_dpdp_assistant failed: {str(exc)}")

        # Analyze legal risk
        try:
            decision, retrieval = await self._agent.analyze_legal_risk(
                session=self._session,
                query=business_context,
                jurisdiction=request.jurisdiction,
                domain=None,
                user_id=request.user_id,
            )
            self._trace.tool_results["analyze_legal_risk"] = {
                "decision_id": decision.decision_id,
                "exposure_level": decision.exposure_level,
                "priority_rank": decision.priority_rank,
            }
            self._trace.retrieved_evidence = [c.to_source_dict() for c in retrieval.chunks]
            findings = self._decision_to_findings(
                decision=decision,
                context=business_context,
                request=request,
            )
        except Exception as exc:
            logger.warning("legal_audit.analyze_failed", error=str(exc))
            self._trace.errors.append(f"analyze_legal_risk failed: {str(exc)}")
            return [], [], None

        # Explain if we have a decision
        if findings:
            try:
                self._trace.tools_invoked.append("explain_decision")
                explanation = await self._agent.explain_decision(
                    session=self._session,
                    decision={"decision_id": self._trace.tool_results["analyze_legal_risk"]["decision_id"]},
                    retrieved_context=self._trace.retrieved_evidence,
                    user_id=request.user_id,
                )
                self._trace.tool_results["explain_decision"] = {
                    "explanation_id": explanation.explanation_id,
                    "factors_count": len(explanation.decision_factors),
                }
            except Exception as exc:
                logger.warning("legal_audit.explain_failed", error=str(exc))
                self._trace.errors.append(f"explain_decision failed: {str(exc)}")

        return findings, [], None

    async def _run_full_audit(
        self,
        business_context: str,
        request: LegalAuditRequestInput,
    ) -> tuple[list[AuditFinding], list[dict[str, Any]], dict[str, Any] | None]:
        """Full audit: parallelized to stay within server timeout limits.

        Phase 1 (parallel): chat_dpdp_assistant + analyze_legal_risk
        Phase 2 (parallel): prioritize_risk + generate_remediation + explain_decision
        """
        self._trace.tools_invoked.extend([
            "chat_dpdp_assistant",
            "analyze_legal_risk",
            "prioritize_risk",
            "generate_remediation",
            "explain_decision",
        ])

        findings: list[AuditFinding] = []
        prioritized_risks: list[dict[str, Any]] = []
        remediation_result: dict[str, Any] | None = None

        # ── Phase 1: run chat + analyze concurrently ──────────────────────────
        async def _phase1_chat():
            try:
                return await self._agent.chat_dpdp_assistant(
                    session=self._session,
                    message=business_context,
                    user_id=request.user_id,
                )
            except Exception as exc:
                logger.warning("legal_audit.chat_failed", error=str(exc))
                self._trace.errors.append(f"chat_dpdp_assistant failed: {str(exc)}")
                return None

        async def _phase1_analyze():
            try:
                decision, retrieval = await self._agent.analyze_legal_risk(
                    session=self._session,
                    query=business_context,
                    jurisdiction=request.jurisdiction,
                    domain=None,
                    user_id=request.user_id,
                )
                self._trace.tool_results["analyze_legal_risk"] = {
                    "decision_id": decision.decision_id,
                    "exposure_level": decision.exposure_level,
                    "priority_rank": decision.priority_rank,
                }
                self._trace.retrieved_evidence = [c.to_source_dict() for c in retrieval.chunks]
                return decision
            except Exception as exc:
                logger.warning("legal_audit.analyze_failed", error=str(exc))
                self._trace.errors.append(f"analyze_legal_risk failed: {str(exc)}")
                return None

        # Run Phase 1 tools concurrently
        chat_result, decision = await asyncio.gather(
            _phase1_chat(),
            _phase1_analyze(),
        )

        if chat_result:
            self._trace.tool_results["chat_dpdp_assistant"] = chat_result

        # Convert decision to findings if available
        if decision:
            findings = self._decision_to_findings(
                decision=decision,
                context=business_context,
                request=request,
            )

        # ── Phase 2: run prioritize + remediate + explain concurrently ────────
        if findings:
            risks_for_prioritization = [
                {
                    "risk_id": f.finding_id,
                    "description": f.title,
                    "exposure_level": f.risk_level.value,
                    "material_exposure": self._risk_to_material_exposure(f.risk_level),
                    "urgency_score": self._risk_to_urgency(f.risk_level),
                    "legal_basis": f.legal_basis,
                }
                for f in findings
            ]

            async def _phase2_prioritize():
                try:
                    prio_result, _ = await self._agent.prioritize_risk(
                        session=self._session,
                        risks=risks_for_prioritization,
                        user_id=request.user_id,
                    )
                    self._trace.tool_results["prioritize_risk"] = {
                        "total_exposure": prio_result.total_material_exposure,
                        "risks_prioritized": len(prio_result.risks),
                    }
                    return [r.model_dump() for r in prio_result.risks]
                except Exception as exc:
                    logger.warning("legal_audit.prioritize_failed", error=str(exc))
                    self._trace.errors.append(f"prioritize_risk failed: {str(exc)}")
                    return []

            async def _phase2_remediate():
                try:
                    top_risk = findings[0]
                    risk_dict = {
                        "decision_id": top_risk.finding_id,
                        "description": top_risk.title,
                        "exposure_level": top_risk.risk_level.value,
                        "priority_rank": 1,
                        "legal_basis": top_risk.legal_basis,
                        "material_exposure": self._risk_to_material_exposure(top_risk.risk_level),
                        "legal_rationale": top_risk.reasoning,
                    }
                    rem_result = await self._agent.generate_remediation(
                        session=self._session,
                        risk=risk_dict,
                        retrieved_context=self._trace.retrieved_evidence,
                        user_id=request.user_id,
                    )
                    self._trace.tool_results["generate_remediation"] = {
                        "remediation_id": rem_result.remediation_id,
                        "steps_count": len(rem_result.steps),
                    }
                    return rem_result.model_dump(mode="json")
                except Exception as exc:
                    logger.warning("legal_audit.remediation_failed", error=str(exc))
                    self._trace.errors.append(f"generate_remediation failed: {str(exc)}")
                    return None

            async def _phase2_explain():
                try:
                    analyze_result = self._trace.tool_results.get("analyze_legal_risk", {})
                    explain_result = await self._agent.explain_decision(
                        session=self._session,
                        decision={"decision_id": analyze_result.get("decision_id", "")},
                        retrieved_context=self._trace.retrieved_evidence,
                        user_id=request.user_id,
                    )
                    self._trace.tool_results["explain_decision"] = {
                        "explanation": explain_result.explanation,
                        "decision_id": explain_result.decision_id,
                    }
                    return explain_result
                except Exception as exc:
                    logger.warning("legal_audit.explain_failed", error=str(exc))
                    self._trace.errors.append(f"explain_decision failed: {str(exc)}")
                    return None

            # Run all Phase 2 tools concurrently
            prio_raw, rem_raw, _exp_raw = await asyncio.gather(
                _phase2_prioritize(),
                _phase2_remediate(),
                _phase2_explain(),
            )

            prioritized_risks = prio_raw or []
            remediation_result = rem_raw

            # Re-order findings by priority if available
            if prioritized_risks:
                priority_map = {
                    r["risk_id"]: r.get("combined_priority_score", 0)
                    for r in prioritized_risks
                }
                findings.sort(key=lambda f: priority_map.get(f.finding_id, 0), reverse=True)

        return findings, prioritized_risks, remediation_result

    # ─── Conversion helpers ─────────────────────────────────────────────────

    def _build_business_context(self, request: LegalAuditRequestInput) -> str:
        """Build a comprehensive context string from structured + natural language input."""
        parts = [request.business_context]

        if request.organization_type:
            parts.append(f"Organization Type: {request.organization_type}")
        if request.industry:
            parts.append(f"Industry: {request.industry}")
        if request.data_involved:
            parts.append(f"Data Involved: {', '.join(request.data_involved)}")
        if request.systems_involved:
            parts.append(f"Systems/Infrastructure: {', '.join(request.systems_involved)}")
        if request.processing_activities:
            parts.append(f"Processing Activities: {', '.join(request.processing_activities)}")
        if request.objective:
            parts.append(f"Audit Objective: {request.objective}")

        return "\n\n".join(parts)

    def _decision_to_findings(
        self,
        decision: Any,
        context: str,
        request: LegalAuditRequestInput,
    ) -> list[AuditFinding]:
        """Convert a DecisionOutput to one or more AuditFinding objects."""
        findings: list[AuditFinding] = []
        exposure = getattr(decision, "exposure_level", "MEDIUM")
        risk = self._exposure_to_risk(exposure)
        domain = self._infer_domain(context, request)

        finding = AuditFinding(
            domain=domain,
            title=f"Legal Risk: {getattr(decision, 'risk_category', 'General Compliance')}",
            description=(
                f"Risk category: {getattr(decision, 'risk_category', 'N/A')}. "
                f"Summary: {getattr(decision, 'summary', 'Risk identified through legal analysis.')}"
            ),
            business_activity=self._identify_business_activity(context, request),
            data_involved=request.data_involved,
            legal_requirement=self._extract_requirement(decision.legal_rationale if hasattr(decision, "legal_rationale") else ""),
            legal_basis=self._extract_legal_basis(decision.legal_sources if hasattr(decision, "legal_sources") else []),
            source=EvidenceSource.GRAPH_RAG_EVIDENCE if decision.legal_sources else EvidenceSource.AGENT_INFERENCE,
            evidence=self._extract_evidence(decision.legal_sources if hasattr(decision, "legal_sources") else []),
            compliance_status=self._exposure_to_compliance_status(exposure),
            risk_level=risk,
            reasoning=(
                decision.legal_rationale[:500]
                if hasattr(decision, "legal_rationale") and decision.legal_rationale
                else "Risk identified through legal analysis."
            ),
            remediation_id=None,
            confidence=decision.confidence or 0.8,
        )
        findings.append(finding)

        # Add additional findings for each actionable step
        if hasattr(decision, "actionable_steps_array") and decision.actionable_steps_array:
            for step in decision.actionable_steps_array[:3]:
                step_finding = AuditFinding(
                    domain=domain,
                    title=f"Action Required: {step[:80]}",
                    description=step,
                    business_activity=self._identify_business_activity(context, request),
                    data_involved=request.data_involved,
                    legal_requirement=self._extract_requirement(
                        decision.legal_rationale if hasattr(decision, "legal_rationale") else ""
                    ),
                    legal_basis=self._extract_legal_basis(
                        decision.legal_sources if hasattr(decision, "legal_sources") else []
                    ),
                    source=EvidenceSource.AGENT_INFERENCE,
                    evidence="Action derived from legal_rationale and actionable_steps",
                    compliance_status=ComplianceStatus.NON_COMPLIANT,
                    risk_level=risk,
                    reasoning=f"Required action identified: {step}",
                    confidence=decision.confidence or 0.7,
                )
                findings.append(step_finding)

        return findings

    def _chat_response_to_finding(
        self,
        response: str,
        context: str,
        request: LegalAuditRequestInput,
    ) -> AuditFinding:
        """Convert a chat response to a finding (for quick_review mode)."""
        return AuditFinding(
            domain=self._infer_domain(context, request),
            title="Legal Assessment (Quick Review)",
            description=response[:1000],
            business_activity=self._identify_business_activity(context, request),
            data_involved=request.data_involved,
            legal_requirement="Review the response for applicable legal requirements under Indian data protection law",
            legal_basis="DPDP Act 2023 & Rules 2025",
            source=EvidenceSource.AGENT_INFERENCE,
            evidence=response[:500],
            compliance_status=ComplianceStatus.INSUFFICIENT_EVIDENCE,
            risk_level=RiskLevel.MEDIUM,
            reasoning=response[:500],
            confidence=0.5,
        )

    # ─── Helper methods ─────────────────────────────────────────────────────

    def _identify_data_processing(self, request: LegalAuditRequestInput) -> list[str]:
        """Identify data processing activities from the request."""
        activities = []
        if request.data_involved:
            activities.extend(request.data_involved)
        if request.processing_activities:
            activities.extend(request.processing_activities)
        if not activities:
            activities = ["General data processing"]
        return list(dict.fromkeys(activities))  # dedupe preserve order

    def _identify_requirements(self, findings: list[AuditFinding]) -> list[str]:
        """Collect unique legal requirements from findings."""
        seen: set[str] = set()
        reqs: list[str] = []
        for f in findings:
            if f.legal_basis and f.legal_basis not in seen:
                seen.add(f.legal_basis)
                reqs.append(f.legal_basis)
        return reqs or ["DPDP Act 2023 (general compliance)"]

    def _build_risk_summary(self, findings: list[AuditFinding]) -> dict[str, int]:
        """Count findings by risk level."""
        summary: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings:
            level = f.risk_level.value if isinstance(f.risk_level, RiskLevel) else str(f.risk_level)
            if level in summary:
                summary[level] += 1
        return summary

    def _collect_evidence_gaps(self, findings: list[AuditFinding]) -> list[str]:
        """Identify findings with insufficient evidence."""
        gaps: list[str] = []
        for f in findings:
            if f.compliance_status == ComplianceStatus.INSUFFICIENT_EVIDENCE:
                gaps.append(f"Finding {f.finding_id}: {f.title} — insufficient evidence")
            if not f.evidence or f.evidence == "INSUFFICIENT_EVIDENCE":
                if f.title not in gaps:
                    gaps.append(f"Finding {f.finding_id}: {f.title} — no retrieved evidence")
        return gaps

    def _build_prioritized_actions(
        self,
        findings: list[AuditFinding],
        prioritized_risks: list[dict[str, Any]],
    ) -> list[str]:
        """Build a prioritized actions list from findings."""
        actions: list[tuple[int, str]] = []  # (priority_rank, action)

        # From prioritized risks
        for risk in prioritized_risks[:5]:
            rec = risk.get("recommendation", "")
            desc = risk.get("description", "")
            if rec:
                actions.append((0, f"[HIGH] {rec}"))
            elif desc:
                actions.append((0, f"[HIGH] {desc[:100]}"))

        # From HIGH/CRITICAL findings
        for f in findings:
            if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                actions.append((1, f"[{f.risk_level.value}] {f.title}: {f.reasoning[:80]}"))

        # Sort and deduplicate
        actions.sort(key=lambda x: x[0])
        seen: set[str] = set()
        unique: list[str] = []
        for _, action in actions:
            normalized = action.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(action)
            if len(unique) >= 5:
                break

        return unique

    def _build_executive_summary(
        self,
        findings: list[AuditFinding],
        request: LegalAuditRequestInput,
    ) -> str:
        """Build the executive summary."""
        if not findings:
            return (
                f"A quick review was conducted for the following scenario: "
                f"{request.business_context[:200]}. "
                f"No significant compliance risks were identified at this time. "
                f"A more detailed audit is recommended for comprehensive coverage of Indian data protection law."
            )

        critical_count = sum(1 for f in findings if f.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for f in findings if f.risk_level == RiskLevel.HIGH)
        non_compliant = sum(1 for f in findings if f.compliance_status == ComplianceStatus.NON_COMPLIANT)

        summary_parts = []

        if non_compliant > 0:
            summary_parts.append(
                f"{non_compliant} {'finding was' if non_compliant == 1 else 'findings were'} identified as NON_COMPLIANT "
                f"under Indian data protection law."
            )

        if critical_count > 0:
            summary_parts.append(
                f"{critical_count} CRITICAL risk{' was' if critical_count == 1 else 's were'} identified "
                f"requiring immediate attention."
            )

        if high_count > 0:
            summary_parts.append(
                f"{high_count} HIGH risk{' was' if high_count == 1 else 's were'} identified "
                f"that should be addressed promptly."
            )

        if not summary_parts:
            summary_parts.append(
                "The audit identified risks that are manageable with standard compliance controls."
            )

        summary_parts.append(
            f"A full {request.mode.value.replace('_', ' ')} was completed. "
            f"Detailed findings and remediation steps are provided below."
        )

        return " ".join(summary_parts)

    def _determine_recommendation(self, findings: list[AuditFinding]) -> FinalRecommendation:
        """Determine the final recommendation from findings."""
        if not findings:
            return FinalRecommendation.APPROVE_WITH_CONDITIONS

        has_critical = any(f.risk_level == RiskLevel.CRITICAL for f in findings)
        has_high = any(f.risk_level == RiskLevel.HIGH for f in findings)
        non_compliant = any(f.compliance_status == ComplianceStatus.NON_COMPLIANT for f in findings)
        insufficient = all(f.compliance_status == ComplianceStatus.INSUFFICIENT_EVIDENCE for f in findings)

        if insufficient:
            return FinalRecommendation.APPROVE_WITH_CONDITIONS

        if has_critical and non_compliant:
            return FinalRecommendation.DO_NOT_APPROVE

        if has_high and non_compliant:
            return FinalRecommendation.APPROVE_WITH_CONDITIONS

        if non_compliant:
            return FinalRecommendation.APPROVE_WITH_CONDITIONS

        return FinalRecommendation.APPROVE

    def _calc_confidence(self, findings: list[AuditFinding], evidence_gaps: list[str]) -> float:
        """Calculate overall audit confidence."""
        if not findings:
            return 0.4

        avg_confidence = sum(f.confidence for f in findings) / len(findings)

        # Penalize for evidence gaps
        gap_penalty = min(len(evidence_gaps) * 0.05, 0.3)

        return max(0.0, min(1.0, avg_confidence - gap_penalty))

    # ─── Domain & exposure helpers ─────────────────────────────────────────

    def _exposure_to_risk(self, exposure: str) -> RiskLevel:
        mapping = {
            "CRITICAL": RiskLevel.CRITICAL,
            "HIGH": RiskLevel.HIGH,
            "MEDIUM": RiskLevel.MEDIUM,
            "LOW": RiskLevel.LOW,
        }
        return mapping.get(exposure.upper() if isinstance(exposure, str) else "MEDIUM", RiskLevel.MEDIUM)

    def _exposure_to_compliance_status(self, exposure: str) -> ComplianceStatus:
        if exposure.upper() in ("CRITICAL", "HIGH"):
            return ComplianceStatus.NON_COMPLIANT
        if exposure.upper() == "MEDIUM":
            return ComplianceStatus.PARTIALLY_COMPLIANT
        return ComplianceStatus.COMPLIANT

    def _risk_to_material_exposure(self, risk: RiskLevel) -> float:
        mapping = {
            RiskLevel.CRITICAL: 10_000_000,
            RiskLevel.HIGH: 5_000_000,
            RiskLevel.MEDIUM: 1_000_000,
            RiskLevel.LOW: 100_000,
        }
        return mapping.get(risk, 1_000_000)

    def _risk_to_urgency(self, risk: RiskLevel) -> int:
        mapping = {
            RiskLevel.CRITICAL: 10,
            RiskLevel.HIGH: 7,
            RiskLevel.MEDIUM: 5,
            RiskLevel.LOW: 2,
        }
        return mapping.get(risk, 5)

    def _infer_domain(self, context: str, request: LegalAuditRequestInput) -> str:
        ctx_lower = context.lower()
        if any(k in ctx_lower for k in ["aadhaar", "pan", "kyc", "financial"]):
            return "financial_data"
        if any(k in ctx_lower for k in ["health", "medical", "patient", "hipaa"]):
            return "health_data"
        if any(k in ctx_lower for k in ["transfer", "cross border", "singapore", "us", "eu", "server"]):
            return "data_localization"
        if any(k in ctx_lower for k in ["consent", "notice", "privacy"]):
            return "consent"
        if any(k in ctx_lower for k in ["breach", "incident", "cert-in"]):
            return "breach_notification"
        if any(k in ctx_lower for k in ["third party", "vendor", "processor", "third-party"]):
            return "third_party"
        if request.data_involved:
            if any(d.lower() in ["aadhaar", "pan"] for d in request.data_involved):
                return "financial_data"
        return "general"

    def _identify_business_activity(self, context: str, request: LegalAuditRequestInput) -> str:
        if request.organization_type:
            return f"{request.organization_type} data processing"
        ctx_lower = context.lower()
        if "startup" in ctx_lower:
            return "Startup data processing operations"
        if "enterprise" in ctx_lower:
            return "Enterprise data processing"
        return "Business data processing"

    def _extract_requirement(self, rationale: str) -> str:
        if not rationale:
            return "DPDP Act 2023 compliance required"
        return rationale[:200]

    def _extract_legal_basis(self, sources: Any) -> str:
        if not sources:
            return ""
        if isinstance(sources, list):
            bases = []
            for s in sources[:3]:
                if isinstance(s, dict):
                    ref = s.get("section_ref") or s.get("reference") or s.get("law") or str(s)[:80]
                    bases.append(ref)
                elif hasattr(s, "section_ref"):
                    bases.append(s.section_ref)
            return "; ".join(bases)
        return str(sources)[:200]

    def _extract_evidence(self, sources: Any) -> str:
        if not sources:
            return "INSUFFICIENT_EVIDENCE"
        if isinstance(sources, list):
            excerpts = []
            for s in sources[:2]:
                if isinstance(s, dict):
                    exc = s.get("excerpt") or s.get("content") or str(s)[:200]
                    excerpts.append(exc[:200])
                elif hasattr(s, "excerpt"):
                    excerpts.append(s.excerpt[:200])
            return " | ".join(excerpts) if excerpts else "INSUFFICIENT_EVIDENCE"
        return str(sources)[:200]
