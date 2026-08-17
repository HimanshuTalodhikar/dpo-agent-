"""Audit record persistence — every CLO decision is logged for accountability."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = structlog.get_logger(__name__)


# ───��─────────────────────────────────────────────────────────────────────────
# Record types
# ─────────────────────────────────────────────────────────────────────────────

class AuditRecord:
    """Immutable audit record for a CLO agent call."""

    __slots__ = (
        "request_id", "decision_id", "agent_version", "tool_name",
        "input_summary", "input_hash", "prompt_hash", "retrieved_sources",
        "output_summary", "exposure_level", "confidence",
        "latency_ms", "user_id", "metadata_", "created_at",
    )

    def __init__(
        self,
        *,
        request_id: str | None = None,
        decision_id: str | None = None,
        agent_version: str = "0.1.0",
        tool_name: str,
        input_summary: str,
        input_data: dict[str, Any],
        retrieved_sources: list[dict[str, Any]] | None = None,
        output_summary: str | None = None,
        exposure_level: str | None = None,
        confidence: float | None = None,
        latency_ms: int | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.request_id = request_id or str(uuid.uuid4())
        self.decision_id = decision_id
        self.agent_version = agent_version
        self.tool_name = tool_name
        self.input_summary = input_summary
        self.input_hash = hashlib.sha256(
            json.dumps(input_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        self.prompt_hash: str | None = None
        self.retrieved_sources = retrieved_sources or []
        self.output_summary = output_summary
        self.exposure_level = exposure_level
        self.confidence = confidence
        self.latency_ms = latency_ms
        self.user_id = user_id
        self.metadata_ = metadata or {}
        self.created_at = datetime.now(timezone.utc)

    def set_prompt_hash(self, prompt: str) -> None:
        """Record the SHA-256 of the prompt sent to the LLM."""
        self.prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary suitable for JSON / DB insert."""
        return {
            "request_id": self.request_id,
            "decision_id": self.decision_id,
            "agent_version": self.agent_version,
            "tool_name": self.tool_name,
            "input_hash": self.input_hash,
            "prompt_hash": self.prompt_hash,
            "retrieved_sources": json.dumps(self.retrieved_sources, default=str),
            "output_summary": self.output_summary,
            "exposure_level": self.exposure_level,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "user_id": self.user_id,
            "metadata_": json.dumps(self.metadata_, default=str),
            "created_at": self.created_at,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Persistence
# ─────────────────────────────────────────────────────────────────────────────

async def write_audit_record(
    session: "AsyncSession",
    record: AuditRecord,
) -> str:
    """Write an audit record to the database."""
    from sqlalchemy import text

    stmt = text("""
        INSERT INTO audit_records
            (request_id, decision_id, agent_version, tool_name,
             input_hash, prompt_hash, retrieved_sources, output_summary,
             exposure_level, confidence, latency_ms, user_id, metadata_)
        VALUES
            (:request_id, :decision_id, :agent_version, :tool_name,
             :input_hash, :prompt_hash, :retrieved_sources, :output_summary,
             :exposure_level, :confidence, :latency_ms, :user_id, :metadata_)
    """)
    await session.execute(stmt, record.to_dict())
    await session.commit()
    logger.info("audit.record_written", request_id=record.request_id, tool=record.tool_name)
    return record.request_id


async def get_audit_record(
    session: "AsyncSession",
    request_id: str,
) -> AuditRecord | None:
    """Retrieve an audit record by request ID."""
    from sqlalchemy import text

    stmt = text("""
        SELECT request_id, decision_id, agent_version, tool_name,
               input_hash, prompt_hash, retrieved_sources, output_summary,
               exposure_level, confidence, latency_ms, user_id, metadata_, created_at
        FROM audit_records
        WHERE request_id = :request_id
    """)
    row = await session.execute(stmt, {"request_id": request_id})
    result = row.fetchone()
    if result is None:
        return None

    return AuditRecord(
        request_id=result[0],
        decision_id=result[1],
        agent_version=result[2],
        tool_name=result[3],
        input_summary="",  # not stored, only hash
        input_data={},    # not stored, only hash
        prompt_hash=result[5],
        retrieved_sources=json.loads(result[6]) if result[6] else [],
        output_summary=result[7],
        exposure_level=result[8],
        confidence=result[9],
        latency_ms=result[10],
        user_id=result[11],
        metadata=json.loads(result[12]) if result[12] else {},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper: timed execution with audit
# ─────��───────────────────────────────────────────────────────────────────────

class AuditTimer:
    """Context manager for timing agent operations."""

    def __init__(self) -> None:
        self.latency_ms: int = 0
        self._start: float = 0.0

    def __enter__(self) -> "AuditTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.latency_ms = int((time.perf_counter() - self._start) * 1000)
