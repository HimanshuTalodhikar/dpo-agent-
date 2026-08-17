# CLO MCP — Phase 1 Implementation Plan

## Context

The repository is empty (greenfield). Phase 1 builds a production-ready CLO MCP Server where a CLO Agent runs inside the MCP service, backed by a government/legal knowledge base on AWS. The goal is a deployable skeleton with working end-to-end flow, not a full legal system.

---

## Architecture

```
MCP Client
    │
    ▼ (HTTP/WebSocket over ALB)
┌──────────���──────────┐
│  ECS/Fargate        │
│  ┌───────────────┐  │
│  │  CLO MCP      │  │
│  │    Server     │  │
│  │  ─────��───── │  │
│  │  CLO Agent   │  │
│  │  ─────────── │  │
│  │  Retrieval   │  │
│  │  ─────────── │  │
│  │  LLM Bridge  │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
Bedrock        Aurora pgvector
(Claude 3.5)   ┌────────���─────┐
               │ legal_docs    │
               │ chunk_embeddings │
               │ audit_records │
               └──────┬────────┘
                      ▼
                     S3 (source PDFs)
```

**Stateless app**: Aurora/S3 hold all persistent state. ECS/Fargate workers have no local disk state.

---

## File Structure

```
cloagent/
├���─ src/                          # Python source
│   ├── __init__.py
│   ├── main.py                   # MCP server entrypoint
│   ├── agent/                    # CLO Agent
│   │   ├── __init__.py
│   │   ├── clo_agent.py         # Main agent orchestrator
│   │   ├── legal_reasoning.py  # Risk analysis, prioritization
│   │   ├── remediation.py       # Recommendation engine
│   │   └── decision_explainer.py
│   ├── retrieval/               # Retrieval layer
│   │   ├── __init__.py
│   │   ├── vector_store.py      # Aurora/pgvector queries
│   │   └── reranker.py          # Optional semantic reranking
│   ├── llm/                      # LLM abstraction
│   │   ├── __init__.py
│   │   ├── base.py              # LLMProvider abstract class
│   │   ├���─ bedrock.py           # Amazon Bedrock implementation
│   │   └── mock.py              # Mock for local dev/tests
│   ├── embedding/                # Embedding abstraction
│   │   ├── __init__.py
│   │   ├── base.py              # EmbeddingProvider abstract class
│   │   ├── bedrock.py          # Bedrock Titan implementation
│   │   └── mock.py              # Mock for local dev/tests
│   ├── storage/                  # Data layer
│   │   ├─��� __init__.py
│   │   ├── s3_client.py         # S3 document operations
│   │   ├── aurora.py            # Aurora/pgvector operations
│   │   └── audit.py             # Audit record persistence
│   ├── ingestion/               # Document pipeline
│   │   ├── __init__.py
│   │   ├── parser.py            # PDF/TXT/HTML parsing
│   │   ├── chunker.py           # Semantic chunking
│   │   └��─ pipeline.py          # Full ingest: parse→chunk→embed→store
│   ├── mcp/                     # MCP protocol layer
│   │   ├── __init__.py
│   │   └── tools.py             # MCP tool definitions
│   └── config.py                # Environment/config loading
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_agent.py
│   │   ├── test_retrieval.py
��   │   ├── test_ingestion.py
│   │   └── test_llm_bridge.py
│   ├── integration/
│   │   ├── test_mcp_endpoints.py
│   │   └── test_retrieval_pipeline.py
│   └── e2e/
│       └── test_full_decision_flow.py
├── infra/                       # Terraform
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── ecs.tf
│   ├── aurora.tf
│   ├── s3.tf
│   ├── iam.tf
│   ├── networking.tf
│   ├── secrets.tf
│   └── ecr.tf
├── sample_docs/                 # Government legal sample docs
│   ├── regulatory/
│   │   ├── gdpr_summary.txt
│   │   ├── ccpa_summary.txt
│   │   └── hipaa_summary.txt
│   ├── employment/
│   │   ├── title_vii_summary.txt
│   │   └── osha_summary.txt
│   └── contracts/
│       └── ucc_article2_summary.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml           # Local dev (app + pgvector + mock LLM)
├── pytest.ini
├── uv.lock / pyproject.toml
├── README.md
├── ARCHITECTURE.md
└── IMPLEMENTATION_PLAN.md
```

---

## 5 MCP Tools to Implement

| Tool | Description | Returns |
|------|-------------|---------|
| `analyze_legal_risk` | Analyze a situation for legal risks using retrieved legal context | `DecisionOutput` (structured JSON) |
| `prioritize_risk` | Prioritize multiple risks by material exposure and urgency | `PrioritizedRisk[]` |
| `generate_remediation` | Generate actionable remediation steps for a given risk | `RemediationOutput` |
| `explain_decision` | Explain a prior decision using legal sources and factors | `ExplanationOutput` |
| `get_agent_status` | Return agent health, version, and capabilities | `AgentStatus` |

---

## Step-by-Step Implementation

### Step 1 — Project Scaffolding
- Create `pyproject.toml` with uv, Python 3.12
- Create `.env.example` (AWS region, Bedrock model, Aurora host, S3 bucket, Secrets Manager ARN, KMS key ARN)
- Create `Dockerfile` (Python 3.12 slim, uv install, healthcheck)
- Create `docker-compose.yml` (app + `pgvector` container + mock Bedrock on port 8080)
- Create `pytest.ini`

### Step 2 — Config & Secrets
- `src/config.py`: load from env vars, validate required fields
- Interface wrappers over `os.environ` / `pydantic-settings`

