"""Mock LLM provider for local development and testing."""

from __future__ import annotations

import json
import re
import uuid
from typing import TYPE_CHECKING, Any, TypeVar

import structlog

from .base import LLMConfig, LLMProvider, LLMResponse, LLMUsage

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound="BaseModel | None")


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider.

    Returns structured JSON matching DecisionOutput / RemediationOutput schemas.
    Works without network access or AWS credentials.
    """

    def __init__(self, url: str = "http://localhost:8080/v1/chat/completions") -> None:
        self._url = url
        self._call_count = 0

    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        """Return deterministic mock text based on prompt content."""
        self._call_count += 1

        # Detect intent from prompt keywords
        prompt_lower = prompt.lower()

        if "analyze" in prompt_lower and "risk" in prompt_lower:
            content = (
                "LEGAL_RISK_ANALYSIS_RESULT:"
                " High exposure identified under applicable regulations. "
                "Priority: 8/10. Confidence: 0.82. "
                "Sources: GDPR Art. 5, CCPA § 1798.100."
            )
        elif "prioritize" in prompt_lower:
            content = (
                "RISK_PRIORITIZATION_RESULT:"
                " 1. GDPR non-compliance (P=9, HIGH), "
                "2. CCPA breach notification (P=7, MEDIUM), "
                "3. OSHA reporting delay (P=4, LOW)."
            )
        elif "remediat" in prompt_lower:
            content = (
                "REMEDIATION_STEPS: [Update privacy policy within 30 days], "
                "[Conduct data inventory], [Notify affected individuals], "
                "[Document remediation actions]."
            )
        elif "explain" in prompt_lower:
            content = (
                "DECISION_EXPLANATION: The risk was assessed as HIGH based on "
                "regulatory exposure, material impact, and likelihood factors. "
                "Applicable law: GDPR Art. 33 (72-hour notification requirement)."
            )
        else:
            content = (
                f"MOCK_RESPONSE_{self._call_count}: "
                f"Acknowledged request. Request ID: {uuid.uuid4()}. "
                "This is a deterministic mock response."
            )

        return LLMResponse(
            content=content,
            model="mock/claude-3.5-sonnet",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            finish_reason="end_turn",
        )

    async def structured_complete(
        self,
        prompt: str,
        output_schema: type[T],
        config: LLMConfig | None = None,
    ) -> T:
        """Return a structured mock object matching the Pydantic schema."""
        import inspect

        from pydantic import BaseModel

        self._call_count += 1
        config = config or LLMConfig()
        model: type[BaseModel] = output_schema  # type: ignore[assignment]
        assert model is not None, "output_schema must not be None"

        # Detect intent from prompt keywords
        prompt_lower = prompt.lower()

        if "analyze" in prompt_lower and "risk" in prompt_lower:
            mock_data: dict[str, Any] = {
                "decision_id": str(uuid.uuid4()),
                "priority_rank": 8,
                "exposure_level": "HIGH",
                "legal_rationale": (
                    "Based on retrieved legal context, the situation presents "
                    "material regulatory exposure under applicable data protection law. "
                    "The entity's current practices may not satisfy statutory requirements "
                    "for data minimization and consent."
                ),
                "actionable_steps_array": [
                    "Conduct immediate data inventory and mapping",
                    "Review and update consent mechanisms",
                    "Assess notification obligations under GDPR Art. 33 / CCPA § 1798.150",
                    "Engage external privacy counsel",
                    "Document findings in compliance register",
                ],
                "legal_sources": [
                    {
                        "document_id": "gov-gdpr-2016-679",
                        "chunk_id": "gdpr-chunk-042",
                        "section": "Article 5 — Principles relating to processing of personal data",
                        "excerpt": "Personal data shall be collected for specified, explicit and legitimate purposes...",
                        "jurisdiction": "EU",
                        "effective_date": "2018-05-25",
                    },
                    {
                        "document_id": "gov-ccpa-2018",
                        "chunk_id": "ccpa-chunk-017",
                        "section": "§ 1798.100 — Consumer right to know",
                        "excerpt": "A consumer shall have the right to request that a business disclose...",
                        "jurisdiction": "US-CA",
                        "effective_date": "2020-01-01",
                    },
                ],
                "confidence": 0.82,
            }
        elif "prioritize" in prompt_lower:
            mock_data = {
                "risks": [
                    {
                        "risk_id": str(uuid.uuid4()),
                        "description": "GDPR Article 33 breach notification failure",
                        "exposure_level": "HIGH",
                        "material_exposure": 5000000.0,
                        "urgency_score": 9,
                        "combined_priority_score": 9.2,
                        "legal_basis": "GDPR Art. 33 — 72-hour notification to supervisory authority",
                        "recommendation": "Initiate breach notification protocol immediately",
                    },
                    {
                        "risk_id": str(uuid.uuid4()),
                        "description": "CCPA consumer rights violation",
                        "exposure_level": "MEDIUM",
                        "material_exposure": 750000.0,
                        "urgency_score": 6,
                        "combined_priority_score": 6.5,
                        "legal_basis": "CCPA § 1798.100 — Consumer right to delete",
                        "recommendation": "Implement consumer rights portal within 30 days",
                    },
                    {
                        "risk_id": str(uuid.uuid4()),
                        "description": "OSHA workplace injury reporting delay",
                        "exposure_level": "LOW",
                        "material_exposure": 25000.0,
                        "urgency_score": 4,
                        "combined_priority_score": 4.1,
                        "legal_basis": "OSHA 29 CFR 1904.29 — Recording criteria",
                        "recommendation": "Review reporting procedures and assign compliance owner",
                    },
                ],
            }
        elif "remediat" in prompt_lower:
            mock_data = {
                "remediation_id": str(uuid.uuid4()),
                "risk_id": "mock-risk-001",
                "steps": [
                    {
                        "step_number": 1,
                        "action": "Conduct urgent data inventory",
                        "description": "Map all personal data processing activities, identify data subjects, categories, and flows",
                        "rationale": "Cannot assess compliance without complete data inventory",
                        "timeline_days": 7,
                        "responsible_party": "Data Protection Officer",
                        "estimated_cost_usd": 15000.0,
                        "priority": "IMMEDIATE",
                        "legal_reference": "GDPR Art. 30 — Records of processing activities",
                    },
                    {
                        "step_number": 2,
                        "action": "Update privacy notice",
                        "description": "Revise privacy policy to accurately reflect current data practices",
                        "rationale": "Transparency obligation under GDPR Art. 5(1)(a) and CCPA § 1798.100",
                        "timeline_days": 14,
                        "responsible_party": "Legal Counsel",
                        "estimated_cost_usd": 8000.0,
                        "priority": "HIGH",
                        "legal_reference": "GDPR Art. 13/14 — Information to be provided",
                    },
                    {
                        "step_number": 3,
                        "action": "Establish consent management framework",
                        "description": "Implement granular consent mechanisms with audit trail",
                        "rationale": "Lawful basis for processing requires valid consent or legitimate interest",
                        "timeline_days": 30,
                        "responsible_party": "Engineering + Legal",
                        "estimated_cost_usd": 50000.0,
                        "priority": "HIGH",
                        "legal_reference": "GDPR Art. 7 — Conditions for consent",
                    },
                    {
                        "step_number": 4,
                        "action": "Develop breach response protocol",
                        "description": "Create incident response plan with notification procedures",
                        "rationale": "Statutory notification deadlines require pre-established procedures",
                        "timeline_days": 21,
                        "responsible_party": "Legal + Security",
                        "estimated_cost_usd": 25000.0,
                        "priority": "MEDIUM",
                        "legal_reference": "GDPR Art. 33/34, CCPA § 1798.82",
                    },
                ],
                "estimated_total_cost_usd": 97500.0,
                "estimated_completion_days": 30,
            }
        elif "explain" in prompt_lower:
            mock_data = {
                "decision_id": str(uuid.uuid4()),
                "explanation": (
                    "The legal risk assessment identified HIGH exposure due to three compounding factors: "
                    "(1) the entity's data collection practices exceed the scope of disclosed purposes, "
                    "violating GDPR Article 5(1)(b) data minimization principles; "
                    "(2) California consumers have not been provided opt-out mechanisms compliant with "
                    "CCPA Section 1798.120; and (3) the absence of a documented breach notification "
                    "procedure creates risk of missing the GDPR 72-hour supervisory authority notification "
                    "window under Article 33. The combined regulatory exposure is assessed at $5.75M, "
                    "comprising potential fines and remediation costs."
                ),
                "decision_factors": [
                    {
                        "factor": "Regulatory Exposure",
                        "weight": 0.40,
                        "assessment": "HIGH",
                        "evidence": "GDPR Art. 5(1)(b) non-compliance; CCPA § 1798.100 violation",
                        "source": "gov-gdpr-2016-679, gov-ccpa-2018",
                    },
                    {
                        "factor": "Material Impact",
                        "weight": 0.35,
                        "assessment": "HIGH",
                        "evidence": "Estimated fine exposure $2.5M–$5M under GDPR Art. 83(4)(a)",
                        "source": "gov-gdpr-2016-679",
                    },
                    {
                        "factor": "Likelihood",
                        "weight": 0.25,
                        "assessment": "MEDIUM",
                        "evidence": "Ongoing collection without compliant consent mechanism increases audit risk",
                        "source": "gov-ccpa-2018",
                    },
                ],
                "sources_cited": [
                    {
                        "document_id": "gov-gdpr-2016-679",
                        "chunks": ["gdpr-chunk-042", "gdpr-chunk-108"],
                        "sections": ["Art. 5", "Art. 33"],
                        "relevance_score": 0.95,
                    },
                    {
                        "document_id": "gov-ccpa-2018",
                        "chunks": ["ccpa-chunk-017", "ccpa-chunk-022"],
                        "sections": ["§ 1798.100", "§ 1798.120"],
                        "relevance_score": 0.88,
                    },
                ],
            }
        else:
            # Generic fallback: generate minimal valid instance
            mock_data = self._generate_generic_fallback(model)

        logger.debug("mock.structured_complete", schema=model.__name__, call=self._call_count)
        return model.model_validate(mock_data)

    def _generate_generic_fallback(self, model: type["BaseModel"]) -> dict[str, Any]:
        """Generate minimal valid data for any schema."""
        schema = model.model_json_schema()
        result: dict[str, Any] = {}

        for key, spec in schema.get("properties", {}).items():
            typ = spec.get("type", "string")
            if typ == "string":
                result[key] = f"mock_{key}_{uuid.uuid4().hex[:8]}"
            elif typ == "integer" or typ == "number":
                result[key] = 0
            elif typ == "boolean":
                result[key] = False
            elif typ == "array":
                result[key] = []
            elif typ == "object":
                result[key] = {}
            else:
                result[key] = None

        return result
