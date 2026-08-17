"""MCP tool definitions for the CLO Agent."""

from __future__ import annotations

from typing import Any

from pydantic import Field

# ─────────────────��───────────────────────────────────────────────────────────
# Tool schemas (MCP-compatible)
# ─────────────────────────────────────────────────────────────────────────────

ANALYZE_LEGAL_RISK_TOOL = {
    "name": "analyze_legal_risk",
    "description": (
        "Analyze a business situation or scenario for legal risks, regulatory exposure, "
        "and compliance obligations. Retrieves relevant government legal authority "
        "and produces a structured risk assessment with priority ranking, "
        "exposure level, and actionable steps grounded in specific legal sources. "
        "If insufficient legal context is available, the response will indicate this clearly."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A description of the situation, event, or business activity to analyze for legal risk (required)",
                "minLength": 10,
                "maxLength": 5000,
            },
            "jurisdiction": {
                "type": "string",
                "description": "Filter legal research to a specific jurisdiction (e.g., 'EU', 'US-CA', 'US-FEDERAL')",
                "examples": ["EU", "US-CA", "US-FEDERAL", "UK"],
            },
            "domain": {
                "type": "string",
                "description": "Filter legal research to a specific domain (e.g., 'regulatory', 'employment', 'contracts')",
                "examples": ["regulatory", "employment", "contracts"],
            },
            "user_id": {
                "type": "string",
                "description": "Optional identifier of the requesting user for audit purposes",
            },
        },
        "required": ["query"],
    },
}

PRIORITIZE_RISK_TOOL = {
    "name": "prioritize_risk",
    "description": (
        "Prioritize multiple legal risks by material exposure (financial impact × likelihood) "
        "and regulatory urgency. Returns a ranked list with combined priority scores, "
        "legal basis for each risk, and immediate action recommendations."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "risks": {
                "type": "array",
                "description": "List of risks to prioritize",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk_id": {"type": "string"},
                        "description": {"type": "string"},
                        "exposure_level": {
                            "type": "string",
                            "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                        },
                        "material_exposure": {
                            "type": "number",
                            "description": "Estimated financial exposure in USD",
                        },
                        "urgency_score": {
                            "type": "integer",
                            "description": "Time sensitivity 1-10",
                            "minimum": 1,
                            "maximum": 10,
                        },
                        "legal_basis": {"type": "string"},
                    },
                    "required": ["description", "exposure_level", "material_exposure", "urgency_score", "legal_basis"],
                },
            },
            "user_id": {"type": "string"},
        },
        "required": ["risks"],
    },
}

GENERATE_REMEDIATION_TOOL = {
    "name": "generate_remediation",
    "description": (
        "Generate a structured remediation plan for a specific legal risk. "
        "Provides actionable steps with timelines, responsible parties, estimated costs, "
        "and legal references. Does NOT autonomously execute consequential actions — "
        "all steps require human approval before execution."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "risk": {
                "type": "object",
                "description": "The risk to remediate (from a prior analyze_legal_risk call)",
                "properties": {
                    "decision_id": {"type": "string"},
                    "description": {"type": "string"},
                    "exposure_level": {"type": "string"},
                    "priority_rank": {"type": "integer"},
                    "legal_basis": {"type": "string"},
                    "material_exposure": {"type": "number"},
                    "legal_rationale": {"type": "string"},
                },
                "required": ["description", "exposure_level"],
            },
            "retrieved_context": {
                "type": "array",
                "description": "Optional: pre-retrieved legal context chunks (from analyze_legal_risk sources)",
                "items": {
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string"},
                        "chunk_id": {"type": "string"},
                        "section": {"type": "string"},
                        "excerpt": {"type": "string"},
                    },
                },
            },
            "user_id": {"type": "string"},
        },
        "required": ["risk"],
    },
}

EXPLAIN_DECISION_TOOL = {
    "name": "explain_decision",
    "description": (
        "Explain a prior CLO decision using the retrieved legal sources and decision factors. "
        "Provides transparent, plain-language reasoning with citations to specific statutes, "
        "regulations, and legal authority."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "object",
                "description": "A prior CLO decision (from analyze_legal_risk)",
                "properties": {
                    "decision_id": {"type": "string"},
                    "priority_rank": {"type": "integer"},
                    "exposure_level": {"type": "string"},
                    "legal_rationale": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["decision_id"],
            },
            "retrieved_context": {
                "type": "array",
                "description": "Legal source chunks from the original analysis",
            },
            "user_id": {"type": "string"},
        },
        "required": ["decision"],
    },
}

