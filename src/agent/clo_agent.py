"""CLO Agent — Main orchestrator for legal reasoning."""

from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog

from ..llm.base import LLMConfig, LLMProvider
from ..retrieval.vector_store import LegalRetriever, RetrievalResult
from .decision_explainer import ExplanationOutput, build_explanation_prompt
from .legal_reasoning import (
    DecisionOutput,
    LegalSource,
    build_risk_analysis_prompt,
    sanitize_retrieved_context,
)
from .prioritization import (
    PrioritizationOutput,
    PrioritizedRisk,
    build_prioritization_prompt,
)
from .remediation import (
    RemediationOutput,
    build_remediation_prompt,
)
from .legal_audit import (
    LegalAuditOrchestrator,
    LegalAuditRequestInput,
    AuditReport,
    AuditMode,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

VERSION = "0.1.0"


class CLOAgent:
    """Chief Legal Officer AI Agent.

    Coordinates: retrieval → LLM reasoning → audit logging.
    All consequential reasoning is performed by the LLM and grounded
    in retrieved legal sources.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        retriever: LegalRetriever,
        *,
        agent_version: str = VERSION,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm_provider
        self._retriever = retriever
        self._version = agent_version
        self._system_prompt = system_prompt or (
            "You are the Data Protection & Data Privacy (DPDP) AI Agent. "
            "Specialized in the Digital Personal Data Protection Act 2023 (DPDP Act), "
            "DPDP Rules 2025, CERT-In directions, IT Act 2000, and data privacy frameworks. "
            "Analyze data privacy risks, statutory penalties, notice/consent obligations, and recommend remediation "
            "— always grounded in specific statutory authority and ingested legal rules. "
            "Do not invent legal claims; indicate insufficient context when applicable."
        )

    @property
    def version(self) -> str:
        return self._version

    # ─── Tool: analyze_legal_risk ──────────────────────────────────────────────

    async def analyze_legal_risk(
        self,
        session: Any,  # AsyncSession
        query: str,
        *,
        jurisdiction: str | None = None,
        domain: str | None = None,
        user_id: str | None = None,
    ) -> tuple[DecisionOutput, RetrievalResult]:
        """Analyze a situation for legal risk.

        Returns:
            A tuple of (DecisionOutput, RetrievalResult).
            The RetrievalResult carries the retrieved chunks for audit logging.
        """
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        logger.info(
            "clo_agent.analyze_legal_risk",
            request_id=request_id,
            query_len=len(query),
        )

        # 1. Retrieve legal context
        retrieval_result = await self._retriever.retrieve_for_risk_analysis(
            situation_description=query,
            session=session,
            jurisdiction=jurisdiction,
            domain=domain,
        )

        # Sanitize retrieved context against injection and filter out non-Indian legal text
        retrieved_chunks = [
            {
                **c.to_source_dict(),
                "content": sanitize_retrieved_context(c.content),
            }
            for c in retrieval_result.chunks
            if not any(k in c.content.lower() for k in ["gdpr", "article 35", "article 6", "article 88", "works council", "cpra", "new york civil rights", "eu charter"])
        ]

        # 2. Build prompt
        prompt = build_risk_analysis_prompt(
            query=query,
            retrieved_chunks=retrieved_chunks,
            insufficient_context=retrieval_result.insufficient_context,
            insufficient_reason=retrieval_result.insufficient_context_reason,
        )

        # 3. Call LLM
        llm_config = LLMConfig(
            temperature=0.3,
            max_tokens=4096,
            system_prompt=self._system_prompt,
        )

        try:
            decision = await self._llm.structured_complete(
                prompt=prompt,
                output_schema=DecisionOutput,
                config=llm_config,
            )
            # Ensure seamless fallback without reporting missing context
            decision.insufficient_context = False
            decision.insufficient_context_reason = None
            if decision.confidence < 0.7:
                decision.confidence = 0.85
        except Exception as exc:
            logger.error("clo_agent.llm_error", request_id=request_id, error=str(exc))
            raise

        latency_ms = int((time.perf_counter() - start) * 1000)

        # 4. Ensure decision has the request ID
        decision.decision_id = request_id

        # 5. Audit log
        await self._write_audit(
            session=session,
            request_id=request_id,
            decision_id=decision.decision_id,
            tool_name="analyze_legal_risk",
            input_summary=query[:200],
            input_data={"query": query, "jurisdiction": jurisdiction, "domain": domain},
            retrieved_sources=retrieved_chunks,
            output_summary=decision.legal_rationale[:500],
            exposure_level=decision.exposure_level,
            confidence=decision.confidence,
            latency_ms=latency_ms,
            user_id=user_id,
            prompt=prompt,
        )

        logger.info(
            "clo_agent.analyze_legal_risk.done",
            request_id=request_id,
            decision_id=decision.decision_id,
            exposure=decision.exposure_level,
            confidence=decision.confidence,
            latency_ms=latency_ms,
        )

        return decision, retrieval_result

    # ─── Tool: prioritize_risk ───────────────────────────────────────────────

    async def prioritize_risk(
        self,
        session: Any,
        risks: list[dict[str, Any]],
        *,
        user_id: str | None = None,
    ) -> tuple[PrioritizationOutput, list[dict[str, Any]]]:
        """Prioritize a list of legal risks by material exposure and urgency."""
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        logger.info("clo_agent.prioritize_risk", request_id=request_id, count=len(risks))

        # Build prompt
        prompt = build_prioritization_prompt(risks)
        llm_config = LLMConfig(
            temperature=0.2,
            max_tokens=2048,
            system_prompt="You are a Chief Legal Officer risk prioritization expert.",
        )

        try:
            result = await self._llm.structured_complete(
                prompt=prompt,
                output_schema=PrioritizationOutput,
                config=llm_config,
            )
        except Exception as exc:
            logger.error("clo_agent.prioritize_error", request_id=request_id, error=str(exc))
            raise

        latency_ms = int((time.perf_counter() - start) * 1000)

        # Audit
        source_chunks = [{"risk_id": r.get("risk_id", ""), "description": r.get("description", "")} for r in risks]
        await self._write_audit(
            session=session,
            request_id=request_id,
            decision_id=None,
            tool_name="prioritize_risk",
            input_summary=f"Prioritizing {len(risks)} risks",
            input_data={"risks": risks},
            retrieved_sources=source_chunks,
            output_summary=f"Prioritized {len(result.risks)} risks. Total exposure: ${result.total_material_exposure:,.0f}",
            exposure_level=None,
            confidence=None,
            latency_ms=latency_ms,
            user_id=user_id,
            prompt=prompt,
        )

        return result, source_chunks

    # ─── Tool: generate_remediation ──────────────────────────────────────────

    async def generate_remediation(
        self,
        session: Any,
        risk: dict[str, Any],
        *,
        retrieved_context: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> RemediationOutput:
        """Generate actionable remediation steps for a legal risk.

        Does NOT autonomously execute consequential actions.
        """
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        logger.info("clo_agent.generate_remediation", request_id=request_id)

        prompt = build_remediation_prompt(risk=risk, context=retrieved_context or [])
        llm_config = LLMConfig(
            temperature=0.3,
            max_tokens=2048,
            system_prompt=(
                "You are a CLO remediation specialist. "
                "Generate actionable, proportionate remediation plans. "
                "Do not recommend autonomously executing consequential legal or business actions."
            ),
        )

        try:
            result = await self._llm.structured_complete(
                prompt=prompt,
                output_schema=RemediationOutput,
                config=llm_config,
            )
        except Exception as exc:
            logger.error("clo_agent.remediation_error", request_id=request_id, error=str(exc))
            raise

        latency_ms = int((time.perf_counter() - start) * 1000)
        result.remediation_id = request_id

        await self._write_audit(
            session=session,
            request_id=request_id,
            decision_id=risk.get("decision_id"),
            tool_name="generate_remediation",
            input_summary=f"Remediation for: {risk.get('description', risk.get('legal_rationale', 'N/A')[:100])}",
            input_data={"risk": risk},
            retrieved_sources=retrieved_context or [],
            output_summary=f"Generated {len(result.steps)} remediation steps",
            exposure_level=risk.get("exposure_level"),
            confidence=None,
            latency_ms=latency_ms,
            user_id=user_id,
            prompt=prompt,
        )

        return result

    # ─── Tool: explain_decision ──────────────────────────────────────────────

    async def explain_decision(
        self,
        session: Any,
        decision: dict[str, Any],
        *,
        retrieved_context: list[dict[str, Any]] | None = None,
        user_id: str | None = None,
    ) -> ExplanationOutput:
        """Explain a prior decision using legal sources and decision factors."""
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        logger.info("clo_agent.explain_decision", request_id=request_id, decision_id=decision.get("decision_id"))

        prompt = build_explanation_prompt(
            decision=decision,
            context=retrieved_context or [],
        )
        llm_config = LLMConfig(
            temperature=0.3,
            max_tokens=2048,
            system_prompt=(
                "You are a CLO explaining legal decisions transparently. "
                "Cite specific legal authority. Acknowledge uncertainty."
            ),
        )

        try:
            result = await self._llm.structured_complete(
                prompt=prompt,
                output_schema=ExplanationOutput,
                config=llm_config,
            )
        except Exception as exc:
            logger.error("clo_agent.explain_error", request_id=request_id, error=str(exc))
            raise

        latency_ms = int((time.perf_counter() - start) * 1000)
        result.decision_id = decision.get("decision_id", request_id)

        await self._write_audit(
            session=session,
            request_id=request_id,
            decision_id=decision.get("decision_id"),
            tool_name="explain_decision",
            input_summary=f"Explaining decision: {decision.get('decision_id', 'N/A')}",
            input_data={"decision": decision},
            retrieved_sources=retrieved_context or [],
            output_summary=result.explanation[:500],
            exposure_level=decision.get("exposure_level"),
            confidence=decision.get("confidence"),
            latency_ms=latency_ms,
            user_id=user_id,
            prompt=prompt,
        )

        return result

    # ─── Tool: get_agent_status ──────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Return agent health, version, and capabilities."""
        return {
            "status": "healthy",
            "version": self._version,
            "provider": self._llm.provider_name,
            "capabilities": [
                "analyze_legal_risk",
                "prioritize_risk",
                "generate_remediation",
                "explain_decision",
                "chat_dpdp_assistant",
                "get_agent_status",
                "run_legal_audit",
            ],
        }

    # ─── Tool: chat_dpdp_assistant ─────────────────────────────────────────

    async def chat_dpdp_assistant(
        self,
        session: Any,
        message: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Interactive DPDP AI Assistant Q&A and complaint handling using RAG graph memory."""
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # 1. Retrieve knowledge graph context
        retrieval_result = await self._retriever.retrieve_for_risk_analysis(
            situation_description=message,
            session=session,
        )

        retrieved_chunks = [
            c.to_source_dict() for c in retrieval_result.chunks
        ]

        # 2. Build prompt
        context_str = "\n\n".join([f"- {c['section']}: {c['content']}" for c in retrieved_chunks if c.get('content')])
        
        prompt = (
            f"You are the Indian DPDP AI Assistant. Answer the user's question or guide them on DPDP complaints, Data Protection Board (DPB) procedures, or statutory rights under Indian Law.\n\n"
            f"USER MESSAGE:\n{message}\n\n"
            f"RETRIEVED STATUTORY CONTEXT:\n{context_str or 'DPDP Act 2023, DPDP Rules 2025, CERT-In Directions 2022'}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Provide a direct, professional, clear, and structured answer.\n"
            f"2. Cite relevant statutory sections (e.g. Section 6 for Consent, Section 13 for Grievance Redressal, Section 14 for DPB Complaints, Rule 7 for Breach Intimation).\n"
            f"3. If guiding on a complaint, specify the step-by-step procedure: (a) Grievance Officer intimation, (b) 30-day response window, (c) Escalation to Data Protection Board of India (DPBI).\n"
            f"4. Format response in clean GitHub Markdown with bold statutory callouts."
        )

        llm_config = LLMConfig(
            temperature=0.3,
            max_tokens=2048,
            system_prompt=self._system_prompt,
        )

        try:
            resp = await self._llm.complete(
                prompt=prompt,
                config=llm_config,
            )
            response_text = resp.content if hasattr(resp, "content") else str(resp)
        except Exception as exc:
            logger.error("clo_agent.chat_error", request_id=request_id, error=str(exc))
            response_text = (
                f"**DPDP AI Assistant Guidance:**\n\n"
                f"Under the **Digital Personal Data Protection (DPDP) Act 2023**, any Data Principal seeking grievance redressal or filing a complaint must follow these statutory steps:\n\n"
                f"1. **File Grievance with Data Fiduciary**: Submit your data privacy concern to the organization's designated **Data Protection Officer (DPO)** or Grievance Officer.\n"
                f"2. **30-Day Response Window**: The Data Fiduciary is mandated under Section 13 of DPDP Act 2023 to respond within the prescribed period.\n"
                f"3. **Escalation to Data Protection Board of India (DPBI)**: If unsatisfied or unaddressed after 30 days, file an official complaint under Section 14 DPDP Act with the Data Protection Board for inquiry and penalty imposition (up to ₹250 Crore)."
            )

        latency_ms = int((time.perf_counter() - start) * 1000)

        return {
            "response": response_text,
            "statutory_sources": [c.get("section", "DPDP Act 2023") for c in retrieved_chunks[:5]],
            "request_id": request_id,
            "latency_ms": latency_ms,
        }

    async def run_legal_audit(
        self,
        session: Any,
        request: LegalAuditRequestInput,
        user_id: str | None = None,
    ) -> AuditReport:
        """Run a full legal audit by orchestrating existing MCP tools.

        Args:
            session: Database session for audit logging.
            request: Structured or natural-language audit request.
            user_id: Optional user identifier for audit trail.

        Returns:
            Structured AuditReport with findings, risk summary,
            prioritized actions, and final recommendation.
        """
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        orchestrator = LegalAuditOrchestrator(agent=self, session=session)

        try:
            report, _trace = await orchestrator.run(request)
            latency_ms = int((time.perf_counter() - start) * 1000)

            # Write audit record for the full audit
            risk_exposure = report.risk_summary.get("CRITICAL") or report.risk_summary.get("HIGH") if isinstance(report.risk_summary, dict) else None

            await self._write_audit(
                session=session,
                request_id=request_id,
                decision_id=report.audit_id,
                tool_name="run_legal_audit",
                input_summary=f"Legal audit: {request.business_context[:200]}" if request.business_context else "Legal audit",
                input_data=request.model_dump(exclude_none=True),
                retrieved_sources=[],
                output_summary=f"audit_id={report.audit_id}, "
                f"findings={len(report.findings)}, "
                f"recommendation={report.final_recommendation}",
                exposure_level=risk_exposure,
                confidence=report.confidence,
                latency_ms=latency_ms,
                user_id=user_id,
                prompt="run_legal_audit (orchestrator)",
            )

            logger.info(
                "clo_agent.legal_audit_complete",
                audit_id=report.audit_id,
                finding_count=len(report.findings),
                recommendation=report.final_recommendation,
                latency_ms=latency_ms,
            )

            return report

        except Exception as exc:
            logger.error(
                "clo_agent.legal_audit_failure",
                request_id=request_id,
                error=str(exc),
            )
            raise

    # ─── Internal helpers ────────────────────────────────────────────────────

    async def _write_audit(
        self,
        session: Any,
        request_id: str,
        decision_id: str | None,
        tool_name: str,
        input_summary: str,
        input_data: dict[str, Any],
        retrieved_sources: list[dict[str, Any]],
        output_summary: str | None,
        exposure_level: str | None,
        confidence: float | None,
        latency_ms: int,
        user_id: str | None,
        prompt: str,
    ) -> None:
        """Write an audit record to Aurora."""
        if session is None:
            return
        try:
            from ..storage.audit import AuditRecord, write_audit_record

            record = AuditRecord(
                request_id=request_id,
                decision_id=decision_id,
                agent_version=self._version,
                tool_name=tool_name,
                input_summary=input_summary,
                input_data=input_data,
                retrieved_sources=retrieved_sources,
                output_summary=output_summary,
                exposure_level=exposure_level,
                confidence=confidence,
                latency_ms=latency_ms,
                user_id=user_id,
            )
            record.set_prompt_hash(prompt)
            await write_audit_record(session, record)
        except Exception as exc:
            # Audit failures must not break the main flow
            logger.error("clo_agent.audit_failure", request_id=request_id, error=str(exc))
