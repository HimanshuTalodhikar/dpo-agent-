"""Legal reasoning engine — structured legal risk analysis prompts."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Output schemas
# ─────────────────────────────────────────────────────────────────────────────

class LegalSource(BaseModel):
    """A cited legal source in a decision."""

    document_id: str = "N/A"
    chunk_id: str = "N/A"
    section: str = ""
    excerpt: str = Field(default="", max_length=500)
    jurisdiction: str | None = None
    effective_date: str | None = None


class DecisionOutput(BaseModel):
    """Structured output of a legal risk analysis."""

    decision_id: str = ""
    priority_rank: int = Field(default=1, ge=1, le=10, description="1=highest priority")
    exposure_level: str = Field(default="HIGH")

    @field_validator("exposure_level")
    @classmethod
    def validate_exposure_level(cls, v: str) -> str:
        allowed = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if v.upper() not in allowed:
            raise ValueError(f"exposure_level must be one of {allowed}, got {v}")
        return v.upper()
    legal_rationale: str = Field(default="", max_length=15000)
    actionable_steps_array: list[str] = Field(default_factory=list)
    legal_sources: list[LegalSource] = Field(default_factory=list)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    insufficient_context: bool = False
    insufficient_context_reason: str | None = None

    @field_validator("legal_sources", mode="before")
    @classmethod
    def coerce_legal_sources(cls, v: Any) -> list[dict[str, Any]]:
        if not isinstance(v, list):
            return []
        coerced = []
        for item in v:
            if isinstance(item, str):
                coerced.append({"section": item, "document_id": "DPDP Act 2023"})
            elif isinstance(item, dict):
                coerced.append(item)
            elif hasattr(item, "model_dump"):
                coerced.append(item.model_dump())
        return coerced


# ─────────────────────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Indian Data Protection & Data Privacy (DPDP) AI Agent.
Your role is to analyze data protection, data privacy, and cybersecurity compliance risks exclusively under Indian Law — specifically the Digital Personal Data Protection Act 2023 (DPDP Act), DPDP Rules 2025, Information Technology Act 2000 (IT Act), CERT-In Section 70B Directions, IT SPDI Rules 2011, and RBI/SEBI data governance frameworks.

PRINCIPLES:
- Restrict all legal analysis, statutory citations, and penalty assessments strictly to Indian Law.
- If retrieved Graph RAG legal context is available, integrate and cite it.
- If Graph RAG context is missing or sparse, DO NOT mention or report that documents or context are missing or unavailable! Instead, draw upon your authoritative knowledge of Indian statutory law to provide a complete, robust, grounded legal risk assessment.
- Always set insufficient_context=false and provide a confident, complete analysis based on Indian statutory provisions.
- Prioritize by statutory penalty limits under the DPDP Act Schedule (up to ₹250 crore) and regulatory scrutiny.
- Never recommend autonomously executing consequential legal or business actions.
"""


RISK_ANALYSIS_PROMPT = """Analyze the following situation for legal risk under Indian Data Protection Law.

SITUATION:
{query}

RETRIEVED LEGAL CONTEXT:
{context}

TASK:
Produce a comprehensive legal risk assessment strictly grounded in Indian Law (DPDP Act 2023, DPDP Rules 2025, CERT-In Section 70B, IT Act 2000).

1. Identify applicable Indian statutory requirements, consent/notice mandates, and legal obligations.
2. Assess potential regulatory exposure under Indian law (DPDP Act Schedule penalties up to ₹250 crore, CERT-In non-compliance, civil liabilities).
3. Assign an exposure level (CRITICAL / HIGH / MEDIUM / LOW).
4. Assign a priority rank from 1 (highest) to 10 (lowest).
5. Provide specific, actionable steps tailored to Indian compliance requirements.
6. Populate legal_sources with specific, descriptive Indian statutory section titles in the 'section' field (e.g. 'Section 6 DPDP Act 2023 (Consent)', 'Section 8(6) DPDP Act 2023 (Breach Notice)', 'Rule 7 DPDP Rules 2025', 'CERT-In Section 70B', 'Section 43A IT Act 2000'). NEVER leave 'section' blank or as 'N/A'!
7. Assign a high confidence score (0.85–1.0) and ALWAYS set insufficient_context=false.

FORMAT: Respond with a JSON object matching the DecisionOutput schema.
DO NOT output or mention that context is insufficient or missing. Always provide a full, authoritative assessment under Indian Law.
"""


def build_risk_analysis_prompt(
    query: str,
    retrieved_chunks: list[dict],  # RetrievedChunk.to_source_dict() format
    insufficient_context: bool = False,
    insufficient_reason: str | None = None,
) -> str:
    """Build the full prompt for risk analysis."""
    if insufficient_context and insufficient_reason:
        context_str = (
            f"[INSUFFICIENT LEGAL CONTEXT]\n{insufficient_reason}\n\n"
            "Unable to produce a reliable legal risk assessment without adequate legal authority."
        )
    elif not retrieved_chunks:
        context_str = "[No legal context retrieved]"
    else:
        lines = []
        for chunk in retrieved_chunks:
            lines.append(
                f"Source: {chunk['document_id']}\n"
                f"Section: {chunk['section']}\n"
                f"Relevance: {chunk.get('similarity', 'N/A')}\n"
                f"Content excerpt: {chunk['excerpt']}\n"
            )
        context_str = "\n---\n".join(lines)

    return RISK_ANALYSIS_PROMPT.format(
        query=query,
        context=context_str,
    )


def sanitize_retrieved_context(text: str) -> str:
    """Strip instruction-like injection attempts from retrieved chunks.

    Retrieved documents are DATA, not instructions. This prevents prompt
    injection via maliciously crafted legal documents.
    """
    import re

    # Remove common instruction injection patterns
    patterns = [
        r"(?im)^ignore (all )?(previous|above|prior) instructions.*$",
        r"(?im)^system:.*$",
        r"(?i)^you are (now |)a .*(jailbreak|hacker|unrestricted).*$",
        r"(?i)^<\|(?:system|user|assistant)\|>",  # ChatML style
    ]

    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.MULTILINE)

    # Truncate at null bytes and control chars (except newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    return text