GET_AGENT_STATUS_TOOL = {
    "name": "get_agent_status",
    "description": (
        "Return the CLO Agent's health status, version, and available capabilities. "
        "Use this to verify the agent is operational before submitting requests."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
}

SEARCH_KNOWLEDGE_GRAPH_TOOL = {
    "name": "search_knowledge_graph",
    "description": (
        "Search the government knowledge graph (Graphiti + Amazon Neptune) for entities, "
        "facts, relationships, and episodes relevant to a query. Returns structured results "
        "with content, relevance score, and provenance metadata. "
        "Use this to directly query what is stored in the knowledge graph, "
        "independently of the full CLO legal risk analysis flow."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query to search the knowledge graph",
                "minLength": 3,
                "maxLength": 2000,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10)",
                "minimum": 1,
                "maximum": 50,
                "default": 10,
            },
            "group_ids": {
                "type": "array",
                "description": "Optional list of document IDs to restrict search scope",
                "items": {"type": "string"},
            },
        },
        "required": ["query"],
    },
}

INGEST_DOCUMENT_TOOL = {
    "name": "ingest_document",
    "description": (
        "Ingest a text document into the government knowledge graph (Graphiti + Amazon Neptune). "
        "Extracts entities, relationships, and facts automatically using the configured LLM. "
        "Idempotent: re-ingesting the same document_id updates rather than duplicates. "
        "Use this to add new compliance documents, regulations, or policies to the knowledge base."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "doc_id": {
                "type": "string",
                "description": "Unique identifier for the document (used for idempotency)",
            },
            "title": {
                "type": "string",
                "description": "Document title",
            },
            "content": {
                "type": "string",
                "description": "Full text content of the document",
                "minLength": 10,
            },
            "doc_type": {
                "type": "string",
                "description": "Document classification type",
                "enum": ["ACT", "RULE", "NOTIFICATION", "ORDER", "GUIDELINE", "REPORT", "CIRCULAR", "REGULATION"],
                "default": "REPORT",
            },
            "issuing_authority": {
                "type": "string",
                "description": "Authority that issued the document",
                "default": "Unknown",
            },
            "jurisdiction": {
                "type": "string",
                "description": "Jurisdiction (e.g. 'central', 'EU', 'US-CA')",
                "default": "central",
            },
            "effective_date": {
                "type": "string",
                "description": "ISO 8601 date when the document became effective (e.g. '2024-01-15')",
            },
            "source_uri": {
                "type": "string",
                "description": "Source URI (e.g. s3://bucket/path/file.pdf)",
            },
        },
        "required": ["doc_id", "title", "content"],
    },
}

CHAT_DPDP_ASSISTANT_TOOL = {
    "name": "chat_dpdp_assistant",
    "description": (
        "Interactive AI Chat Assistant for Indian DPDP Act queries, DPB (Data Protection Board) complaint procedures, "
        "Data Principal rights, data breach intimation guidelines, and general privacy compliance Q&A under Indian Law. "
        "Leverages Zep Cloud / Graphiti statutory knowledge graph automatically when required."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "User question, complaint scenario, or general DPDP Act query (required)",
                "minLength": 2,
                "maxLength": 4000,
            },
            "user_id": {
                "type": "string",
                "description": "Optional identifier for audit logging",
            },
        },
        "required": ["message"],
    },
}

ALL_TOOLS = [
    ANALYZE_LEGAL_RISK_TOOL,
    PRIORITIZE_RISK_TOOL,
    GENERATE_REMEDIATION_TOOL,
    EXPLAIN_DECISION_TOOL,
    GET_AGENT_STATUS_TOOL,
    SEARCH_KNOWLEDGE_GRAPH_TOOL,
    INGEST_DOCUMENT_TOOL,
    CHAT_DPDP_ASSISTANT_TOOL,
]


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Find a tool definition by name."""
    for tool in ALL_TOOLS:
        if tool["name"] == name:
            return tool
    return None
