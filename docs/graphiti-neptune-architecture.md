# Graphiti + Amazon Neptune Architecture

## Overview

CLO Agent uses **Graphiti** (`graphiti-core 0.29.3`) as its knowledge graph engine, backed by **Amazon Neptune** for graph persistence and **Amazon OpenSearch Serverless (AOSS)** for full-text search.

This dual-storage architecture is **mandatory** for the Neptune backend:

| Storage | What it stores | Why |
|---|---|---|
| Amazon Neptune | Nodes, edges, episodes (graph topology) | Temporal knowledge graph with openCypher queries |
| Amazon OpenSearch Serverless (AOSS) | Text indices (name, summary, fact, content) | Full-text + semantic search against graph content |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLO Agent MCP Server (FastAPI :8000)                              │
│                                                                     │
│  CLOAgent.analyze_legal_risk()                                      │
│         │                                                           │
│         v                                                           │
│  GraphitiRetrieverAdapter.retrieve(RetrievalQuery)                  │
│         │                                                           │
│         v                                                           │
│  GovtGraphRAG.search(query, limit, group_ids)                       │
│         │                                                           │
└─────────┼───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│  Graphiti v0.29.3                   │
│  ┌──────────────────────────────┐   │
│  │  NeptuneDriver               │   │
│  │  host: neptune-db://...      │   │
│  │  aoss_host: ...aoss.aws.com  │   │
│  └──────────┬───────────────────┘   │
│             │                       │
│  ┌──────────┴──────────┐            │
│  │ LLM: AnthropicClient│            │
│  │ model: claude-*     │            │
│  │ base_url: codemax   │            │
│  └─────────────────────┘            │
│                                     │
│  ┌─────────────────────┐            │
│  │ Embedder:           │            │
│  │ OpenAIEmbedder      │            │
│  │ model: text-emb-3sm │            │
│  └─────────────────────┘            │
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
Amazon          Amazon OpenSearch
Neptune         Serverless (AOSS)
(graph DB)      (text search)
cluster:        collection:
cloagent-govt   cloagent-govt
```

## Data Flow: Document Ingestion

```
PDF / Text Document
        │
        ▼
  _chunk_text() ──► list of ~1000-char chunks
        │
        ▼ (for each chunk)
  graphiti.add_episode(
    name="doc-id-chunk-N",
    episode_body="[Document header]\n[Chunk content]",
    source_description="ACT: Title (Authority, Date)",
    reference_time=effective_date,
    source=EpisodeType.text,
    group_id=doc_id,           ← idempotency partition
  )
        │
        ├── Neptune ──► stores episode node, extracted entity nodes,
        │               relationship edges
        │
        └── AOSS ──────► indexes 4 index types:
                          node_name_and_summary
                          community_name
                          episode_content
                          edge_name_and_fact
```

## Data Flow: Query/Retrieval

```
Natural Language Query
        │
        ▼
  graphiti.search(
    query="what are data protection penalties",
    group_ids=["DPDP-2023-001"],   ← optional doc scope
    num_results=10,
  )
        │
        ├── AOSS BM25 search (text-based)
        │
        └── Neptune Cypher traversal (graph-based)
        │
        ▼
  list[EdgeResult | NodeResult | EpisodeResult]
        │
        ▼
  GraphitiRetrieverAdapter normalizes → RetrievalResult
        │
        ▼
  CLOAgent builds prompt with retrieved context
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GRAPHITI_NEPTUNE_HOST` | ✅ | `neptune-db://endpoint:8182` |
| `GRAPHITI_AOSS_HOST` | ✅ | `https://collection-id.region.aoss.amazonaws.com` |
| `GRAPHITI_AOSS_PORT` | No (443) | AOSS port |
| `GRAPHITI_AWS_REGION` | No (ap-south-1) | AWS region |
| `GRAPHITI_GRAPH_NAME` | No (govt-knowledge-base) | Logical graph name |
| `GRAPHITI_ANTHROPIC_API_KEY` | ✅ | Anthropic API key |
| `GRAPHITI_ANTHROPIC_BASE_URL` | No | Custom proxy base URL |
| `GRAPHITI_ANTHROPIC_MODEL` | No (claude-sonnet-5) | Anthropic model |
| `GRAPHITI_OPENAI_API_KEY` | ✅ | OpenAI API key (for text-embedding-3-small) |

> **Note**: `GRAPHITI_OPENAI_API_KEY` is required by the Graphiti Neptune backend.
> The OpenAI API is used ONLY for text embeddings, not for LLM inference.
> You can use any OpenAI key with embedding model access.

## Key Design Decisions

### 1. group_id = doc_id (Idempotency)
Every episode for a document uses `doc_id` as `group_id`. This means:
- All facts from the same document are co-partitioned in the graph
- Re-ingesting the same document updates rather than duplicates nodes/edges
- Retrieval can be scoped to specific documents via `group_ids` parameter

### 2. Document Header in Each Chunk
Each episode body starts with a structured header:
```
Document: <title>
Type: ACT | Classification: UNCLASSIFIED
Authority: Parliament of India
Effective: 2023-08-11
Jurisdiction: central
----
<chunk content>
```
This ensures Graphiti has full document context for entity extraction even from middle chunks.

### 3. AOSS Host Normalization
The `.env` file can store the AOSS host either with or without `https://`. The `_normalize_aoss_host()` helper strips any scheme prefix before passing to `NeptuneDriver`, which expects a bare hostname.

### 4. Graphiti LLM Client
Graphiti uses `AnthropicClient(config=AnthropicConfig(...))` — not the application's own `CodemaxLLMProvider`. This is separate and independent. The Codemax proxy is used as the `base_url` for Anthropic.

### 5. GraphitiRetrieverAdapter
This adapter implements `LegalRetriever` (the same interface the old Aurora/pgvector store implemented), so `CLOAgent` requires zero changes when switching from vector search to graph RAG.
