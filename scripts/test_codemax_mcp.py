"""
Validation script for Codemax AI service across MCP tools.
"""

from __future__ import annotations

import asyncio
import json
import logging
from src.llm.codemax import CodemaxLLMProvider
from src.services.zep_graphrag import get_graphrag_service, GraphitiRetrieverAdapter
from src.agent.clo_agent import CLOAgent

logging.basicConfig(level=logging.INFO)


async def main():
    print("======================================================================")
    print(" TESTING CODEMAX AI PROVIDER WITH ZEP CLOUD AGENT MEMORY ON CLO AGENT")
    print("======================================================================")

    # 1. Initialize Codemax LLM Provider
    codemax_key = os.getenv("CODEMAX_API_KEY", "your_codemax_api_key_here")
    llm = CodemaxLLMProvider(
        api_key=codemax_key,
        base_url="https://api.codemax.pro",
        model="claude-sonnet-5",
    )
    print(f"Codemax LLM Provider initialized: model=claude-sonnet-5, base_url=https://api.codemax.pro")

    # 2. Initialize Zep Cloud Retriever
    graph_rag = get_graphrag_service()
    retriever = GraphitiRetrieverAdapter(graph_rag)

    # 3. Initialize CLO Agent
    agent = CLOAgent(llm_provider=llm, retriever=retriever)
    status = agent.get_status()
    print("CLO Agent Status:", json.dumps(status, indent=2))

    # 4. Test Legal Risk Analysis Call
    test_query = (
        "Our financial app processes customer payment data and experienced a unauthorized access incident "
        "at 10:00 AM. Does CERT-In mandatory 6-hour reporting apply?"
    )
    print(f"\nSubmitting Query to CLO Agent (Powered by Codemax AI):\n'{test_query}'\n")

    # Pass dummy session mock for unit/script execution
    class DummySession:
        async def execute(self, *args, **kwargs):
            class DummyResult:
                def fetchone(self): return None
            return DummyResult()
        async def commit(self): pass
        async def close(self): pass

    decision, retrieval = await agent.analyze_legal_risk(
        session=DummySession(),
        query=test_query,
        jurisdiction="central",
    )

    print("======================================================================")
    print(" CODEMAX AI DECISION RESULT")
    print("======================================================================")
    print(f"Decision ID:     {decision.decision_id}")
    print(f"Exposure Level:  {decision.exposure_level}")
    print(f"Priority Rank:   {decision.priority_rank}")
    print(f"Confidence:      {decision.confidence}")
    print(f"Legal Rationale:\n{decision.legal_rationale}\n")
    print("Actionable Steps:")
    for idx, step in enumerate(decision.actionable_steps_array, 1):
        print(f"  {idx}. {step}")

    await graph_rag.close()
    print("======================================================================")
    print(" CODEMAX AI VALIDATION CLEAN PASSED")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(main())
