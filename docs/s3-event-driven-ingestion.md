# Event-Driven S3 Automated Document Ingestion Pipeline

## 1. Overview

The **Event-Driven S3 Automated Ingestion Pipeline** automatically ingests legal documents (PDFs) uploaded to AWS S3 into **Zep Cloud Agent Memory** (`govt-knowledge-base`).

```mermaid
flowchart LR
    User[User / System] -->|Upload PDF| S3[AWS S3 Bucket: clo-legal-docs]
    S3 -->|ObjectCreated Event| EventBridge[AWS EventBridge / SNS]
    EventBridge -->|HTTP POST /api/v1/ingest/s3-event| FastAPI[FastAPI MCP Server]
    FastAPI -->|Download PDF| S3Ingestor[S3EventIngestor Service]
    S3Ingestor -->|Extract Text| PyPDF[PyPDF Parser]
    PyPDF -->|Chunk & Form GovtDocument| ZepSDK[Zep Cloud SDK AsyncZep]
    ZepSDK -->|Graph Memory Ingestion| ZepGraph[Zep Cloud Graph: govt-knowledge-base]
```

---

## 2. API Endpoints

### A. `POST /api/v1/ingest/s3-event`
Receives standard AWS S3 `ObjectCreated:Put` event notification payloads (sent via AWS EventBridge, SQS, or SNS Webhook).

**Request Body Example**:
```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "ap-south-1",
      "eventName": "ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "clo-legal-docs-bucket"
        },
        "object": {
          "key": "incoming/DPDP_Rules_2025.pdf"
        }
      }
    }
  ]
}
```

**Response Example**:
```json
{
  "success": true,
  "records_processed": 1,
  "results": [
    {
      "doc_id": "doc-DPDP-Rules-2025",
      "title": "DPDP_Rules_2025",
      "chunks_created": 79,
      "ingestion_time_ms": 1420.5,
      "errors": []
    }
  ]
}
```

---

### B. `POST /api/v1/ingest/s3-file`
Direct endpoint to trigger ingestion for a specific file stored in AWS S3.

**Request Body Example**:
```json
{
  "bucket": "clo-legal-docs-bucket",
  "key": "legal-docs/DPDP_Rules_2025.pdf",
  "document_id": "custom-doc-id-123"
}
```

---

## 3. Metadata Inference & Categorization

The `S3EventIngestor` service automatically inspects document keys to infer domain metadata:

| Keyword in Key | Document Type | Classification | Issuing Authority |
| :--- | :--- | :--- | :--- |
| `cert` | `REGULATION` | `SENSITIVE` | Indian Computer Emergency Response Team (CERT-In) |
| `dpdp` | `RULE` | `UNCLASSIFIED` | Ministry of Electronics & Information Technology |
| `it_act` | `ACT` | `UNCLASSIFIED` | Parliament of India |
| `sdpi` | `REPORT` | `UNCLASSIFIED` | National Institute of Public Finance and Policy |

---

## 4. Verification

The pipeline has been verified with unit tests covering metadata inference, S3 event parsing, PDF text extraction, and Zep Cloud API ingestion. All 45 tests pass.
