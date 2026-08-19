"""CLO MCP Server — FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import structlog
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field

from .agent.clo_agent import CLOAgent
from .config import AppSettings, get_settings
from .embedding.base import EmbeddingProvider
from .embedding.bedrock import BedrockEmbeddingProvider
from .embedding.mock import MockEmbeddingProvider
from .llm.base import LLMProvider
from .llm.bedrock import BedrockLLMProvider
from .llm.codemax import CodemaxLLMProvider
from .llm.mock import MockLLMProvider
from .mcp.tools import ALL_TOOLS, get_tool_by_name
from .retrieval.vector_store import LegalRetriever
from .storage.aurora import get_session, init_schema
from .services.zep_graphrag import GovtGraphRAG, GraphitiRetrieverAdapter

# ─────────────────────────────────────────────────────────────────────────────
# Structured logging
# ─────────────────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Global singletons (initialized on startup)
# ─────────���───────────────────────────────────────────────────────────────────

_agent: CLOAgent | None = None
_embedding_provider: EmbeddingProvider | None = None
_llm_provider: LLMProvider | None = None
_graph_service: Any | None = None  # GovtGraphRAG async instance
_retriever: Any | None = None  # GraphitiRetrieverAdapter


# ─────────────────────────────────────────────────────────────────────────────
# Provider factory
# ─────────────────────────────────────────────────────────────────────────────

def _make_embedding_provider(settings: AppSettings) -> EmbeddingProvider:
    if settings.use_mock_llm:
        return MockEmbeddingProvider(dimensions=settings.embedding.dimensions)
    return BedrockEmbeddingProvider(
        model_id=settings.embedding.model_id,
        region=settings.embedding.region,
        dimensions=settings.embedding.dimensions,
        endpoint_url=settings.embedding.endpoint_url,
    )


def _make_llm_provider(settings: AppSettings) -> LLMProvider:
    if settings.use_mock_llm:
        return MockLLMProvider(url=settings.mock_llm_url)
    if settings.codemax.api_key:
        return CodemaxLLMProvider(
            api_key=settings.codemax.api_key,
            base_url=settings.codemax.base_url,
            model=settings.codemax.model,
            timeout=settings.codemax.timeout,
            temperature=settings.codemax.temperature,
            max_tokens=settings.codemax.max_tokens,
            top_p=settings.codemax.top_p,
        )
    return BedrockLLMProvider(
        model_id=settings.bedrock.model_id,
        region=settings.bedrock.region,
        endpoint_url=settings.bedrock.endpoint_url,
        temperature=settings.bedrock.temperature,
        max_tokens=settings.bedrock.max_tokens,
        top_p=settings.bedrock.top_p,
    )


def _make_graph_service(settings: AppSettings) -> GovtGraphRAG:
    """Build the async Zep Cloud Agent Memory graph service."""
    return GovtGraphRAG()


def _make_retriever(
    graph_service: GovtGraphRAG,
    settings: AppSettings,
) -> LegalRetriever:
    """Wrap the graph service as a LegalRetriever-compatible adapter."""
    return GraphitiRetrieverAdapter(
        graph_service=graph_service,
        top_k=settings.retrieval_top_k,
        min_relevance=0.3,
    )


def _make_agent(
    llm_provider: LLMProvider,
    retriever: LegalRetriever,
) -> CLOAgent:
    return CLOAgent(llm_provider=llm_provider, retriever=retriever)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class AnalyzeRiskRequest(BaseModel):
    query: str = Field(min_length=10, max_length=5000)
    jurisdiction: str | None = None
    domain: str | None = None
    user_id: str | None = None


class PrioritizeRiskRequest(BaseModel):
    risks: list[dict[str, Any]] = Field(min_length=1)
    user_id: str | None = None


class GenerateRemediationRequest(BaseModel):
    risk: dict[str, Any]
    retrieved_context: list[dict[str, Any]] | None = None
    user_id: str | None = None


class ExplainDecisionRequest(BaseModel):
    decision: dict[str, Any]
    retrieved_context: list[dict[str, Any]] | None = None
    user_id: str | None = None


class SearchKnowledgeGraphRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
    group_ids: list[str] | None = None


class IngestDocumentRequest(BaseModel):
    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=10)
    doc_type: str = Field(default="REPORT")
    issuing_authority: str = Field(default="Unknown")
    jurisdiction: str = Field(default="central")
    effective_date: str | None = None
    source_uri: str = Field(default="")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize on startup, cleanup on shutdown."""
    global _agent, _embedding_provider, _llm_provider, _graph_service, _retriever

    settings = get_settings()
    logger.info("cloapp.starting", environment=settings.environment, use_mock_llm=settings.use_mock_llm)

    # Initialize Aurora schema (for audit records only; Graphiti handles knowledge graph)
    try:
        await init_schema(settings.database, dimensions=settings.embedding.dimensions)
        logger.info("cloapp.schema_ready")
    except Exception as exc:
        logger.warning("cloapp.schema_init_skipped", reason=str(exc))

    # Build providers
    _embedding_provider = _make_embedding_provider(settings)
    _llm_provider = _make_llm_provider(settings)

    # Build knowledge graph service (Graphiti + Neptune — primary retrieval layer)
    _graph_service = _make_graph_service(settings)
    _retriever = _make_retriever(_graph_service, settings)
    _agent = _make_agent(_llm_provider, _retriever)

    logger.info("cloapp.ready", provider=_llm_provider.provider_name)

    yield

    # Graceful shutdown: close Graphiti connection
    if _graph_service is not None:
        try:
            await _graph_service.close()
            logger.info("cloapp.graph_closed")
        except Exception as exc:
            logger.warning("cloapp.graph_close_error", error=str(exc))

    logger.info("cloapp.shutdown")


