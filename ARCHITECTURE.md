# CLO MCP Platform — Architecture

> Version: 0.1.0 | Phase: 1 | Status: In Progress

---

## System Overview

```
┌─���───────────────────────────────────────────────────────────────────────────┐
│  External Systems (Future Phases)                                          │
│  Slack │ Email │ Google Drive │ Microsoft Teams │ Court Feeds               │
└────────────────────────────┬───────────────────���────────────────────────────┘
                            │ ingest
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP Client (Claude Code, custom apps, integrations)                        │
│  → POST /mcp/tools/{tool}/call  │  → GET /mcp/tools                      │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ HTTPS (TLS 1.3)
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AWS Global                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Application Load Balancer (HTTPS, TLS termination)                    │ │
│  │  ─��� Security Group: 443/80 only                                      │ │
│  └─��────────────────────────────────┬───────────────────────────────────┘ │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │ VPC PrivateLink / ALB
                                     ▼
┌��────────────────────────────────────────────────────────────────────────────┐
│  AWS VPC (10.0.0.0/16) — Private, no public IPs                            ��
│                                                                             │
│  ┌─ Public Subnets (2 AZs) ─────────────────────────────────────────────┐ │
│  │  ┌─────────────┐  ┌���────────────┐                                    │ │
│  │  │ NAT Gateway │  │ NAT Gateway │  (for outbound internet from ECS)   │ │
│  │  └──���──────────┘  └─────────────┘                                    │ │
│  │  ┌─────────────────────────────┐                                      │ │
│  │  │  ALB (Internet-facing)       │  HTTPS :443 → ECS :8000            │ │
│  │  └────────────���────────────────┘                                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─ Private Subnets (2 AZs) ─────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │  ECS Cluster: cloagent-cluster                                    │ │ │
│  │  │  ┌──────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │  ECS Task (Fargate)  ─── 2 replicas ──── CPU: 1024, Mem: 2048 │ │ │
│  │  │  │                                                          │   │ │ │
│  │  │  │  CLO MCP Server (FastAPI)                                │   │ │ │
│  │  │  │    ├── /health                                           │   │ │ │
│  │  │  │    ├── /mcp/tools  (list)                                 │   │ │ │
│  │  │  │    └── /mcp/tools/{name}/call                             │   │ │ │
│  ���  │  │                                                          │   │ │ │
│  │  │  │  CLO Agent                                               │   │ │ │
│  │  │  │    ├── analyze_legal_risk()                              │   │ │ │
│  │  │  │    ├── prioritize_risk()                                 │   │ │ │
│  │  │  │    ├── generate_remediation()                            │   │ │ │
│  │  │  │    ├── explain_decision()                                │   │ │ │
│  │  │  │    └── get_agent_status()                                │   │ │ │
│  │  │  │                                                          │   │ │ │
│  │  │  │  Legal Retrieval (Aurora pgvector)                       │   │ │ │
│  │  │  │                                                          │   │ │ │
│  │  │  └──────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │  Aurora PostgreSQL (Serverless v2)                              │ │ │
│  │  │  Writer + Reader instances                                       │ │ │
│  │  │  Encryption: KMS │ Extension: pgvector (1536 dims)              │ │ │
│  │  │                                                                  │ │ │
│  │  │  Tables:                                                        │ │ │
│  │  │  ├── legal_documents  (metadata,jurisdiction,law_type,version) │ │ │
│  │  │  ├��─ legal_chunks    (content, embedding, section_ref)         │ │ │
│  │  │  └── audit_records   (request_id, decision_id, hashes)         │ │ │
│  │  └─────────────────���───────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ IAM Role: ecs_task_role
                                     │   ├── bedrock:InvokeModel
                                     │   ├── s3:GetObject, PutObject, ListBucket
                                     │   ├── secretsmanager:GetSecretValue
                                     │   └── kms:Decrypt
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AWS Services (Shared)                                                      │
���                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐                   │
│  │ Amazon        │  │ Amazon S3     │  │ AWS Secrets  │                   │
│  │ Bedrock       │  │ cloagent-docs│  │ Manager      │                   │
│  │ ────────────  │  │ ────────────  │  │ ────────────  │                   │
│  │ Claude 3.5    │  │ legal docs   │  │ DB creds    │                   │
│  │ Sonnet        │  │ (KMS-SSE)   │  │ (KMS-enc)  │                   │
│  │               │  │ versioning  │  │              │                   │
│  │ Titan Embed   │  │ lifecycle   │  │              │                   │
│  │ v2 (1024d)    │  │             │  │              │                   │
│  └��──────────────┘  └───────────────┘  └──────────────┘                   │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐                                      │
│  │ AWS KMS        │  │ CloudWatch    │                                      │
│  │ alias/cloagent│  │ Logs: /ecs/  │                                      │
│  │ (encryption)  │  │ cloagent     │                                      │
│  └───────────────┘  └───────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### CLO MCP Server (`src/main.py`)
- FastAPI HTTP server listening on port 8000
- `/mcp/tools` — tool discovery
- `/mcp/tools/{name}/call` — tool invocation
- `/health` — liveness/readiness probe
- Initializes providers on startup (lifespan manager)
- All state lives in Aurora/S3; server is stateless

### CLO Agent (`src/agent/clo_agent.py`)
- Orchestrates the full reasoning pipeline per tool call
- Flow: retrieve → sanitize → prompt → LLM → parse → audit
- Writes every call to `audit_records` table
- Raises on LLM errors; never swallows failures silently

### Legal Retrieval (`src/retrieval/vector_store.py`)
- Embeds query with Titan → cosine similarity search in pgvector
- Filters by jurisdiction, domain, law_type, effective_date
- Returns top-K chunks with similarity scores
- Returns `insufficient_context` flag if no chunks found

### LLM Abstraction (`src/llm/`)
- `LLMProvider` ABC: `complete()` + `structured_complete()`
- `BedrockLLMProvider`: real Bedrock via boto3 (Claude messages API)
- `MockLLMProvider`: deterministic structured JSON (local dev/test)
- Swap provider via `USE_MOCK_LLM` env var

### Embedding Abstraction (`src/embedding/`)
- `EmbeddingProvider` ABC: `embed()` + `embed_batch()`
- `BedrockEmbeddingProvider`: Titan v2 via boto3
- `MockEmbeddingProvider`: deterministic hash-based vectors (local dev/test)

### Storage (`src/storage/`)
- **Aurora**: `legal_documents`, `legal_chunks`, `audit_records` tables
- **S3**: raw document files (PDF/TXT), versioned, KMS-encrypted
- **Audit**: every agent call writes: `request_id`, `decision_id`, `input_hash` (SHA-256), `prompt_hash`, `retrieved_sources` (JSONB), `latency_ms`

---

## Data Flow: `analyze_legal_risk`

```
1. MCP Client �� POST /mcp/tools/analyze_legal_risk/call {query, jurisdiction, domain}
2. FastAPI validates body
3. CLO Agent.analyze_legal_risk()
   a. Generate request_id = uuid4()
   b. LegalRetriever.retrieve_for_risk_analysis()
      → Embed query (Titan)
      → Aurora/pgvector: cosine similarity search
      → Returns list[RetrievedChunk] OR insufficient_context flag
   c. Sanitize retrieved chunks (prompt injection strip)
   d. Build RISK_ANALYSIS_PROMPT with retrieved context
   e. LLMProvider.structured_complete(prompt, DecisionOutput)
      → Bedrock Claude 3.5 Sonnet
      → Returns DecisionOutput (JSON, validated by Pydantic)
   f. AuditRecord.write() → Aurora audit_records table
   g. Return (DecisionOutput, retrieved_chunks)
