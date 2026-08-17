# Plan: Legal Audit Orchestration — `run_legal_audit`

## Phase 1: Architecture Assessment

### Current State
- **8 MCP tools** defined in `src/mcp/tools.py` (2 undocumented beyond the 6 reported)
- **FastAPI server** in `src/main.py` routes each tool by name
- **CLOAgent** in `src/agent/clo_agent.py` owns all tool implementations
- **LLM abstraction**: `LLMProvider` with `complete()` + `structured_complete()` + `provider_name`
- **Retrieval**: `GovtGraphRAG` (Zep Cloud) wrapped by `ZepRetrieverAdapter` → `LegalRetriever`
- **Audit**: Every tool call writes to Aurora via `_write_audit()`
- **Existing schemas**: `DecisionOutput`, `PrioritizationOutput`, `RemediationOutput`, `ExplanationOutput`
- **No Zep**: Graphiti/Neptune config exists but isn't wired in; Zep Cloud is the active retrieval layer
- **Codemax** LLM via `CodemaxLLMProvider` is the production LLM (not Bedrock)
- **Test pattern**: Mock LLM + mock retriever; `patch("src.storage.audit.write_audit_record")`

### Clean Extension Points Identified
1. **Tool registration**: Add `RUN_LEGAL_AUDIT_TOOL` dict to `src/mcp/tools.py` and include it in `ALL_TOOLS`
2. **Agent method**: Add `run_legal_audit()` method to `CLOAgent` class
3. **FastAPI route**: Add `elif tool_name == "run_legal_audit"` branch in `call_tool()`
4. **New module**: `src/agent/legal_audit.py` — schemas + orchestrator (self-contained)
5. **Capabilities list**: Update `get_status()` to include `run_legal_audit`
6. **Tests**: Extend existing test patterns

### What NOT to touch
- `src/services/zep_graphrag.py` — works fine, no changes needed
- `src/retrieval/vector_store.py` — works fine
- `src/storage/audit.py` — works fine
- `src/config.py` — no new config required
- `src/llm/` — works fine
- `src/embedding/` — works fine
- Existing 6 tool implementations — unchanged
- Existing tests — only extend, don't modify

---

## Phase 2: Implementation

### Step 1 — New module: `src/agent/legal_audit.py`

**Purpose**: All audit-specific schemas + the `LegalAuditOrchestrator` class.

#### Schemas

