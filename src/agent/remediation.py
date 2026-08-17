"""Remediation recommendation engine."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RemediationStep(BaseModel):
    """A single remediation step."""

    step_number: int = Field(default=1)
    action: str = Field(default="")
    action_description: str | None = None
    description: str = Field(default="")
    rationale: str = Field(default="")
    timeline_days: int = Field(default=1)
    responsible_party: str = Field(default="Legal Counsel")
    estimated_cost_usd: float = Field(default=0.0)
    priority: str = Field(default="HIGH")
    legal_reference: str | None = None
    requires_executive_approval: bool | None = None


class RemediationOutput(BaseModel):
    """Output of remediation generation."""

    remediation_id: str
    risk_id: str
    steps: list[RemediationStep]
    estimated_total_cost_usd: float
    estimated_completion_days: int
    disclaimer: str = (
        "These recommendations are for informational purposes only and do not "
        "constitute legal advice. Consult qualified legal counsel before taking action."
    )


SYSTEM_PROMPT_REMEDIATE = """You are a Chief Legal Officer remediation specialist.
Generate actionable, proportionate, and cost-effective remediation plans.
IMPORTANT: Do not recommend autonomously executing consequential legal or business actions.
All remediation plans must include a legal counsel review step.
"""


REMEDIATION_PROMPT = """Generate a remediation plan for the following legal risk.

RISK:
{risk}

RETRIEVED LEGAL SOURCES:
{context}

TASK:
1. Generate 3-8 specific, actionable remediation steps
2. Each step must include:
   - Action description
   - Rationale tied to specific legal requirements
   - Estimated timeline (in days)
   - Responsible party
   - Estimated cost
   - Priority (IMMEDIATE / HIGH / MEDIUM / LOW)
   - Legal reference (statute or regulation)
3. Calculate total estimated cost and completion timeline
4. Include a legal disclaimer
5. Flag any steps that require board/executive approval or external counsel

IMPORTANT CONSTRAINTS:
- Do NOT recommend autonomously executing any action that could bind the company,
  create legal obligations, fire employees, terminate contracts, or make regulatory filings.
- All consequential steps should be labeled "Requires Legal/Executive Approval"
- Priority=IMMEDIATE only for legally mandated deadlines (e.g., 72-hour breach notification)

FORMAT: Respond with a JSON object matching RemediationOutput schema.
"""


def build_remediation_prompt(risk: dict, context: list[dict]) -> str:
    """Build the prompt for remediation generation."""
    risk_str = (
        f"Description: {risk.get('description', 'N/A')}\n"
        f"Exposure Level: {risk.get('exposure_level', 'UNKNOWN')}\n"
        f"Material Exposure: ${risk.get('material_exposure', 0):,.0f}\n"
        f"Legal Basis: {risk.get('legal_basis', 'N/A')}\n"
        f"Priority Rank: {risk.get('priority_rank', 'N/A')}/10"
    )

    if context:
        context_lines = []
        for chunk in context:
            context_lines.append(
                f"Source: {chunk['document_id']} — {chunk['section']}\n"
                f"Excerpt: {chunk['excerpt']}\n"
            )
        context_str = "\n---\n".join(context_lines)
    else:
        context_str = "[No specific legal sources available]"

    return REMEDIATION_PROMPT.format(risk=risk_str, context=context_str)