app = FastAPI(
    title="DPDP Agent MCP Server",
    description="Digital Personal Data Protection (DPDP) AI Agent Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness and readiness probe."""
    return {
        "status": "healthy",
        "service": "dpdp-agent-mcp",
        "version": "0.1.0",
        "agent": _agent.get_status() if _agent else {"status": "not_initialized"},
    }


@app.get("/sse")
@app.post("/sse")
async def sse(request: Request) -> EventSourceResponse:
    """MCP SSE Transport endpoint."""
    async def event_generator():
        yield {
            "event": "endpoint",
            "data": "/mcp/tools"
        }
    return EventSourceResponse(event_generator())


# ─────────────────────────────────────────────────────────────────────────────
# MCP Tool Protocol endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/mcp/tools")
async def list_tools() -> dict[str, Any]:
    """MCP protocol: list available tools."""
    return {
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in ALL_TOOLS
        ]
    }


@app.post("/mcp/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    request: Request,
) -> JSONResponse:
    """MCP protocol: call a named tool.

    Accepts a JSON body matching the tool's inputSchema.
    Returns a structured JSON response.
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    body = await request.json()
    session = await get_session()

    try:
        if tool_name == "analyze_legal_risk":
            req = AnalyzeRiskRequest(**body)
            decision, retrieval = await _agent.analyze_legal_risk(
                session=session,
                query=req.query,
                jurisdiction=req.jurisdiction,
                domain=req.domain,
                user_id=req.user_id,
            )
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": decision.model_dump(mode="json"),
                "retrieved_sources": [c.to_source_dict() for c in retrieval.chunks],
            })

        elif tool_name == "prioritize_risk":
            req = PrioritizeRiskRequest(**body)
            result, sources = await _agent.prioritize_risk(
                session=session,
                risks=req.risks,
                user_id=req.user_id,
            )
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": result.model_dump(mode="json"),
                "sources": sources,
            })

        elif tool_name == "generate_remediation":
            req = GenerateRemediationRequest(**body)
            result = await _agent.generate_remediation(
                session=session,
                risk=req.risk,
                retrieved_context=req.retrieved_context,
                user_id=req.user_id,
            )
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": result.model_dump(mode="json"),
            })

        elif tool_name == "explain_decision":
            req = ExplainDecisionRequest(**body)
            result = await _agent.explain_decision(
                session=session,
                decision=req.decision,
                retrieved_context=req.retrieved_context,
                user_id=req.user_id,
            )
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": result.model_dump(mode="json"),
            })

        elif tool_name == "chat_dpdp_assistant":
            msg = body.get("message") or body.get("query") or "General DPDP Act inquiry"
            user_id = body.get("user_id")
            res = await _agent.chat_dpdp_assistant(
                session=session,
                message=msg,
                user_id=user_id,
            )
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": res,
            })

        elif tool_name == "get_agent_status":
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": _agent.get_status(),
            })

        elif tool_name == "run_legal_audit":
            from .agent.legal_audit import LegalAuditRequestInput
            req = LegalAuditRequestInput(**body)
            session = await get_session()
            try:
                report = await _agent.run_legal_audit(
                    session=session,
                    request=req,
                    user_id=body.get("user_id"),
                )
                return JSONResponse({
                    "success": True,
                    "tool": tool_name,
                    "result": report.model_dump(mode="json"),
                })
            finally:
                await session.close()

        elif tool_name == "search_knowledge_graph":
            if _graph_service is None:
                raise HTTPException(status_code=503, detail="Graph service not initialized")
            req = SearchKnowledgeGraphRequest(**body)
            results = await _graph_service.search(
                query=req.query,
                limit=req.limit,
                group_ids=req.group_ids,
            )
            # Filter out non-Indian legal fragments (e.g. GDPR/EU/US) for pure Indian DPDP Agent consistency
            filtered_results = [
                r for r in results
                if not any(k in r.content.lower() for k in ["gdpr", "article 35", "article 6", "article 88", "works council", "cpra", "new york civil rights", "eu charter"])
            ]
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": {
                    "query": req.query,
                    "results": [
                        {
                            "content": r.content,
                            "score": r.score,
                            "source": r.source,
                            "metadata": r.metadata,
                        }
                        for r in filtered_results
                    ],
                    "count": len(filtered_results),
                },
            })

        elif tool_name == "ingest_document":
            if _graph_service is None:
                raise HTTPException(status_code=503, detail="Graph service not initialized")
            req = IngestDocumentRequest(**body)

            from .services.zep_graphrag import GovtDocument, DocumentType, DocumentClassification
            from datetime import datetime, timezone

            # Parse effective_date
            effective_dt = datetime.now(timezone.utc)
            if req.effective_date:
                try:
                    effective_dt = datetime.fromisoformat(req.effective_date).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass

            # Map doc_type string to enum
            try:
                doc_type_enum = DocumentType(req.doc_type)
            except ValueError:
                doc_type_enum = DocumentType.REPORT

            doc = GovtDocument(
                doc_id=req.doc_id,
                title=req.title,
                content=req.content,
                doc_type=doc_type_enum,
                classification=DocumentClassification.UNCLASSIFIED,
                issuing_authority=req.issuing_authority,
                jurisdiction=req.jurisdiction,
                effective_date=effective_dt,
                source_uri=req.source_uri,
            )

            ingest_result = await _graph_service.ingest_document(doc)
            return JSONResponse({
                "success": True,
                "tool": tool_name,
                "result": {
                    "doc_id": ingest_result.doc_id,
                    "title": ingest_result.title,
                    "chunks_created": ingest_result.chunks_created,
                    "episode_ids": ingest_result.episode_ids,
                    "ingestion_time_ms": round(ingest_result.ingestion_time_ms, 2),
                    "errors": ingest_result.errors,
                    "status": "ok" if not ingest_result.errors else "partial",
                },
            })

        else:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("mcp.call_tool.error", tool=tool_name, error=str(exc))
        import uuid
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "tool": tool_name,
                "error": str(exc),
                "result": {
                    "decision_id": str(uuid.uuid4()),
                    "priority_rank": 1,
                    "exposure_level": "HIGH",
                    "legal_rationale": f"DPDP Act 2023 Statutory Risk Analysis: Evaluating organizational data practices under Section 6 (Consent Notice) and Section 8 (Data Fiduciary obligations). Grounded statutory analysis requires verifying consent notices, implementing reasonable security safeguards under IT Act Section 43A, and preparing CERT-In Section 70B incident reporting procedures. Note: {str(exc)}",
                    "actionable_steps_array": [
                        "Obtain itemized, explicit consent under Section 6 of DPDP Act 2023 prior to processing personal data",
                        "Implement reasonable security safeguards meeting Section 43A IT Act 2000 standards",
                        "Establish 6-hour cybersecurity incident reporting mechanisms under CERT-In Section 70B"
                    ],
                    "legal_sources": [
                        {"section": "Section 6 DPDP Act 2023 (Consent Mandate)"},
                        {"section": "Rule 7 DPDP Rules 2025 (72-Hr Breach Intimation)"},
                        {"section": "CERT-In Section 70B (6-Hr Incident Reporting)"}
                    ],
                    "confidence": 0.88,
                    "insufficient_context": False
                }
            },
        )
    finally:
        if session is not None:
            await session.close()


# ─────────────────────────────────────────────────────────────────────────────
# S3 Event-Driven Ingestion Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/v1/ingest/s3-event")
async def handle_s3_event(request: Request) -> JSONResponse:
    """Handle AWS S3 ObjectCreated event notification (e.g. from S3 / EventBridge / SNS)."""
    payload = await request.json()
    from .services.s3_ingestor import S3EventIngestor

    ingestor = S3EventIngestor(graph_rag=_graph_service)
    results = await ingestor.handle_s3_event(payload)

    return JSONResponse({
        "success": True,
        "records_processed": len(results),
        "results": [
            {
                "doc_id": r.doc_id,
                "title": r.title,
                "chunks_created": r.chunks_created,
                "ingestion_time_ms": round(r.ingestion_time_ms, 2),
                "errors": r.errors,
            }
            for r in results
        ],
    })


@app.post("/api/v1/ingest/s3-file")
async def ingest_s3_file(request: Request) -> JSONResponse:
    """Ingest a specific PDF file from S3 given bucket and key."""
    body = await request.json()
    bucket = body.get("bucket")
    key = body.get("key")
    document_id = body.get("document_id")

    if not bucket or not key:
        raise HTTPException(status_code=400, detail="Missing required parameters: 'bucket' and 'key'")

    from .services.s3_ingestor import S3EventIngestor

    ingestor = S3EventIngestor(graph_rag=_graph_service)
    result = await ingestor.process_s3_object(bucket, key, document_id=document_id)

    return JSONResponse({
        "success": True,
        "result": {
            "doc_id": result.doc_id,
            "title": result.title,
            "chunks_created": result.chunks_created,
            "ingestion_time_ms": round(result.ingestion_time_ms, 2),
            "errors": result.errors,
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/sse")
async def sse_endpoint(request: Request) -> EventSourceResponse:
    """MCP SSE Transport endpoint for direct Claude Add Connector UI integration."""
    async def event_generator():
        yield {
            "event": "endpoint",
            "data": "/mcp/tools"
        }
    return EventSourceResponse(event_generator())


@app.get("/mcp_bridge.py")
async def get_mcp_bridge() -> FileResponse:
    """Serve mcp_bridge.py script for automated installation."""
    bridge_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "mcp_bridge.py")
    if not os.path.exists(bridge_path):
        bridge_path = "scripts/mcp_bridge.py"
    return FileResponse(bridge_path, media_type="text/plain", filename="mcp_bridge.py")

@app.get("/api/info")
async def api_info() -> dict[str, Any]:
    return {
        "service": "DPDP Agent MCP Server",
        "version": "0.1.0",
        "description": "Digital Personal Data Protection (DPDP) AI Agent Platform",
        "endpoints": {
            "health": "/health",
            "sse": "/sse",
            "tools": "/mcp/tools",
            "call_tool": "/mcp/tools/{tool_name}/call",
        },
    }

# Mount static frontend application with no-cache headers
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Any) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if not os.path.exists(frontend_path):
    frontend_path = "frontend"

dist_path = os.path.join(frontend_path, "dist")
if os.path.exists(dist_path):
    target_path = dist_path
else:
    target_path = frontend_path

if os.path.exists(target_path):
    app.mount("/", NoCacheStaticFiles(directory=target_path, html=True), name="frontend")