```python
# Audit Finding (per finding in the report)
class AuditFinding(BaseModel):
    finding_id: str
    domain: str                          # e.g. "data_privacy", "data_localization"
    title: str
    description: str
    business_activity: str              # What the org is doing
    data_involved: list[str]            # e.g. ["Aadhaar", "PAN", "biometric"]
    legal_requirement: str              # What Indian law requires
    legal_basis: str                    # e.g. "Section 16 DPDP Act 2023"
    source: str                        # e.g. "GRAPH_RAG_EVIDENCE", "EXTERNAL_INDIAN_SOURCE"
    evidence: str                      # Retrieved text or "INSUFFICIENT_EVIDENCE"
    compliance_status: str              # COMPLIANT | PARTIALLY_COMPLIANT | NON_COMPLIANT | INSUFFICIENT_EVIDENCE | NOT_APPLICABLE
    risk_level: str                    # LOW | MEDIUM | HIGH | CRITICAL
    reasoning: str                     # Concise decision-relevant reasoning
    remediation: str | None            # "See remediation_plan" or None
    confidence: float                  # 0.0–1.0

# Audit input (supports both structured + natural language)
class LegalAuditRequest(BaseModel):
    # Natural language fallback
    business_context: str = Field(..., min_length=10, max_length=5000)
    # Structured fields (all optional — extracted from business_context if absent)
    objective: str | None = None
    organization_type: str | None = None   # e.g. "fintech", "healthcare", "ecommerce"
    industry: str | None = None           # e.g. "financial_services", "health"
    data_involved: list[str] = Field(default_factory=list)
    systems_involved: list[str] = Field(default_factory=list)
    processing_activities: list[str] = Field(default_factory=list)
    mode: str = Field(default="full_audit")  # full_audit | risk_assessment | quick_review
    jurisdiction: str = Field(default="IN")   # India-only
    user_id: str | None = None

# Audit execution trace (internal, not exposed in response)
class AuditExecutionTrace(BaseModel):
    audit_id: str
    request: LegalAuditRequest
    tools_invoked: list[str]
    tool_results: dict[str, Any]
    retrieved_evidence: list[dict]
    findings: list[AuditFinding]
    execution_time_ms: int
    errors: list[str]
    status: str  # success | partial | failed

# Audit Report (the final output)
class AuditReport(BaseModel):
    audit_id: str
    executive_summary: str
    business_context: str
    identified_data_processing: list[str]       # What data/pipelines were identified
    applicable_indian_requirements: list[str]  # Key statutory requirements
    findings: list[AuditFinding]
    risk_summary: dict[str, int]               # {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 1}
    prioritized_actions: list[str]              # Top 5 actions by priority
    remediation_plan: RemediationOutput | None  # Reuse existing schema
    final_recommendation: str                  # APPROVE | APPROVE_WITH_CONDITIONS | DO_NOT_APPROVE
    confidence: float
    evidence_gaps: list[str]                   # Areas marked INSUFFICIENT_EVIDENCE
    generated_at: str                          # ISO timestamp
```

#### Orchestrator Class: `LegalAuditOrchestrator`

```python
class LegalAuditOrchestrator:
    """Orchestrates existing MCP tools to produce a structured legal audit."""

    def __init__(self, agent: CLOAgent, session: Any):
        self._agent = agent
        self._session = session
        self._trace: AuditExecutionTrace | None = None

    async def run(self, request: LegalAuditRequest) -> tuple[AuditReport, AuditExecutionTrace]:
        """
        Full audit workflow:
        1. Parse/extract context (natural language or structured)
        2. Route: quick_review → chat_dpdp_assistant only
                  risk_assessment → chat + analyze_legal_risk + explain_decision
                  full_audit → chat + analyze + prioritize + remediate + explain
        3. Aggregate findings
        4. Generate remediation (shared across findings)
        5. Produce final recommendation
        6. Return (AuditReport, AuditExecutionTrace)
        """
```

#### Key design decisions
- **Orchestrator is internal** to `CLOAgent.run_legal_audit()` — not a separate service
- **Graceful degradation**: If any tool fails, the audit continues with available data; failed tools are logged in `trace.errors`
- **No tool mocking**: The orchestrator calls the agent's methods directly (they mock their own internals)
- **Reuse existing schemas**: `RemediationOutput` is used directly in the report
- **India-only filtering**: Same filtering logic used in `clo_agent.py` (strip non-Indian legal text)

### Step 2 — Register new MCP tool in `src/mcp/tools.py`

Add `RUN_LEGAL_AUDIT_TOOL` dict to `ALL_TOOLS`. Input schema mirrors `LegalAuditRequest`.

### Step 3 — Add `run_legal_audit()` to `CLOAgent`

```python
async def run_legal_audit(
    self,
    session: Any,
    business_context: str,
    *,
    objective: str | None = None,
    organization_type: str | None = None,
    industry: str | None = None,
    data_involved: list[str] | None = None,
    systems_involved: list[str] | None = None,
    processing_activities: list[str] | None = None,
    mode: str = "full_audit",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Run a full legal audit orchestration."""
```

- Creates `LegalAuditRequest` from inputs
- Instantiates `LegalAuditOrchestrator(self, session)`
- Calls `orchestrator.run()`
- Writes audit record (tool_name = "run_legal_audit")
- Returns `{report: AuditReport.model_dump(), trace: AuditExecutionTrace.model_dump()}` (trace is internal but returned for observability)
- Structured JSON response from the endpoint

