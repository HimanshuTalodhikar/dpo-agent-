#!/usr/bin/env bash
# start.sh — Waits for dependencies, initializes schema, ingests docs, then starts app

set -e

echo "=== CLO MCP Server Startup ==="

# ── Wait for dependencies ──────────────────────────────────────────────────

echo "Waiting for pgvector..."
until pg_isready -h pgvector -p 5432 -U cloagent > /dev/null 2>&1; do
  echo "  pgvector not ready, retrying..."
  sleep 2
done
echo "  pgvector ready."

echo "Waiting for mock-llm..."
until curl -sf http://mock-llm:8080/health > /dev/null 2>&1; do
  echo "  mock-llm not ready, retrying..."
  sleep 2
done
echo "  mock-llm ready."

# ── Initialize database schema ──────────────────────────────────────────────
echo "Initializing database schema..."
python -c "
import asyncio
from src.storage.aurora import init_schema, get_session_factory
from src.config import DatabaseSettings

async def _main():
    settings = DatabaseSettings()
    factory = get_session_factory(settings)
    async with factory() as session:
        await init_schema(session)
    print('  Schema ready.')

asyncio.run(_main())
"

# ── Ingest sample documents ─────────────────────────────────────────────────
echo "Ingesting sample legal documents..."
python -c "
import asyncio
from pathlib import Path
from src.config import DatabaseSettings
from src.storage.aurora import get_session_factory
from src.embedding.mock import MockEmbeddingProvider
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.parser import extract_metadata_from_filename

async def _main():
    settings = DatabaseSettings()
    factory = get_session_factory(settings)
    embed = MockEmbeddingProvider()
    pipeline = IngestionPipeline(embedding_provider=embed)
    sample_dir = Path('/sample_docs')
    count = 0
    for f in sorted(sample_dir.rglob('*.txt')):
        meta = extract_metadata_from_filename(f.name)
        async with factory() as session:
            try:
                await pipeline.ingest_file(
                    str(f),
                    session,
                    title=meta.get('title', f.stem),
                    jurisdiction=meta.get('jurisdiction'),
                    domain=meta.get('domain'),
                    law_type=meta.get('law_type'),
                )
                count += 1
                print(f'  Ingested: {f.name}')
            except Exception as e:
                print(f'  Skipped {f.name}: {e}')
    print(f'  {count} document(s) ingested.')

asyncio.run(_main())
"

echo "=== Starting CLO MCP Server ==="
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
