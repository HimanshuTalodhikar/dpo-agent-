# DPO Agent — Data Protection Officer AI Agent Platform

> Phase 1: Government Legal & Privacy Knowledge Base + DPO Agent + Multi-LLM / Bedrock RAG

## Overview

The **DPO Agent** is an autonomous legal & data protection intelligence platform where a Data Protection Officer (DPO) AI Agent runs inside an MCP (Model Context Protocol) service, backed by a comprehensive government legal and privacy knowledge base (DPDP Act, GDPR, CERT-In, IT Act, etc.).

```
MCP Client / Frontend UI
    ↓
DPO Agent Server (FastAPI + MCP)
    ↓
DPO Agent Orchestrator
    ↓
Legal Retrieval → Aurora pgvector / Zep GraphRAG / Neptune
    ↓
LLM Provider (Claude / Bedrock / Codemax)
    ↓
Structured Risk Analysis + Remediation + Audit Record
```

## Features

- **5 MCP Tools**: `analyze_legal_risk`, `prioritize_risk`, `generate_remediation`, `explain_decision`, `get_agent_status`
- **Comprehensive Privacy & Legal Knowledge Base**: DPDP Act 2023 & Rules 2025, GDPR, CERT-In Directions, IT Act, CCPA, HIPAA
- **Source-Grounded Reasoning**: Every decision cites specific statutes, sections, and regulations
- **Fully Auditable**: Every call writes an audit record with request/decision IDs, retrieved sources, LLM prompt hash, and latency
- **Prompt Injection Protection**: Retrieved documents are sanitized before passing to the LLM
- **Production Stack**: Bedrock / Codemax LLM, Aurora pgvector / Zep GraphRAG, S3, ECS/Fargate, Terraform Infra

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development outside Docker)
- AWS credentials / API keys (configured in `.env`)

### 1. Clone & Start

```bash
git clone https://github.com/HimanshuTalodhikar/dpo-agent-.git
cd dpo-agent-

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

### 2. Run a Data Protection & Legal Risk Analysis

```bash
curl -X POST http://localhost:8000/mcp/tools/analyze_legal_risk/call \
  -H "Content-Type: application/json" \
  -d '{
    "query": "We discovered a personal data breach affecting 10,000 users in India and the EU. What are our notification obligations?",
    "jurisdiction": "IN/EU",
    "domain": "privacy"
  }'
```

### 3. Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests (requires running environment)
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
- Amazon Bedrock or configured LLM provider
- ECR repository push permission
- ECS/Fargate capacity

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the complete infrastructure diagram.

## Project Structure

```
dpo-agent/
├── src/
│   ├── main.py              # FastAPI app + MCP endpoints
│   ├── config.py            # Pydantic settings
│   ├── agent/               # DPO / CLO Agent
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
│   │   ├── codemax.py
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
│   └── iam.tf
└── docs/                    # Government & Privacy Legal Documents
```

## Security

- **Least privilege IAM**: ECS task role has only Bedrock, S3, Aurora, Secrets Manager, KMS
- **Secrets Manager**: DB credentials injected at runtime, never in environment variables
- **KMS encryption**: All data encrypted at rest (Aurora, S3)
- **VPC isolation**: Aurora and ECS tasks in private subnets, no public access
- **Audit logging**: Every decision logged with SHA-256 hashes of input and LLM prompt
- **Prompt injection protection**: Retrieved documents sanitized before LLM calls

## Future Roadmap

- Phase 2: Automated DPIA (Data Protection Impact Assessment) workflow engine
- Phase 3: Real-time CERT-In Incident Response automation
- Phase 4: Multi-jurisdiction data privacy compliance dashboard
