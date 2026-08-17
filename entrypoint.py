#!/usr/bin/env python3
"""Entrypoint: wait for dependencies, init schema, ingest docs, start app."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

import httpx

# ── Wait for dependencies ──────────���───────────────────────────────────────────

async def wait_for_pgvector(host: str = "pgvector", port: int = 5432, timeout: int = 60) -> None:
    """Poll pgvector until it's ready to accept connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            import asyncpg
            conn = await asyncpg.connect(
                host=host, port=port,
                user="cloagent", password="cloagent_secret", database="cloagent",
                timeout=3,
            )
            await conn.close()
            print("[entrypoint] pgvector is ready")
            return
        except Exception:
            pass
        await asyncio.sleep(1)
    raise RuntimeError("pgvector did not become ready within timeout")


async def wait_for_mock_llm(url: str = "http://mock-llm:8080/health", timeout: int = 60) -> None:
    """Poll mock LLM server until it responds."""
    deadline = time.time() + timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.time() < deadline:
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    print("[entrypoint] mock-llm is ready")
                    return
            except Exception:
                pass
            await asyncio.sleep(1)
    raise RuntimeError("mock-llm did not become ready within timeout")


# ── Init ───────────────────────────────────────────────────────────────────────

async def init_schema() -> None:
    """Run Aurora schema migration."""
    print("[entrypoint] Initializing database schema...")
    from src.storage.aurora import get_session_factory, init_schema as _init_schema
    from src.config import DatabaseSettings

    settings = DatabaseSettings()
    factory = get_session_factory(settings)
    async with factory() as session:
        await _init_schema(session)
    print("[entrypoint] Schema ready")


async def ingest_documents() -> None:
    """Ingest sample legal documents into the vector store."""
    print("[entrypoint] Ingesting sample legal documents...")
    from src.storage.aurora import get_session_factory
    from src.config import DatabaseSettings
    from src.embedding.mock import MockEmbeddingProvider
    from src.ingestion.pipeline import IngestionPipeline
    from src.ingestion.parser import extract_metadata_from_filename

    factory = get_session_factory(DatabaseSettings())
    embed = MockEmbeddingProvider()
    pipeline = IngestionPipeline(embedding_provider=embed)
    sample_dir = Path("/sample_docs")
    count = 0

    for f in sorted(sample_dir.rglob("*.txt")):
        meta = extract_metadata_from_filename(f.name)
        async with factory() as session:
            try:
                await pipeline.ingest_file(
                    str(f), session,
                    title=meta.get("title", f.stem),
                    jurisdiction=meta.get("jurisdiction"),
                    domain=meta.get("domain"),
                    law_type=meta.get("law_type"),
                )
                count += 1
                print(f"[entrypoint]   ingested: {f.name}")
            except Exception as e:
                print(f"[entrypoint]   skipped: {f.name} — {e}")

    print(f"[entrypoint] Ingestion done: {count} document(s)")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    await wait_for_pgvector()
    await wait_for_mock_llm()
    await init_schema()
    await ingest_documents()

    print("[entrypoint] Starting uvicorn on :8000 with ALB keep-alive optimizations")
    # Replace this process with uvicorn
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app",
         "--host", "0.0.0.0", "--port", "8000",
         "--proxy-headers", "--forwarded-allow-ips", "*",
         "--timeout-keep-alive", "75"],
        stdout=sys.stdout, stderr=sys.stderr,
    )
    proc.wait()


if __name__ == "__main__":
    asyncio.run(main())
