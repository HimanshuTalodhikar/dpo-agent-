#!/usr/bin/env python3
"""
ingest_pdfs.py — Ingest government PDFs into Graphiti + Amazon Neptune
=====================================================================
Reads all PDFs from a directory, extracts text per page,
and loads them into the government knowledge graph.

Usage:
    python scripts/ingest_pdfs.py [--docs-dir <path>]

Environment variables:
    NEPTUNE_HOST      Neptune endpoint (default: neptune-db://localhost:8182)
    AOSS_HOST         OpenSearch Serverless host (required)
    AWS_REGION         AWS region (default: us-east-1)
    GRAPHITI_GRAPH_NAME  Graph name (default: govt-knowledge-base)
    ANTHROPIC_API_KEY  Anthropic API key (required)
    OPENAI_API_KEY    OpenAI API key for embeddings (required)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import sys
import time
from datetime import datetime, timezone

# Ensure src is on path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from src.services.zep_graphrag import (
    GovtDocument,
    DocumentType,
    DocumentClassification,
    get_graphrag_service,
    get_sync_graphrag_service,
)

log = logging.getLogger("ingest_pdfs")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Suppress httpx/httpcore noise from graphiti dependencies
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ── Classification helpers ─────────────────���─────────────────────────────────────

DOC_TYPE_MAP = {
    "cert": DocumentType.REGULATION,
    "dpdp": DocumentType.RULE,
    "it_act": DocumentType.ACT,
    "sdpi": DocumentType.REPORT,
    "rules": DocumentType.RULE,
}
CLASSIFICATION_MAP = {
    "cert": DocumentClassification.SENSITIVE,
    "dpdp": DocumentClassification.UNCLASSIFIED,
    "it_act": DocumentClassification.UNCLASSIFIED,
    "sdpi": DocumentClassification.UNCLASSIFIED,
    "rules": DocumentClassification.UNCLASSIFIED,
}
ISSUING_AUTHORITY_MAP = {
    "cert": "Indian Computer Emergency Response Team (CERT-In)",
    "dpdp": "Ministry of Electronics & Information Technology",
    "it_act": "Parliament of India",
    "sdpi": "National Institute of Public Finance and Policy",
    "rules": "Ministry of Electronics & Information Technology",
}
JURISDICTION_MAP = {
    "cert": "central",
    "dpdp": "central",
    "it_act": "central",
    "sdpi": "central",
    "rules": "central",
}


def _classify(filename: str):
    """Infer document metadata from filename."""
    fname_lower = filename.lower()
    for key, dtype in DOC_TYPE_MAP.items():
        if key in fname_lower:
            return (
                dtype,
                CLASSIFICATION_MAP[key],
                ISSUING_AUTHORITY_MAP[key],
                JURISDICTION_MAP[key],
            )
    return (
        DocumentType.REPORT,
        DocumentClassification.UNCLASSIFIED,
        "Unknown",
        "central",
    )


def _extract_pdf(pdf_path: pathlib.Path):
    """Extract text from each page of a PDF using pypdf."""
    import pypdf
    pages = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if len(text.strip()) < 50:
                continue
            pages.append((i, text))
    except Exception as e:
        log.error("Failed to open %s: %s", pdf_path.name, e)
    return pages


def _make_doc_id(pdf_path: pathlib.Path) -> str:
    name = pdf_path.stem.replace(" ", "-").replace("_", "-")
    return f"doc-{name}"


def _parse_title(text: str, fallback: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:5]:
        if len(line) > 10 and len(line) < 150:
            return line
    return fallback[:100]


def _extract_tags(doc_type: DocumentType, jurisdiction: str) -> list[str]:
    base = [doc_type.value.lower(), jurisdiction, "government", "india"]
    if doc_type == DocumentType.REGULATION:
        return base + ["cyber-security", "incident-response"]
    if doc_type == DocumentType.RULE:
        return base + ["data-protection", "privacy"]
    if doc_type == DocumentType.ACT:
        return base + ["information-technology", "digital-law"]
    if doc_type == DocumentType.REPORT:
        return base + ["policy", "research", "digital-economy"]
    return base + ["regulatory"]


# ── Checkpoint helpers ───────────────��──────────────────────────────────────────

def _checkpoint_path(docs_dir: pathlib.Path) -> pathlib.Path:
    return docs_dir / ".ingest_checkpoint.json"


def _load_checkpoint(docs_dir: pathlib.Path) -> set[str]:
    cp = _checkpoint_path(docs_dir)
    if cp.exists():
        try:
            return set(json.loads(cp.read_text()).get("ingested", []))
        except Exception:
            return set()
    return set()


def _save_checkpoint(docs_dir: pathlib.Path, ingested: set[str]) -> None:
    _checkpoint_path(docs_dir).write_text(
        json.dumps({"ingested": sorted(ingested)}, indent=2)
    )


# ── Core ingestion ──────────────────────────────────────────────────────────────

async def ingest_pdfs_async(
    docs_dir: pathlib.Path,
    skip_existing: bool = True,
) -> dict[str, dict]:
    """Ingest all PDFs asynchronously using Graphiti + Neptune."""
    pdf_files = sorted(docs_dir.glob("*.pdf"))
    if not pdf_files:
        log.error("No PDFs found in %s", docs_dir)
        return {}

    results = {}
    ingested_ids: set[str] = set()
    checkpoint = _load_checkpoint(docs_dir)
    log.info("Checkpoint: %d already ingested", len(checkpoint))

    service = get_graphrag_service()
    total = len(pdf_files)

    try:
        for idx, pdf_path in enumerate(pdf_files, 1):
            dtype, classification, authority, jurisdiction = _classify(pdf_path.name)
            doc_id = _make_doc_id(pdf_path)

            if doc_id in checkpoint:
                log.info("[%d/%d] SKIP   %s (checkpoint)", idx, total, pdf_path.name)
                results[doc_id] = {"status": "skipped", "doc_title": pdf_path.stem, "chunks_created": 0}
                continue

            print(f"[{idx}/{total}] {pdf_path.name}", flush=True)
            log.info("[%d/%d] START  %s", idx, total, pdf_path.name)

            pages = _extract_pdf(pdf_path)
            if not pages:
                log.warning("No text extracted from %s", pdf_path.name)
                results[doc_id] = {"status": "skipped", "doc_title": pdf_path.stem, "chunks_created": 0}
                continue

            full_text = "\n\n".join(f"[Page {pn}] {t}" for pn, t in pages)
            title = _parse_title(full_text, pdf_path.stem)

            doc = GovtDocument(
                title=title,
                content=full_text,
                doc_type=dtype,
                classification=classification,
                doc_id=doc_id,
                issuing_authority=authority,
                effective_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                jurisdiction=jurisdiction,
                subject_tags=_extract_tags(dtype, jurisdiction),
            )

            # Ingest with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = await service.ingest_document(doc)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    log.warning("Retry %d/%d for %s: %s", attempt + 1, max_retries, pdf_path.name, e)
                    await asyncio.sleep(2)

            results[doc_id] = {
                "status": "ok" if not result.errors else "partial",
                "doc_title": title,
                "pages_extracted": len(pages),
                "chunks_created": result.chunks_created,
                "errors": result.errors,
                "ingestion_time_ms": result.ingestion_time_ms,
            }

            ingested_ids.add(doc_id)
            _save_checkpoint(docs_dir, ingested_ids)

            if result.errors:
                print(f"  WARN: {result.chunks_created} chunks, {len(result.errors)} errors", flush=True)
            else:
                print(f"  OK: {result.chunks_created} chunks in {result.ingestion_time_ms:.0f}ms", flush=True)

            await asyncio.sleep(1)

    finally:
        await service.close()

    return results


def ingest_pdfs(
    docs_dir: pathlib.Path,
    skip_existing: bool = True,
) -> dict[str, dict]:
    """Synchronous wrapper for ingest_pdfs_async."""
    return asyncio.run(ingest_pdfs_async(docs_dir, skip_existing))


# ── CLI ────────────���────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest government PDFs into Graphiti + Neptune")
    parser.add_argument(
        "--docs-dir",
        type=pathlib.Path,
        default=pathlib.Path(__file__).parent.parent / "docs",
        help="Directory containing PDFs (default: ./docs)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Reingest all documents (ignore checkpoint)",
    )
    args = parser.parse_args()

    docs_dir = args.docs_dir
    if not docs_dir.exists():
        log.error("Docs directory does not exist: %s", docs_dir)
        sys.exit(1)

    log.info("Starting PDF ingestion from: %s", docs_dir.resolve())

    results = ingest_pdfs(docs_dir, skip_existing=not args.no_skip)

    # Summary
    total = len(results)
    ok = sum(1 for r in results.values() if r["status"] == "ok")
    partial = sum(1 for r in results.values() if r["status"] == "partial")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total PDFs:  {total}")
    print(f"  OK:       {ok}")
    print(f"  Partial:   {partial}")
    print(f"  Skipped:  {skipped}")
    print("=" * 60)
    for doc_id, result in results.items():
        icon = {"ok": "OK", "partial": "WARN", "skipped": "SKIP"}.get(result["status"], "?")
        print(f"  [{icon}] {doc_id} — {result.get('doc_title', '')}")


if __name__ == "__main__":
    main()
