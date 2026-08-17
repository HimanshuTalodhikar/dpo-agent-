"""Document parser — extracts text from PDFs and plain text files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DocumentParseError(Exception):
    """Raised when a document cannot be parsed."""


async def parse_document(file_path: str | Path) -> str:
    """Parse a document and return plain text content.

    Supported formats: .txt, .pdf
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return await _parse_txt(path)
    elif suffix == ".pdf":
        return await _parse_pdf(path)
    else:
        raise DocumentParseError(f"Unsupported file format: {suffix}")


async def _parse_txt(path: Path) -> str:
    """Parse a plain text file."""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")
    logger.debug("parser.txt", path=str(path), chars=len(content))
    return content


async def _parse_pdf(path: Path) -> str:
    """Parse a PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise DocumentParseError(
            "pypdf is required to parse PDF files. Install with: pip install pypdf"
        )

    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        content = "\n\n".join(parts)
        logger.debug("parser.pdf", path=str(path), pages=len(reader.pages), chars=len(content))
        return content
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse PDF {path}: {exc}") from exc


def extract_metadata_from_filename(filename: str) -> dict[str, Any]:
    """Infer document metadata from the filename.

    Convention: {domain}_{jurisdiction}_{law_type}_{effective_date}.txt
    Example: regulatory_EU_GDPR_2016-05-25.txt
    """
    name = Path(filename).stem
    parts = name.split("_")

    metadata: dict[str, Any] = {
        "title": name.replace("_", " ").title(),
        "jurisdiction": "UNKNOWN",
        "domain": "general",
        "law_type": "UNKNOWN",
        "effective_date": None,
    }

    # Known jurisdiction prefixes
    JURISDICTIONS = {
        "EU": "EU", "US": "US-FEDERAL", "US-CA": "US-CA", "US-NY": "US-NY",
        "UK": "UK", "DE": "DE", "FR": "FR",
    }
    for prefix, jurisdiction in JURISDICTIONS.items():
        if prefix in name.upper():
            metadata["jurisdiction"] = jurisdiction
            break

    # Known domains
    if any(k in name.lower() for k in ["privacy", "gdpr", "ccpa", "hipaa", "data"]):
        metadata["domain"] = "regulatory"
    elif any(k in name.lower() for k in ["employment", "labor", "osha", "titlevii", "eeoc"]):
        metadata["domain"] = "employment"
    elif any(k in name.lower() for k in ["contract", "ucc", "agreement"]):
        metadata["domain"] = "contracts"

    # Law type detection
    LAW_TYPES = {
        "GDPR": "GDPR", "CCPA": "CCPA", "HIPAA": "HIPAA",
        "SOX": "SOX", "OSHA": "OSHA", "TITLEVII": "Title VII",
        "UCC": "UCC", "ECOA": "ECOA",
    }
    for law, law_type in LAW_TYPES.items():
        if law in name.upper():
            metadata["law_type"] = law_type
            break

    # Date extraction: look for ISO-style dates (YYYY-MM-DD)
    date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", name)
    if date_match:
        metadata["effective_date"] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

    return metadata
