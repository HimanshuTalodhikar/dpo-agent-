# Zep Cloud Agent Memory Architecture

## Overview

CLO Agent uses **Zep Cloud Agent Memory** (`zep-cloud 3.28.0`) as its primary knowledge graph and contextual memory layer for document ingestion, temporal graph creation, and legal context retrieval.

Zep Cloud provides a fully managed temporal context graph platform that automatically extracts entities, facts, and relationships from ingested regulatory documents, making them available for context-aware RAG queries.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLO Agent MCP Server (FastAPI :8000)                              │
│                                                                     │
│  CLOAgent.analyze_legal_risk()                                      │
│         │                                                           │
│         v                                                           │
│  ZepRetrieverAdapter.retrieve(RetrievalQuery)                       │
│         │                                                           │
│         v                                                           │
│  GovtGraphRAG.search(query, limit)                                  │
│         │                                                           │
└─────────┼───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Zep Cloud Agent Memory API (zep-cloud SDK)                        │
│                                                                     │
│  - Graph ID: govt-knowledge-base                                    │
│  - API Key: z_1dWlkIjoi...                                          │
│                                                                     │
│  ┌───────────────────────────┐     ┌─────────────────────────────┐  │
│  │ azep.graph.add(...)       │     │ azep.graph.search(...)      │  │
│  │ (Document Ingestion)      │     │ (Contextual Retrieval)      │  │
│  └─────────────┬─────────────┘     └──────────────┬──────────────┘  │
└────────────────┼──────────────────────────────────┼─────────────────┘
                 │                                  │
                 ▼                                  ▼
      Temporal Context Graph              Hybrid Graph Search
      (Nodes, Edges, Episodes)           (Facts, Edges, Episodes)
```

## Data Flow: Document Ingestion

```
PDF / Text Document
        │
        ▼
  _chunk_text() ──► list of ~1000-char chunks
        │
        ▼ (for each chunk)
  azep.graph.add(
    graph_id="govt-knowledge-base",
    type="text",
    data="[Document Header]\n[Chunk Content]",
    source_description="ACT: Title (Authority, Date)",
    metadata={ doc_id, chunk_index, title, doc_type, issuing_authority }
  )
        │
        ▼
  Zep Cloud automatically extracts:
    - Entity nodes (laws, authorities, penalties, requirements)
    - Fact triples / edges (relationships and obligations)
    - Temporal context (dates, versions, amendments)
```

## Data Flow: Query & Retrieval

```
Natural Language Query (e.g., "What are the penalties for data breaches under DPDP?")
        │
        ▼
  azep.graph.search(
    graph_id="govt-knowledge-base",
    query=query,
    limit=10
  )
        │
        ▼
  Zep Cloud returns GraphSearchResults:
    - edges: Fact triples (e.g. "Data breach penalty is up to 250 crore rupees")
    - nodes: Entity nodes & summaries
    - episodes: Relevant document chunks
        │
        ▼
  ZepRetrieverAdapter converts to RetrievedChunk format
        │
        ▼
  CLO Agent receives rich legal context for risk analysis
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `ZEP_API_KEY` | Zep Cloud API key | `z_1dWlkIjoi...` |
| `ZEP_GRAPH_ID` | Zep Cloud Graph identifier | `govt-knowledge-base` |
| `ZEP_CHUNK_SIZE` | Ingestion chunk size (characters) | `1000` |
| `ZEP_CHUNK_OVERLAP` | Ingestion overlap (characters) | `200` |

## Advantages over Graphiti Self-Hosted

1. **Fully Managed Cloud Infrastructure**: No complex local Neptune or OpenSearch Serverless provisioning required.
2. **Superior Performance**: Fast indexing and query response times.
3. **Automated Fact Extraction**: Advanced entity and relationship extraction powered by Zep Cloud.
4. **Seamless SDK Integration**: Clean, idiomatic Python SDK using `zep-cloud`.