### Step 3 — LLM & Embedding Abstractions
- `src/llm/base.py`: abstract `LLMProvider` with `complete()` and `structured_complete()` methods
- `src/llm/bedrock.py`: real Bedrock call via `boto3` (Claude 3.5 Sonnet)
- `src/llm/mock.py`: in-memory mock that returns deterministic structured JSON — no network needed
- Same pattern for `src/embedding/base.py`, `bedrock.py`, `mock.py`

### Step 4 — Storage Layer
- `src/storage/aurora.py`: SQLAlchemy async + `asyncpg`, CRUD for `legal_chunks`, `audit_records`
- `src/storage/s3_client.py`: `boto3` S3 operations for raw document upload/download
- `src/storage/audit.py`: structured audit record writes

### Step 5 — Retrieval Layer
- `src/retrieval/vector_store.py`: pgvector similarity search (cosine distance), metadata filtering by jurisdiction/section/date
- Chunk → embed → store pipeline

### Step 6 — Document Ingestion Pipeline
- `src/ingestion/parser.py`: PDF text extraction (`pypdf` or `pdfplumber`), plain text pass-through
- `src/ingestion/chunker.py`: fixed-size + sentence-boundary chunker with overlap, outputs chunk metadata
- `src/ingestion/pipeline.py`: orchestrates parse → chunk → embed → store → S3 upload

### Step 7 — CLO Agent
- `src/agent/legal_reasoning.py`: prompt template for risk analysis, structured output parsing
- `src/agent/remediation.py`: prompt template for actionable recommendations
- `src/agent/decision_explainer.py`: generate human-readable explanations
- `src/agent/clo_agent.py`: orchestrates retrieval → reasoning → audit write

### Step 8 — MCP Server
- `src/mcp/tools.py`: five tool definitions using `mcp` Python SDK
- `src/main.py`: FastMCP or official MCP server bootstrap, register tools, start server

### Step 9 — Auditability
- Every agent call writes an `audit_record` to Aurora with:
  - `request_id`, `decision_id`, `timestamp`, `input_summary`, `retrieved_sources`, `llm_prompt_hash`, `output_summary`, `latency_ms`
- `prompt-injection protection`: sanitize retrieved chunks before passing to LLM (strip instruction-like patterns)
- Source attribution: every decision factor must cite a `source_document_id` + `chunk_id`

### Step 10 — Terraform Infrastructure
- `infra/main.tf`: provider config, backend (S3+DynamoDB for state)
- `infra/networking.tf`: VPC, private subnets, NAT Gateway
- `infra/aurora.tf`: Aurora Serverless v2 PostgreSQL + pgvector, in private subnets
- `infra/s3.tf`: S3 bucket for documents (versioning enabled), KMS SSE
- `infra/iam.tf`: ECS task role (least privilege: Bedrock, S3, Aurora, Secrets Manager, KMS)
- `infra/ecs.tf`: ECS cluster, task definition, service, ALB
- `infra/secrets.tf`: Secrets Manager for DB credentials, Bedrock API key
- `infra/ecr.tf`: ECR repository
- `infra/variables.tf` + `outputs.tf`

### Step 11 — Sample Government Documents
- Create 6 sample text files covering: GDPR, CCPA, HIPAA, Title VII, OSHA, UCC Article 2
- Include realistic metadata: jurisdiction, effective date, section references
- Ingest them as part of the local dev setup

### Step 12 — Tests
- **Unit tests**: each module independently testable with mock LLM/embedding
- **Integration tests**: MCP tool calls, Aurora queries, retrieval pipeline
- **E2E test**: MCP call → CLO Agent → retrieval → Bedrock → decision → audit record

### Step 13 — Documentation
- `README.md`: setup, run, test, deploy
- `ARCHITECTURE.md`: system diagram, data flow, component responsibilities
- `IMPLEMENTATION_PLAN.md`: this file (kept for reference)

---

## Risk Reduction: Mock-First Development

The `mock` providers in Steps 3–4 let the entire app run locally without AWS credentials. Tests and the E2E flow run fully offline. Real Bedrock/Aurora is wired in via config flags (`USE_MOCK_LLM=true`).

---

## Assumptions

1. AWS account with permissions to create Aurora, ECS, S3, IAM, Secrets Manager, KMS
2. Bedrock access to Claude 3.5 Sonnet in the target region
3. `pgvector` extension available in Aurora PostgreSQL 15+
4. Port 8080 available locally for mock LLM server
5. No existing infrastructure — everything is net-new

---

## Open Questions for User

- Should the E2E test run against real Bedrock or stay mock-only?
- Do you want a REST fallback API in addition to MCP?
- Should I seed Aurora with the sample documents on `docker-compose up`, or require a manual ingest step?
- Preferred region for AWS resources (us-east-1, eu-west-1, etc.)?

---

## Definition of Done Verification

| # | Criterion | Where Verified |
|---|-----------|----------------|
| 1 | CLO MCP server starts | `docker-compose up`, MCP client connects |
| 2 | All 5 tools discoverable | MCP client `listTools` returns 5 |
| 3 | CLO Agent runs inside MCP | `src/agent/clo_agent.py` called from tools |
| 4 | Docs ingest to S3 + Aurora | `ingestion/pipeline.py` end-to-end |
| 5 | Retrieval returns chunks | `retrieval/vector_store.py` query |
| 6 | Bedrock LLM responds | `llm/bedrock.py` with real credentials |
| 7 | Structured decisions produced | JSON matching `DecisionOutput` schema |
| 8 | Decisions are auditable | `audit_records` table populated |
| 9 | Tests pass | `pytest` with exit code 0 |
| 10 | ECS/Fargate deployable | Terraform `plan` completes, ECS task runs |
