# Document Ingestion Guide

## Overview

Documents are ingested into the Graphiti + Neptune knowledge graph in two ways:

1. **CLI script** (`scripts/ingest_pdfs.py`) — batch ingest PDFs from a directory
2. **MCP tool** (`ingest_document`) — ingest arbitrary text via the MCP API
3. **REST API** (`POST /mcp/tools/ingest_document/call`) — same as MCP tool, via HTTP

Ingestion is **idempotent**: re-ingesting the same `doc_id` updates nodes/edges in Neptune rather than creating duplicates. This is enforced via Graphiti's `group_id` mechanism.

## CLI: Batch PDF Ingestion

```bash
# Ingest all PDFs in the docs/ directory
python scripts/ingest_pdfs.py

# Or specify a custom directory
python scripts/ingest_pdfs.py --docs-dir /path/to/pdfs

# Force re-ingest (ignore checkpoint)
python scripts/ingest_pdfs.py --no-skip
```

### Required Environment Variables for CLI

```bash
export GRAPHITI_NEPTUNE_HOST="neptune-db://cloagent-govt.cluster-cbk4moqeonjo.ap-south-1.neptune.amazonaws.com:8182"
export GRAPHITI_AOSS_HOST="https://8bj12teqwj4xh6vuv5k7.ap-south-1.aoss.amazonaws.com"
export GRAPHITI_ANTHROPIC_API_KEY="sk-..."
export GRAPHITI_OPENAI_API_KEY="sk-..."
```

### Checkpoint System

The CLI maintains a `.ingest_checkpoint.json` in the docs directory. Documents already ingested are skipped unless `--no-skip` is passed. This enables resumable batch ingestion.

### Supported PDF Types

The script uses **pypdf** for text extraction and classifies documents by filename:

| Filename Pattern | Doc Type | Authority |
|---|---|---|
| `*cert*` | REGULATION | CERT-In |
| `*dpdp*` | RULE | Ministry of Electronics & IT |
| `*it_act*` | ACT | Parliament of India |
| `*sdpi*` | REPORT | NIPFP |
| `*rules*` | RULE | Ministry of Electronics & IT |
| Other | REPORT | Unknown |

## API: Ingest via MCP Tool

```bash
curl -X POST http://localhost:8000/mcp/tools/ingest_document/call \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "DPDP-2023-001",
    "title": "Digital Personal Data Protection Act 2023",
    "content": "1. PRELIMINARY\n1.1 This Act provides for protection...",
    "doc_type": "ACT",
    "issuing_authority": "Parliament of India",
    "jurisdiction": "central",
    "effective_date": "2023-08-11"
  }'
```

### Response

```json
{
  "success": true,
  "tool": "ingest_document",
  "result": {
    "doc_id": "DPDP-2023-001",
    "title": "Digital Personal Data Protection Act 2023",
    "chunks_created": 12,
    "episode_ids": ["ep-uuid-1", "ep-uuid-2", "..."],
    "ingestion_time_ms": 45230.5,
    "errors": [],
    "status": "ok"
  }
}
```

## Ingestion Pipeline Detail

```
Input Document
    │
    ▼
_chunk_text(chunk_size=1000, overlap=200)
    │
    ▼ (per chunk)
[Document Header] + [Chunk Text]
    │
    ▼
graphiti.add_episode(
    name = "{doc_id}-chunk-{N}",
    episode_body = "{header}\n{chunk}",
    source_description = "{type}: {title} ({authority}, {date})",
    reference_time = effective_date,
    source = EpisodeType.text,
    group_id = doc_id,          ← idempotency key
)
    │
    ├── LLM (Anthropic) extracts:
    │       - Named entities (organizations, laws, people, concepts)
    │       - Relationships between entities
    │       - Temporal facts
    │
    └── Writes to Neptune:
            - Episode node
            - Entity nodes (deduped with existing)
            - Edge nodes (relationships between entities)
        And to AOSS:
            - node_name_and_summary index
            - episode_content index
            - edge_name_and_fact index
```

## Chunk Size Tuning

| Setting | Default | Notes |
|---|---|---|
| `GRAPHITI_CHUNK_SIZE` | 1000 chars | Smaller = more granular facts, slower ingestion |
| `GRAPHITI_CHUNK_OVERLAP` | 200 chars | Prevents context loss at chunk boundaries |

For legal documents with complex cross-references, `chunk_size=2000` with `chunk_overlap=400` may produce better entity extraction at the cost of speed.

## Ingestion Time

Typical ingestion times (per chunk):
- Simple text extraction: ~2-5 seconds (LLM entity extraction)
- Complex regulatory documents: ~5-15 seconds per chunk

For a 50-page PDF (~20 chunks at default size): ~5-10 minutes total.

## Error Handling

- **Retry**: Each chunk retries up to 3 times with exponential backoff (2s, 4s, 8s)
- **Partial success**: If some chunks fail, `status="partial"` is returned with error details
- **Idempotency**: Failed chunks can be retried by re-running ingestion with the same `doc_id`