### Step 4 — Wire endpoint in `src/main.py`

Add `elif tool_name == "run_legal_audit"` branch in `call_tool()`:
- Parse body into `LegalAuditRequest`
- Call `_agent.run_legal_audit()`
- Return `JSONResponse({"success": True, "tool": "run_legal_audit", "result": ...})`

Add `RunLegalAuditRequest` Pydantic model at the top of the file.

### Step 5 — Update `get_status()` capabilities list

Add `"run_legal_audit"` to the capabilities array returned by `CLOAgent.get_status()`.

### Step 6 — Update `/health` response

The health endpoint already returns `_agent.get_status()`, so it will automatically include the new capability.

---

## Phase 3: Tests

### Unit tests (`tests/unit/test_legal_audit.py`)
1. `test_audit_request_validation` — valid/invalid inputs
2. `test_audit_finding_schema` — all compliance statuses and risk levels
3. `test_audit_report_schema` — complete report structure
4. `test_quick_review_mode_routes_to_chat` — mode=quick_review triggers only chat
5. `test_full_audit_mode_routes_correct_tools` — mode=full_audit chains all tools
6. `test_graceful_degradation_on_tool_failure` — audit continues with partial results
7. `test_india_only_filtering_in_audit` — non-Indian content is filtered
8. `test_insufficient_evidence_marked` — when Graph RAG returns nothing
9. `test_final_recommendation_values` — only APPROVE/APPROVE_WITH_CONDITIONS/DO_NOT_APPROVE

### Integration tests (`tests/integration/test_mcp_endpoints.py`)
1. `test_run_legal_audit_full_audit_flow` — end-to-end with mock retriever/LLM
2. `test_run_legal_audit_natural_language_input` — simple query string
3. `test_run_legal_audit_invalid_mode` — validation error handling
4. `test_run_legal_audit_backward_compatibility` — existing tools still work

### Scenario tests (mocked legal responses, no hardcoded answers)
- A: Cross-border data storage (Singapore AWS server)
- B: Customer data breach notification
- C: Employee monitoring system
- D: Third-party data processor onboarding
- E: Children's personal data processing

---

## Phase 4: Documentation Updates

### Update `README.md`
Add `run_legal_audit` to the features list and MCP tools table.

### Update `ARCHITECTURE.md`
Add the new tool to the architecture diagram and component list.

---

## File Changes Summary

| File | Change |
|------|--------|
| `src/agent/legal_audit.py` | **NEW** — schemas + orchestrator |
| `src/mcp/tools.py` | Add `RUN_LEGAL_AUDIT_TOOL` to `ALL_TOOLS` |
| `src/agent/clo_agent.py` | Add `run_legal_audit()` method + update `get_status()` |
| `src/main.py` | Add request model + `elif` branch in `call_tool()` |
| `tests/unit/test_legal_audit.py` | **NEW** — 9 unit tests |
| `tests/integration/test_mcp_endpoints.py` | Add 4 integration tests |
| `README.md` | Update tool list |
| `ARCHITECTURE.md` | Update diagram |

**Lines of new code**: ~400–500 (orchestrator + schemas + tests + wiring)

---

## Execution Order

1. `src/agent/legal_audit.py` (schemas + orchestrator)
2. `src/mcp/tools.py` (tool registration)
3. `src/agent/clo_agent.py` (agent method + capabilities)
4. `src/main.py` (endpoint wiring)
5. `tests/unit/test_legal_audit.py` (unit tests)
6. `tests/integration/test_mcp_endpoints.py` (integration tests)
7. Run full test suite: `pytest tests/ -v`
8. Verify health: `curl http://localhost:8000/health`
9. Verify tools: `curl http://localhost:8000/mcp/tools | jq '.tools[].name'`
10. Update README + ARCHITECTURE
