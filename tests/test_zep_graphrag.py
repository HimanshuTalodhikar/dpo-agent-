"""
Test script for Graphiti + Neptune GraphRAG Layer
================================================
Ingest dummy government documents and verify search/retrieval works.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

from src.services.zep_graphrag import (
    GovtDocument,
    DocumentType,
    DocumentClassification,
    get_graphrag_service,
)

# ── Dummy Government Documents ──────────────────────────────────────────────────

DUMMY_DOCUMENTS: list[dict[str, Any]] = [
    {
        "title": "Digital India Initiative Guidelines 2024",
        "doc_id": "POL-2024-001",
        "doc_type": DocumentType.GUIDELINE,
        "classification": DocumentClassification.UNCLASSIFIED,
        "issuing_authority": "Ministry of Electronics & IT",
        "effective_date": datetime(2024, 1, 15, tzinfo=timezone.utc),
        "jurisdiction": "central",
        "subject_tags": ["digital-india", "e-governance", "citizen-services"],
        "reference_numbers": ["MEITY/DIGI/2024/001"],
        "content": """
        DIGITAL INDIA INITIATIVE GUIDELINES - 2024

        1. OBJECTIVES
        1.1. To transform India into a digitally empowered society and knowledge economy.
        1.2. To ensure digital infrastructure as a core utility to every citizen.
        1.3. To make government services electronically available.

        2. DIGITAL LITERACY
        2.1. Digital literacy programmes shall be conducted in all districts.
        2.2. At least one digitally skilled person per family in rural areas.
        2.3. Online courses shall be made available in all regional languages.

        3. CYBERSECURITY
        3.1. All digital platforms shall implement multi-factor authentication.
        3.2. Data encryption standards shall comply with NIST guidelines.
        3.3. Incident response protocols shall be established within 60 days.
        """.strip(),
    },
    {
        "title": "DPDP Act 2023 - Data Protection Requirements",
        "doc_id": "DPDP-2023-001",
        "doc_type": DocumentType.ACT,
        "classification": DocumentClassification.UNCLASSIFIED,
        "issuing_authority": "Parliament of India",
        "effective_date": datetime(2023, 8, 11, tzinfo=timezone.utc),
        "jurisdiction": "central",
        "subject_tags": ["data-protection", "privacy", "personal-data", "dpdp"],
        "reference_numbers": ["DPDP-ACT-2023"],
        "content": """
        DIGITAL PERSONAL DATA PROTECTION ACT, 2023

        1. PRELIMINARY
        1.1. This Act provides for protection of digital personal data.
        1.2. Applies to processing of digital personal data collected online or digitised.

        2. OBLIGATIONS OF DATA FIDUCIARY
        2.1. Process data in a fair and reasonable manner.
        2.2. Ensure accuracy and completeness of data.
        2.3. Implement security safeguards against breaches.

        3. RIGHTS OF DATA PRINCIPAL
        3.1. Right to access information and correction.
        3.2. Right to erasure and data portability.
        3.3. Right to grievance redressal within 30 days.

        4. PENALTIES
        4.1. Penalty up to Rs. 250 crore for breach.
        4.2. Penalty up to Rs. 10,000 for non-compliance with Data Principal rights.
        """.strip(),
    },
    {
        "title": "CERT-In Cyber Incident Response Guidelines",
        "doc_id": "CERT-2024-001",
        "doc_type": DocumentType.REGULATION,
        "classification": DocumentClassification.SENSITIVE,
        "issuing_authority": "Indian Computer Emergency Response Team",
        "effective_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "jurisdiction": "central",
        "subject_tags": ["cybersecurity", "incident-response", "data-breach", "mandatory-reporting"],
        "reference_numbers": ["CERT-In/REG/2024/001"],
        "content": """
        CERT-In CYBER INCIDENT RESPONSE GUIDELINES

        1. MANDATORY INCIDENT REPORTING
        1.1. All service providers must report cyber incidents within 6 hours.
        1.2. Incidents affecting critical infrastructure within 1 hour.
        1.3. Data breaches affecting 500+ users must be reported.

        2. INCIDENT CATEGORIES
        2.1. Tier 1: Critical (ransomware, APT, data exfiltration)
        2.2. Tier 2: High (phishing, DDoS, malware)
        2.3. Tier 3: Medium (unauthorised access, policy violation)

        3. RESPONSE REQUIREMENTS
        3.1. Immediate containment within 1 hour of detection.
        3.2. Forensic preservation of evidence.
        3.3. Notification to affected users within 24 hours.
        """.strip(),
    },
]


async def run_tests() -> None:
    """Run ingestion and search tests."""
    service = get_graphrag_service(sync=False)

    print("\n" + "=" * 60)
    print("GRAPHITI GRAPHRAG TEST")
    print("=" * 60)
    print(f"Graph: {service.graph_name}")
    print(f"Neptune: {service.neptune_host}")
    print(f"AOSS: {service.aoss_host}")

    # Ingest all documents
    print("\n--- INGESTION ---")
    results = {}
    for doc_data in DUMMY_DOCUMENTS:
        doc = GovtDocument(**doc_data)
        print(f"\nIngesting: {doc.title}")
        result = await service.ingest_document(doc)
        results[doc.doc_id] = result
        print(f"  -> {result.chunks_created} chunks in {result.ingestion_time_ms:.0f}ms")
        if result.errors:
            for err in result.errors[:3]:
                print(f"  ERROR: {err}")

    # Search tests
    print("\n--- SEARCH TESTS ---")
    queries = [
        ("data protection", "auto"),
        ("cybersecurity incident", "auto"),
        ("digital India", "auto"),
    ]
    for query, scope in queries:
        results_list = await service.search(query, scope=scope, limit=3)
        print(f"\nQuery: '{query}' (scope={scope})")
        if not results_list:
            print("  -> No results")
        for r in results_list:
            print(f"  Score: {r.score:.3f} | {r.content[:100].replace(chr(10), ' ')}")

    await service.close()
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