4. FastAPI → JSON response: {success, result, retrieved_sources}
5. MCP Client receives structured decision with legal sources
```

---

## Security Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ Network Security                                                       │
│ ────────────────                                                       │
│ • Aurora: private subnets only, SG allows only ECS tasks (port 5432) ��
│ • ECS tasks: no public IPs, outbound via NAT Gateway                 │
│ • ALB: HTTPS only (TLS 1.3), optional IP allowlist                   │
│ • No security groups open to 0.0.0.0/0 (except ALB port 443)         │
│                                                                        │
│ Data Security                                                           │
│ ────────────                                                            │
│ • Aurora: KMS-encrypted storage (aws:kms)                             ���
│ • S3: KMS-SSE with bucket key, versioning enabled                     │
│ • Secrets Manager: KMS-encrypted, credentials never in env vars       │
│ • Audit records: JSONB with SHA-256 input/prompt hashes                │
│                                                                        │
│ Application Security                                                    │
│ ────────────────────                                                    │
│ • Prompt injection: all retrieved chunks sanitized before LLM call   │
│ • Retrieved docs are DATA, not instructions                            │
│ • No autonomous execution of consequential actions                     │
│ • Pydantic validation on all API inputs                               │
│ • Structured JSON responses only (no free-text LLM bypass)            │
└─────────���────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- legal_documents
document_id, title, jurisdiction, domain, law_type,
effective_date, source_url, version, s3_key, created_at

-- legal_chunks
document_id (FK), chunk_index, content, section, section_ref,
embedding VECTOR(1024), token_count, created_at

-- audit_records
request_id, decision_id, agent_version, tool_name,
input_hash, prompt_hash, retrieved_sources (JSONB),
output_summary, exposure_level, confidence, latency_ms,
user_id, metadata_ (JSONB), created_at
```

---

## Interface Design Principles

1. **Structured outputs only** — LLM responses validated by Pydantic schemas
2. **No hidden chain-of-thought** — all reasoning is in the response; auditable
3. **Source attribution** — every decision cites `document_id + chunk_id`
4. **Graceful degradation** — insufficient legal context returns a clear flag, not hallucinated law
5. **Fail loudly** — audit failures are logged but do not break the main flow
6. **Provider abstraction** — LLM and embedding backends are swappable via env vars

---

## Future Architecture (Phases 2–4)

```
Slack / Email / Drive / Teams / Court Feeds
              ↓
         Ingestion Layer
              ↓
          CLO MCP  ← Already built
              ↓
      Government Legal KB (Phase 1 ✓)
              ↓
    Company Legal / Contracts (Phase 2)
              ↓
    Autonomous Actions + Approval Workflows (Phase 3)
              ↓
    Multi-Jurisdiction Dashboard (Phase 4)
```
