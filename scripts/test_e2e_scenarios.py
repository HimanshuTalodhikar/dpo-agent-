"""
End-to-End Legal Risk Analysis Validation
=====================================================================
Grounds reasoning in Zep Cloud Agent Memory facts using Codemax Anthropic LLM.
"""

from __future__ import annotations

import asyncio
import logging
import os
import json
import pathlib
import sys

# Ensure src is on path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.llm.codemax import CodemaxLLMProvider
from src.services.zep_graphrag import get_graphrag_service, ZepRetrieverAdapter
from src.agent.clo_agent import CLOAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("e2e_validation")


SCENARIOS = [
    {
        "name": "Scenario 1: Customer Data Breach Notification Failure",
        "jurisdiction": "central",
        "domain": "data-protection",
        "query": (
            "Our e-commerce platform suffered a database breach involving 50,000 customer personal records "
            "(names, email addresses, phone numbers, and delivery addresses) at 02:00 AM. The security team "
            "contained the breach and patched the vulnerability by 06:00 AM. The management decided not to "
            "inform the Data Protection Board of India or CERT-In because the vulnerability was quickly resolved. "
            "What is our legal exposure and what penalties apply under DPDP 2023 and CERT-In directions?"
        ),
    },
    {
        "name": "Scenario 2: Ransomware Attack on Government Client Server",
        "jurisdiction": "central",
        "domain": "cybersecurity",
        "query": (
            "A ransomware attack encrypted files on our server providing IT services to a government department. "
            "No data exfiltration was detected, and we restored system backups after 4 hours. "
            "Are we required to report this ransomware incident to CERT-In, and what is the mandatory reporting timeline?"
        ),
    },
    {
        "name": "Scenario 3: Unauthorised Collection & Third-Party Sharing of Personal Data",
        "jurisdiction": "central",
        "domain": "privacy",
        "query": (
            "Our company's mobile app collects user location and contact lists without obtaining explicit consent, "
            "and shares this data with third-party marketing vendors. What is our regulatory risk and penalty "
            "exposure under the Digital Personal Data Protection Act 2023?"
        ),
    },
]


async def run_validation():
    log.info("Starting End-to-End Legal Risk Analysis Validation...")

    api_key = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.codemax.pro")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    # 1. Build components
    llm_provider = CodemaxLLMProvider(api_key=api_key, base_url=base_url, model=model)
    graph_service = get_graphrag_service()
    retriever = ZepRetrieverAdapter(graph_service, top_k=10)
    agent = CLOAgent(llm_provider=llm_provider, retriever=retriever)

    print("\n" + "=" * 80)
    print("CLO AGENT — END-TO-END VALIDATION WITH ZEP CLOUD AGENT MEMORY")
    print("=" * 80)

    for idx, sc in enumerate(SCENARIOS, 1):
        print(f"\n\n[{idx}/3] {sc['name']}")
        print("-" * 80)
        print(f"QUERY: {sc['query']}\n")

        # Execute Legal Risk Analysis
        decision, retrieval_result = await agent.analyze_legal_risk(
            session=None,
            query=sc["query"],
            jurisdiction=sc["jurisdiction"],
            domain=sc["domain"],
        )

        print("RETRIEVED LEGAL CONTEXT (from Zep Cloud Agent Memory):")
        if retrieval_result.chunks:
            for c_idx, chunk in enumerate(retrieval_result.chunks[:4], 1):
                print(f"  {c_idx}. [{chunk.document_id}] (Score: {chunk.similarity:.4f})")
                print(f"     {chunk.content[:150]}...\n")
        else:
            print("  (No chunks retrieved)")

        print("LEGAL DECISION ANALYSIS:")
        print(f"  - Request ID:        {decision.decision_id}")
        print(f"  - Exposure Level:    {decision.exposure_level.upper()}")
        print(f"  - Priority Rank:     {decision.priority_rank}")
        print(f"  - Confidence:        {decision.confidence:.2f}")
        print(f"  - Legal Rationale:\n    {decision.legal_rationale[:300]}...\n")

        print(f"  - Actionable Steps:")
        for a_idx, action in enumerate(decision.actionable_steps_array, 1):
            print(f"      {a_idx}. {action}")

        print(f"\n  - Legal Sources Cited:")
        for s in decision.legal_sources:
            print(f"      * [{s.document_id}] Section: {s.section} — {s.excerpt[:80]}...")

    await graph_service.close()
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE — ALL SCENARIOS EVALUATED SUCCESSFULLY")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_validation())
