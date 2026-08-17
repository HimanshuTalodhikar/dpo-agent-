"""Local mock LLM server — simulates Bedrock for development without AWS credentials.

Run standalone:
    python mock_llm_server.py

Or via Docker:
    CMD ["python", "mock_llm_server.py"]

Listens on port 8080, accepts OpenAI-compatible /v1/chat/completions requests.
"""

from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs


class MockLLMHandler(BaseHTTPRequestHandler):
    """Handles mock LLM requests for all 5 CLO agent tools."""

    # ── Tool detection ──────────────────────────────────────────────────────────

    def _detect_tool(self, prompt: str) -> str:
        """Detect which CLO tool is being called from the prompt content."""
        prompt_lower = prompt.lower()
        if "analyze" in prompt_lower and "risk" in prompt_lower:
            return "analyze_legal_risk"
        if "prioritize" in prompt_lower:
            return "prioritize_risk"
        if "remediat" in prompt_lower:
            return "generate_remediation"
        if "explain" in prompt_lower and "decision" in prompt_lower:
            return "explain_decision"
        return "generic"

    # ── Response generators ───────────────────────────────────────────────────

    def _analyze_legal_risk_response(self, prompt: str) -> dict:
        # Extract jurisdiction/domain hints from prompt for realism
        jurisdiction = None
        if "eu" in prompt.lower():
            jurisdiction = "EU"
        elif "california" in prompt.lower() or "ccpa" in prompt.lower():
            jurisdiction = "US-CA"

        doc_id = "gov-gdpr-2016-679" if jurisdiction == "EU" else "gov-ccpa-2018"

        return {
            "id": f"clo-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "mock/claude-3.5-sonnet",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "decision_id": str(uuid.uuid4()),
                            "priority_rank": 8,
                            "exposure_level": "HIGH",
                            "legal_rationale": (
                                "Under GDPR Article 33, a data controller must notify the "
                                "supervisory authority of a personal data breach within 72 hours "
                                "of becoming aware of it, unless the breach is unlikely to result "
                                "in a risk to the rights and freedoms of natural persons. "
                                "Failure to notify constitutes a violation subject to fines "
                                "up to €10 million or 2% of annual worldwide turnover."
                            ),
                            "actionable_steps_array": [
                                "Document the breach details, timeline, and scope immediately",
                                "Notify your supervisory authority (DPA) within 72 hours",
                                "Identify affected data subjects and categories of personal data",
                                "Assess whether the breach poses a risk to individuals' rights",
                                "If high risk, notify affected individuals without undue delay",
                                "Update your incident response plan and breach register",
                                "Review and strengthen technical and organizational security measures",
                            ],
                            "legal_sources": [
                                {
                                    "document_id": "gov-gdpr-2016-679",
                                    "chunk_id": "gdpr-chunk-art33",
                                    "section": "GDPR Article 33 — Notification of a personal data breach to the supervisory authority",
                                    "excerpt": "the controller shall notify the supervisory authority of the breach without undue delay and, where feasible, not later than 72 hours after having become aware of it",
                                    "jurisdiction": "EU",
                                    "effective_date": "2018-05-25",
                                },
                                {
                                    "document_id": "gov-gdpr-2016-679",
                                    "chunk_id": "gdpr-chunk-art33a",
                                    "section": "GDPR Article 34 — Communication of a personal data breach to the data subject",
                                    "excerpt": "When the personal data breach is likely to result in a high risk..., the controller shall communicate the personal data breach to the data subject without undue delay",
                                    "jurisdiction": "EU",
                                    "effective_date": "2018-05-25",
                                },
                            ],
                            "confidence": 0.92,
                            "insufficient_context": False,
                            "insufficient_context_reason": None,
                        }),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 200, "completion_tokens": 300, "total_tokens": 500},
        }

    def _prioritize_risk_response(self, prompt: str) -> dict:
        return {
            "id": f"clo-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "mock/claude-3.5-sonnet",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "risks": [
                                {
                                    "risk_id": str(uuid.uuid4()),
                                    "description": "GDPR Article 33 — Unreported data breach within 72-hour window",
                                    "exposure_level": "CRITICAL",
                                    "material_exposure": 15000000.0,
                                    "urgency_score": 10,
                                    "combined_priority_score": 9.8,
                                    "legal_basis": "GDPR Art. 33 — mandatory 72-hour supervisory authority notification",
                                    "recommendation": "IMMEDIATE: File notification with DPA today. Document breach details and timeline.",
                                },
                                {
                                    "risk_id": str(uuid.uuid4()),
                                    "description": "CCPA § 1798.100 — Consumer right to know about data collected",
                                    "exposure_level": "HIGH",
                                    "material_exposure": 5000000.0,
                                    "urgency_score": 6,
                                    "combined_priority_score": 7.4,
                                    "legal_basis": "CCPA § 1798.100 — consumer right to know; 45-day response window",
                                    "recommendation": "HIGH: Fulfill data subject access requests within 45 days. Audit data collection practices.",
                                },
                                {
                                    "risk_id": str(uuid.uuid4()),
                                    "description": "HIPAA § 164.400 — Breach notification to HHS (500+ individuals)",
                                    "exposure_level": "HIGH",
                                    "material_exposure": 3000000.0,
                                    "urgency_score": 8,
                                    "combined_priority_score": 8.2,
                                    "legal_basis": "HIPAA Breach Notification Rule § 164.400",
                                    "recommendation": "IMMEDIATE: Report to HHS immediately. Media notification if >500 in a state.",
                                },
                            ],
                            "total_material_exposure": 23000000.0,
                            "critical_count": 1,
                            "high_count": 2,
                        }),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 150, "completion_tokens": 250, "total_tokens": 400},
        }

    def _generate_remediation_response(self, prompt: str) -> dict:
        return {
            "id": f"clo-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "mock/claude-3.5-sonnet",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "remediation_id": str(uuid.uuid4()),
                            "risk_id": "gdpr-art33-breach-notif",
                            "steps": [
                                {
                                    "step_number": 1,
                                    "action": "Document and Contain",
                                    "description": "Immediately document all known details of the breach and take steps to contain further unauthorized access.",
                                    "rationale": "GDPR Art. 33 requires awareness of the breach; containment reduces harm and demonstrates due diligence.",
                                    "timeline_days": 1,
                                    "responsible_party": "CISO / Legal",
                                    "estimated_cost_usd": 5000.0,
                                    "priority": "IMMEDIATE",
                                    "legal_reference": "GDPR Art. 33",
                                },
                                {
                                    "step_number": 2,
                                    "action": "Notify Supervisory Authority (DPA)",
                                    "description": "Submit breach notification to the competent supervisory authority within 72 hours of awareness.",
                                    "rationale": "GDPR Art. 33(1): notification is mandatory within 72 hours unless the breach is unlikely to result in risk to individuals.",
                                    "timeline_days": 3,
                                    "responsible_party": "CLO / DPO",
                                    "estimated_cost_usd": 2000.0,
                                    "priority": "IMMEDIATE",
                                    "legal_reference": "GDPR Art. 33(1)",
                                },
                                {
                                    "step_number": 3,
                                    "action": "Assess Individual Risk Level",
                                    "description": "Evaluate whether the breach is likely to result in a high risk to the rights and freedoms of individuals.",
                                    "rationale": "GDPR Art. 34 threshold: high-risk breaches require direct communication to affected individuals.",
                                    "timeline_days": 5,
                                    "responsible_party": "DPO / Legal Counsel",
                                    "estimated_cost_usd": 10000.0,
                                    "priority": "HIGH",
                                    "legal_reference": "GDPR Art. 34(1)",
                                },
                                {
                                    "step_number": 4,
                                    "action": "Notify Affected Individuals (if high risk)",
                                    "description": "If the assessment finds high risk to individuals, communicate the breach to all affected data subjects.",
                                    "rationale": "GDPR Art. 34: high-risk breaches require communication to data subjects without undue delay.",
                                    "timeline_days": 14,
                                    "responsible_party": "Legal / Communications",
                                    "estimated_cost_usd": 50000.0,
                                    "priority": "HIGH",
                                    "legal_reference": "GDPR Art. 34",
                                },
                                {
                                    "step_number": 5,
                                    "action": "Update Records and Conduct Root Cause Analysis",
                                    "description": "Update the Record of Processing Activities (ROPA) and conduct a root cause analysis to prevent recurrence.",
                                    "rationale": "GDPR Art. 30: maintain records of processing. Art. 32: implement measures to ensure security.",
                                    "timeline_days": 30,
                                    "responsible_party": "DPO / Engineering",
                                    "estimated_cost_usd": 25000.0,
                                    "priority": "MEDIUM",
                                    "legal_reference": "GDPR Art. 30, Art. 32",
                                },
                            ],
                            "estimated_total_cost_usd": 92000.0,
                            "estimated_completion_days": 30,
                            "disclaimer": (
                                "These recommendations are for informational purposes only and do not "
                                "constitute legal advice. Consult qualified legal counsel before taking action."
                            ),
                        }),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 180, "completion_tokens": 350, "total_tokens": 530},
        }

    def _explain_decision_response(self, prompt: str) -> dict:
        return {
            "id": f"clo-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "mock/claude-3.5-sonnet",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "decision_id": str(uuid.uuid4()),
                            "explanation": (
                                "The CLO Agent assessed this situation as HIGH exposure based on three "
                                "converging factors: (1) GDPR Article 33 imposes a strict 72-hour "
                                "notification obligation to the supervisory authority once the controller "
                                "becomes aware of a personal data breach; (2) failure to notify is a "
                                "violation that can result in fines up to €10 million or 2% of global "
                                "annual turnover; (3) the breach scope (10,000 EU customers) crosses "
                                "the Article 34 threshold, triggering additional obligations to notify "
                                "individuals if the risk is assessed as high. The priority rank of 8 "
                                "reflects that this is a time-critical, high-consequence legal matter "
                                "requiring immediate internal escalation."
                            ),
                            "decision_factors": [
                                {
                                    "factor": "Mandatory notification timeline",
                                    "weight": 0.35,
                                    "assessment": "72-hour window is strictly enforced by DPAs",
                                    "evidence": "GDPR Art. 33(1) requires notification without undue delay, within 72 hours",
                                    "source": "GDPR Article 33",
                                },
                                {
                                    "factor": "Financial exposure magnitude",
                                    "weight": 0.30,
                                    "assessment": "Up to €10M or 2% global turnover",
                                    "evidence": "GDPR Art. 83(4)(a): up to €10M or 2% for infringement of basic processing principles",
                                    "source": "GDPR Article 83",
                                },
                                {
                                    "factor": "Number of affected individuals",
                                    "weight": 0.20,
                                    "assessment": "10,000 EU individuals — crosses Article 34 threshold",
                                    "evidence": "GDPR Art. 34: high risk to rights/freedoms triggers individual notification",
                                    "source": "GDPR Article 34",
                                },
                                {
                                    "factor": "Regulatory enforcement trends",
                                    "weight": 0.15,
                                    "assessment": "GDPR fines have increased 40% YoY; DPA enforcement is intensifying",
                                    "evidence": "DPA enforcement statistics 2023-2024",
                                    "source": "EDPB Annual Report",
                                },
                            ],
                            "sources_cited": [
                                {
                                    "document_id": "gov-gdpr-2016-679",
                                    "chunks": ["gdpr-chunk-art33", "gdpr-chunk-art33a", "gdpr-chunk-art34"],
                                    "sections": ["Article 33", "Article 34", "Article 83"],
                                    "relevance_score": 0.97,
                                },
                            ],
                        }),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 160, "completion_tokens": 280, "total_tokens": 440},
        }

    def _generic_response(self, prompt: str) -> dict:
        tool = self._detect_tool(prompt)
        if tool == "analyze_legal_risk":
            return self._analyze_legal_risk_response(prompt)
        if tool == "prioritize_risk":
            return self._prioritize_risk_response(prompt)
        if tool == "generate_remediation":
            return self._generate_remediation_response(prompt)
        if tool == "explain_decision":
            return self._explain_decision_response(prompt)
        return {
            "id": f"clo-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "mock/claude-3.5-sonnet",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "decision_id": str(uuid.uuid4()),
                            "priority_rank": 5,
                            "exposure_level": "MEDIUM",
                            "legal_rationale": "Unable to determine specific legal exposure from the provided context. Please provide more details.",
                            "actionable_steps_array": ["Consult legal counsel", "Gather more facts"],
                            "legal_sources": [],
                            "confidence": 0.3,
                            "insufficient_context": True,
                            "insufficient_context_reason": "Prompt content did not match any known legal domain patterns.",
                        }),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
        }

    # ── HTTP handlers ─────────────────────────────────────────────────────────

    def _send_json(self, status: int, data: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "healthy", "model": "mock/claude-3.5-sonnet"})
        elif self.path == "/v1/models":
            self._send_json(200, {
                "object": "list",
                "data": [{"id": "mock/claude-3.5-sonnet", "object": "model"}],
            })
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        import threading
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        if self.path == "/v1/chat/completions":
            try:
                request = json.loads(body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return

            messages = request.get("messages", [])
            prompt = " ".join(
                m.get("content", "") for m in messages if isinstance(m.get("content"), str)
            )

            response = self._generic_response(prompt)
            self._send_json(200, response)

        elif self.path == "/v1/embeddings":
            # Return mock embedding vectors
            try:
                request = json.loads(body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return

            import numpy as np
            input_texts = request.get("input", [])
            if isinstance(input_texts, str):
                input_texts = [input_texts]

            data = []
            for text in input_texts:
                seed = hash(text) % (2**32)
                rng = np.random.Generator(np.random.PCG64(seed))
                vector = rng.normal(size=1024).astype(np.float32)
                vector = vector / np.linalg.norm(vector)
                data.append({
                    "object": "embedding",
                    "embedding": vector.tolist(),
                    "index": len(data),
                })

            self._send_json(200, {
                "object": "list",
                "data": data,
                "model": "mock/titan-embed",
                "usage": {"prompt_tokens": 10, "total_tokens": 10},
            })
        else:
            self._send_json(404, {"error": "Not found"})

    def log_message(self, format: str, *args) -> None:
        pass  # Silent unless debugging


if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("0.0.0.0", port), MockLLMHandler)
    print(f"[mock-llm] Mock LLM server running on http://0.0.0.0:{port}")
    print(f"[mock-llm] Endpoints: GET /health, POST /v1/chat/completions, POST /v1/embeddings")
    server.serve_forever()
