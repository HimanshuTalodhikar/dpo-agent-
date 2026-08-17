"""Decision explanation engine."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DecisionFactor(BaseModel):
    """A single factor in a decision."""

    factor: str
    weight: float = Field(ge=0, le=1)
    assessment: str
    evidence: str
    source: str


class SourceCited(BaseModel):
    """A legal source cited in an explanation."""

    document_id: str
    chunks: list[str]
    sections: list[str]
    relevance_score: float = Field(ge=0, le=1)


class ExplanationOutput(BaseModel):
    """Output of decision explanation."""

    decision_id: str
    explanation: str = Field(max_length=3000)
    decision_factors: list[DecisionFactor]
    sources_cited: list[SourceCited]


SYSTEM_PROMPT_EXPLAIN = """You are a Chief Legal Officer explaining legal decisions.
Explain reasoning transparently, citing specific legal authority.
Distinguish facts from legal interpretations. Acknowledge uncertainty.
"""


EXPLANATION_PROMPT = """Explain the following legal decision using the retrieved legal sources and decision factors.

DECISION:
{explanation_request}

RETRIEVED LEGAL SOURCES:
{context}

TASK:
1. Provide a clear, plain-language explanation of the decision
2. Break down the key decision factors and their relative weights
3. Explain how each legal source contributed to the decision
4. Acknowledge any areas of legal uncertainty or interpretive judgment
5. Do not simply restate the conclusion — explain the reasoning chain

FORMAT: Respond with a JSON object matching ExplanationOutput schema.
"""


def build_explanation_prompt(
    decision: dict,
    context: list[dict],
) -> str:
    """Build the prompt for decision explanation."""
    decision_str = (
        f"Decision ID: {decision.get('decision_id', 'N/A')}\n"
        f"Priority Rank: {decision.get('priority_rank', 'N/A')}/10\n"
        f"Exposure Level: {decision.get('exposure_level', 'UNKNOWN')}\n"
        f"Legal Rationale: {decision.get('legal_rationale', 'N/A')}\n"
        f"Confidence: {decision.get('confidence', 'N/A')}\n"
    )

    if context:
        context_lines = []
        for chunk in context:
            context_lines.append(
                f"Source: {chunk['document_id']} — {chunk['section']}\n"
                f"Relevance: {chunk.get('similarity', 'N/A')}\n"
                f"Content: {chunk['excerpt']}\n"
            )
        context_str = "\n---\n".join(context_lines)
    else:
        context_str = "[No legal sources available]"

    return EXPLANATION_PROMPT.format(
        explanation_request=decision_str,
        context=context_str,
    )
