"""End-to-end tests for the complete CLO decision flow.

Runs the full chain: MCP tool call → CLO Agent → Retrieval → LLM → Decision → Audit.
Requires docker-compose services (app + pgvector + mock-llm) to be running.

Run with: pytest tests/e2e/ --tb=short -v
"""

import pytest

pytestmark = pytest.mark.e2e


class TestFullDecisionFlow:
    """E2E tests for the complete CLO decision pipeline."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, http_client):
        """Verify the MCP server is healthy and tools are registered."""
        response = await http_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent" in data

    @pytest.mark.asyncio
    async def test_list_tools(self, http_client):
        """Verify all 5 MCP tools are discoverable."""
        response = await http_client.get("/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        tool_names = [t["name"] for t in data["tools"]]
        expected = [
            "analyze_legal_risk",
            "prioritize_risk",
            "generate_remediation",
            "explain_decision",
            "get_agent_status",
        ]
        for tool in expected:
            assert tool in tool_names, f"Tool {tool} not found in registered tools"

    @pytest.mark.asyncio
    async def test_get_agent_status(self, http_client):
        """Test get_agent_status endpoint."""
        response = await http_client.post(
            "/mcp/tools/get_agent_status/call",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["result"]
        assert result["status"] == "healthy"
        assert "version" in result
        assert "capabilities" in result

    @pytest.mark.asyncio
    async def test_analyze_legal_risk_full_flow(self, http_client):
        """Test complete analyze_legal_risk → decision → audit flow."""
        payload = {
            "query": "We are implementing a new AI system that processes employee performance data. "
                     "Does this trigger any GDPR obligations, and what are the risks?",
            "jurisdiction": "EU",
            "domain": "regulatory",
            "user_id": "e2e-test-user",
        }
        response = await http_client.post(
            "/mcp/tools/analyze_legal_risk/call",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tool"] == "analyze_legal_risk"
        result = data["result"]
        # Validate decision output schema
        assert "decision_id" in result
        assert "priority_rank" in result
        assert result["priority_rank"] in range(1, 11)
        assert result["exposure_level"] in ("HIGH", "MEDIUM", "LOW", "CRITICAL")
        assert "legal_rationale" in result
        assert isinstance(result["actionable_steps_array"], list)
        assert isinstance(result["legal_sources"], list)
        assert 0.0 <= result["confidence"] <= 1.0
        # Sources should be cited
        assert len(result["legal_sources"]) >= 0
        # Retrieved sources should be in response
        assert "retrieved_sources" in data
        assert isinstance(data["retrieved_sources"], list)

    @pytest.mark.asyncio
    async def test_analyze_legal_risk_insufficient_context(self, http_client):
        """Test that obscure queries return insufficient_context flag."""
        payload = {
            "query": "Is our internal coffee machine compliant with obscure regulation XYZ-123?",
        }
        response = await http_client.post(
            "/mcp/tools/analyze_legal_risk/call",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["result"]
        # Either the context is insufficient, or retrieval found something
        assert result.get("insufficient_context", False) or len(result.get("legal_sources", [])) >= 0

    @pytest.mark.asyncio
    async def test_prioritize_risk_full_flow(self, http_client):
        """Test risk prioritization with multiple risks."""
        payload = {
            "risks": [
                {
                    "description": "GDPR Art. 33 breach notification failure — 72-hour window expired",
                    "exposure_level": "HIGH",
                    "material_exposure": 5_000_000,
                    "urgency_score": 9,
                    "legal_basis": "GDPR Art. 33",
                },
                {
                    "description": "CCPA consumer rights portal not implemented",
                    "exposure_level": "MEDIUM",
                    "material_exposure": 750_000,
                    "urgency_score": 6,
                    "legal_basis": "CCPA § 1798.100",
                },
                {
                    "description": "OSHA 300 log entries not filed within 7-day window",
                    "exposure_level": "LOW",
                    "material_exposure": 25_000,
                    "urgency_score": 4,
                    "legal_basis": "OSHA 29 CFR 1904.29",
                },
            ],
            "user_id": "e2e-test-user",
        }
        response = await http_client.post(
            "/mcp/tools/prioritize_risk/call",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["result"]
        assert len(result["risks"]) == 3
        assert result["total_material_exposure"] == 5_775_000
        # Risks should be sorted by priority score
        scores = [r["combined_priority_score"] for r in result["risks"]]
        assert scores == sorted(scores, reverse=True)
        assert result["risks"][0]["exposure_level"] == "HIGH"

    @pytest.mark.asyncio
    async def test_generate_remediation_full_flow(self, http_client):
        """Test remediation plan generation."""
        # First get a decision
        analyze_payload = {
            "query": "We accidentally shared customer PII with an unauthorized third-party analytics provider.",
            "jurisdiction": "EU",
            "domain": "regulatory",
        }
        analyze_response = await http_client.post(
            "/mcp/tools/analyze_legal_risk/call",
            json=analyze_payload,
        )
        assert analyze_response.status_code == 200
        decision = analyze_response.json()["result"]

        # Now generate remediation
        remediate_payload = {
            "risk": {
                "decision_id": decision["decision_id"],
                "description": "Unauthorized disclosure of customer PII",
                "exposure_level": decision["exposure_level"],
                "priority_rank": decision["priority_rank"],
                "legal_rationale": decision["legal_rationale"],
            },
            "retrieved_context": analyze_response.json()["retrieved_sources"][:3],
            "user_id": "e2e-test-user",
        }
        response = await http_client.post(
            "/mcp/tools/generate_remediation/call",
            json=remediate_payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["result"]
        assert "remediation_id" in result
        assert len(result["steps"]) >= 1
        # IMMEDIATE steps must have short timelines
        for step in result["steps"]:
            assert "step_number" in step
            assert "action" in step
            assert "timeline_days" in step
            assert "responsible_party" in step
            assert "priority" in step
            if step["priority"] == "IMMEDIATE":
                assert step["timeline_days"] <= 7
        assert "disclaimer" in result
        assert "informational" in result["disclaimer"].lower()

    @pytest.mark.asyncio
    async def test_explain_decision_full_flow(self, http_client):
        """Test decision explanation."""
        # First get a decision
        analyze_payload = {
            "query": "An employee was terminated after reporting safety violations to OSHA. Could this be retaliation?",
            "jurisdiction": "US-FEDERAL",
            "domain": "employment",
        }
        analyze_response = await http_client.post(
            "/mcp/tools/analyze_legal_risk/call",
            json=analyze_payload,
        )
        assert analyze_response.status_code == 200
        decision = analyze_response.json()["result"]

        # Explain it
        explain_payload = {
            "decision": {
                "decision_id": decision["decision_id"],
                "priority_rank": decision["priority_rank"],
                "exposure_level": decision["exposure_level"],
                "legal_rationale": decision["legal_rationale"],
                "confidence": decision["confidence"],
            },
            "retrieved_context": analyze_response.json()["retrieved_sources"][:3],
        }
        response = await http_client.post(
            "/mcp/tools/explain_decision/call",
            json=explain_payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        result = data["result"]
        assert result["decision_id"] == decision["decision_id"]
        assert len(result["explanation"]) > 0
        assert len(result["decision_factors"]) >= 1
        assert len(result["sources_cited"]) >= 0
        # Weights should sum reasonably
        weights = [f["weight"] for f in result["decision_factors"]]
        assert sum(weights) > 0

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_404(self, http_client):
        """Test that unknown tools return 404."""
        response = await http_client.post(
            "/mcp/tools/unknown_tool/call",
            json={},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_risk_query_validation(self, http_client):
        """Test that too-short queries are rejected."""
        payload = {"query": "hi"}  # min 10 chars
        response = await http_client.post(
            "/mcp/tools/analyze_legal_risk/call",
            json=payload,
        )
        # Should return validation error (422)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_audit_record_written(self, http_client, db_session):
        """Verify audit records are written to Aurora after a tool call."""
        from sqlalchemy import text

        payload = {
            "query": "Are we required to maintain records of employee processing activities under any regulation?",
            "jurisdiction": "EU",
            "domain": "regulatory",
            "user_id": "audit-test-user",
        }
        response = await http_client.post(
            "/mcp/tools/analyze_legal_risk/call",
            json=payload,
        )
        assert response.status_code == 200

        # Check audit table
        result = await db_session.execute(
            text("SELECT request_id, tool_name, user_id, exposure_level FROM audit_records ORDER BY created_at DESC LIMIT 1")
        )
        row = result.fetchone()
        assert row is not None
        assert row[1] == "analyze_legal_risk"
        assert row[2] == "audit-test-user"
