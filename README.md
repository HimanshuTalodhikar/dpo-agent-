# CLO MCP Server — Chief Legal Officer AI Agent Platform

> Phase 1: Government Legal Knowledge Base + CLO Agent + Amazon Bedrock

## Overview

The CLO MCP Server is an autonomous legal intelligence platform where a Chief Legal Officer AI Agent runs inside an MCP (Model Context Protocol) service, backed by a government/legal knowledge base.

```
MCP Client
    ↓
CLO MCP Server (ECS/Fargate)
    ↓
CLO Agent
    ↓
Legal Retrieval → Aurora pgvector
    ↓
Amazon Bedrock (Claude 3.5 Sonnet + Titan)
    ↓
Structured CLO Decision + Audit Record
```

## Features

- **5 MCP Tools**: `analyze_legal_risk`, `prioritize_risk`, `generate_remediation`, `explain_decision`, `get_agent_status`
- **Government Legal Knowledge Base**: GDPR, CCPA, HIPAA, Title VII, OSHA, UCC Article 2
- **Source-Grounded Reasoning**: Every decision cites specific statutes and regulations
- **Fully Auditable**: Every call writes an audit record with request/decision IDs, retrieved sources, LLM prompt hash, and latency
- **Prompt Injection Protection**: Retrieved documents are sanitized before passing to the LLM
- **AWS-Only Production Stack**: Bedrock, Aurora pgvector, S3, ECS/Fargate, Secrets Manager, KMS

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development outside Docker)
- AWS credentials (for production deployment)

### 1. Clone & Start

```bash
git clone <repo-url>
cd cloagent

# Copy environment file
cp .env.example .env

# Start local stack (pgvector + mock LLM + app)
docker compose up --build
```

Wait ~30 seconds for the app to initialize, then:

```bash
# Verify health
curl http://localhost:8000/health

# List tools
curl http://localhost:8000/mcp/tools
```

### 2. Run a Legal Risk Analysis

```bash
curl -X POST http://localhost:8000/mcp/tools/analyze_legal_risk/call \
  -H "Content-Type: application/json" \
  -d '{
    "query": "We discovered a data breach affecting 10,000 EU customers. What are our obligations?",
    "jurisdiction": "EU",
    "domain": "regulatory"
  }'
```

### 3. Run Tests

```bash
# Unit tests (no services needed)
pytest tests/unit/ -v

# Integration tests (mock-only, no AWS)
pytest tests/integration/ -v

# E2E tests (requires docker-compose up)
pytest tests/e2e/ -v --tb=short
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design.

## Production Deployment

```bash
cd infra

# Initialize Terraform
terraform init

# Plan
terraform plan -var="environment=production"

# Apply
terraform apply -var="environment=production"
```

### AWS Requirements

- Aurora PostgreSQL 15+ with pgvector extension
- Amazon Bedrock access to Claude 3.5 Sonnet + Titan Embeddings
- ECR repository push permission
- ECS/Fargate capacity

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the complete infrastructure diagram.

## Project Structure

```
cloagent/
├── src/
│   ├── main.py              # FastAPI app + MCP endpoints
│   ├── config.py            # Pydantic settings
│   ├── agent/               # CLO Agent
│   │   ├── clo_agent.py     # Main orchestrator
│   │   ├── legal_reasoning.py
│   │   ├── prioritization.py
│   │   ├── remediation.py
│   │   └── decision_explainer.py
│   ├── retrieval/           # Vector search
│   │   └── vector_store.py
│   ├── llm/                 # LLM abstraction
│   │   ├── base.py
│   │   ├── bedrock.py
│   │   └── mock.py
│   ├── embedding/           # Embedding abstraction
│   │   ├── base.py
│   │   ├── bedrock.py
│   │   └── mock.py
│   ├── storage/             # Data layer
│   │   ├── aurora.py        # Aurora/pgvector
│   │   ├── s3_client.py
│   │   └── audit.py
│   ├── ingestion/           # Document pipeline
│   │   ├── parser.py
│   │   ├── chunker.py
│   │   └── pipeline.py
│   └── mcp/
│       └── tools.py         # MCP tool definitions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── infra/                   # Terraform
│   ├── main.tf
│   ├── aurora.tf
│   ├── ecs.tf
│   ├── networking.tf
│   ├── s3.tf
│   └���─ iam.tf
└── sample_docs/             # Government legal documents
    ├── regulatory/
    ├── employment/
    └── contracts/
```

## Security

- **Least privilege IAM**: ECS task role has only Bedrock, S3, Aurora, Secrets Manager, KMS
- **Secrets Manager**: DB credentials injected at runtime, never in environment variables
- **KMS encryption**: All data encrypted at rest (Aurora, S3)
- **VPC isolation**: Aurora and ECS tasks in private subnets, no public access
- **Audit logging**: Every decision logged with SHA-256 hashes of input and LLM prompt
- **Prompt injection protection**: Retrieved documents sanitized before LLM calls

## Future Phases

- Phase 2: Slack/Email ingestion, court feeds, customer vector DBs
- Phase 3: Autonomous action execution with approval workflows
- Phase 4: Multi-jurisdiction compliance dashboards
