"""Risk prioritization engine."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrioritizedRisk(BaseModel):
    """A single risk with prioritization score."""

    risk_id: str
    description: str
    exposure_level: str = Field(pattern="^(HIGH|MEDIUM|LOW|CRITICAL)$")
    material_exposure: float = Field(ge=0, description="Estimated financial exposure in USD")
    urgency_score: int = Field(ge=1, le=10, description="Time sensitivity 1-10")
    combined_priority_score: float = Field(ge=0, le=10)
    legal_basis: str
    recommendation: str


class PrioritizationOutput(BaseModel):
    """Output of risk prioritization."""

    risks: list[PrioritizedRisk]
    total_material_exposure: float = 0.0
    critical_count: int = 0
    high_count: int = 0


SYSTEM_PROMPT_PRIORITIZE = """You are a Chief Legal Officer risk prioritization expert.
Prioritize legal risks based on: (1) material exposure, (2) regulatory urgency, (3) enforcement trends.
Output only a JSON array of PrioritizedRisk objects.
"""


PRIORITIZATION_PROMPT = """Prioritize the following identified legal risks in order of urgency and material impact.

RISKS:
{risks}

TASK:
1. Calculate a combined priority score for each risk using: (urgency_score × 0.6) + (exposure_level_weight × 0.4)
   - CRITICAL = 10, HIGH = 7, MEDIUM = 4, LOW = 1
   - exposure_level_weight = min(material_exposure / 10_000_000, 10) capped
2. Sort by combined priority score descending
3. For each risk, provide a specific immediate recommendation
4. Aggregate total material exposure across all risks

FORMAT: Respond with a JSON object matching PrioritizationOutput schema.
"""


def build_prioritization_prompt(risks: list[dict]) -> str:
    """Build the prompt for risk prioritization."""
    risk_lines = []
    for i, risk in enumerate(risks, 1):
        risk_lines.append(
            f"{i}. Description: {risk.get('description', 'N/A')}\n"
            f"   Exposure Level: {risk.get('exposure_level', 'UNKNOWN')}\n"
            f"   Material Exposure: ${risk.get('material_exposure', 0):,.0f}\n"
            f"   Urgency Score: {risk.get('urgency_score', 5)}/10\n"
            f"   Legal Basis: {risk.get('legal_basis', 'N/A')}\n"
        )
    return PRIORITIZATION_PROMPT.format(risks="\n".join(risk_lines))
