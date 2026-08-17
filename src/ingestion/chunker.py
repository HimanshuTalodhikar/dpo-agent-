"""Semantic text chunker for legal documents."""

from __future__ import annotations

import re
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Approximate tokens per character (English prose ~4 chars/token)
TOKENS_PER_CHAR = 0.25


@dataclass
class TextChunk:
    """A single text chunk with metadata."""

    chunk_index: int
    content: str
    section: str | None
    section_ref: str | None
    token_count: int
    start_char: int
    end_char: int


class LegalChunker:
    """Splits legal documents into semantically coherent chunks.

    Strategy:
    1. First try to split on section headings (markdown #, numbered sections)
    2. Fall back to sentence-boundary splitting with overlap
    3. Hard cap at max_tokens
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 64,
        overlap_chars: int | None = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens
        # Convert token overlap to approximate char overlap
        self._overlap_chars = overlap_chars or int(overlap_tokens / TOKENS_PER_CHAR)  # type: ignore[arg-type]

    def chunk_text(self, text: str) -> list[TextChunk]:
        """Split text into chunks."""
        chunks: list[TextChunk] = []

        # Try section-based splitting first
        sections = self._split_by_sections(text)
        if len(sections) > 1:
            current = ""
            current_start = 0
            current_section = None
            current_section_ref = None
            chunk_index = 0
            char_pos = 0

            for section_text, section, ref in sections:
                section_tokens = int(len(section_text) * TOKENS_PER_CHAR)

                if section_tokens > self._max_tokens:
                    # Flush current chunk
                    if current:
                        chunks.append(TextChunk(
                            chunk_index=chunk_index,
                            content=current.strip(),
                            section=current_section,
                            section_ref=current_section_ref,
                            token_count=int(len(current) * TOKENS_PER_CHAR),
                            start_char=current_start,
                            end_char=char_pos,
                        ))
                        chunk_index += 1
                        current = ""
                        current_start = char_pos

                    # Split large section by sentences
                    sub_chunks = self._split_by_sentences(section_text)
                    for sub in sub_chunks:
                        chunks.append(TextChunk(
                            chunk_index=chunk_index,
                            content=sub.strip(),
                            section=section,
                            section_ref=ref,
                            token_count=int(len(sub) * TOKENS_PER_CHAR),
                            start_char=char_pos,
                            end_char=char_pos + len(sub),
                        ))
                        char_pos += len(sub)
                        chunk_index += 1
                else:
                    if (int((len(current) + len(section_text)) * TOKENS_PER_CHAR) > self._max_tokens
                            and current):
                        chunks.append(TextChunk(
                            chunk_index=chunk_index,
                            content=current.strip(),
                            section=current_section,
                            section_ref=current_section_ref,
                            token_count=int(len(current) * TOKENS_PER_CHAR),
                            start_char=current_start,
                            end_char=char_pos,
                        ))
                        chunk_index += 1
                        # Overlap
                        overlap_text = current[-self._overlap_chars:] if len(current) > self._overlap_chars else current
                        current = overlap_text + "\n\n" + section_text
                        current_start = char_pos - len(overlap_text)
                    else:
                        if current:
                            current += "\n\n"
                        current += section_text
                    char_pos += len(section_text) + 2

                current_section = section
                current_section_ref = ref

            # Flush remaining
            if current.strip():
                chunks.append(TextChunk(
                    chunk_index=chunk_index,
                    content=current.strip(),
                    section=current_section,
                    section_ref=current_section_ref,
                    token_count=int(len(current) * TOKENS_PER_CHAR),
                    start_char=current_start,
                    end_char=char_pos,
                ))
        else:
            # Fallback: pure sentence splitting
            sub_chunks = self._split_by_sentences(text)
            for i, sub in enumerate(sub_chunks):
                chunks.append(TextChunk(
                    chunk_index=i,
                    content=sub.strip(),
                    section=None,
                    section_ref=None,
                    token_count=int(len(sub) * TOKENS_PER_CHAR),
                    start_char=0,
                    end_char=len(sub),
                ))

        # Assign sequential indices
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i

        logger.debug("chunker.done", original_chars=len(text), chunks=len(chunks))
        return chunks

    def _split_by_sections(self, text: str) -> list[tuple[str, str | None, str | None]]:
        """Split text on markdown headings and numbered sections."""
        # Markdown headings: # Title, ## Section
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        parts: list[tuple[str, str | None, str | None]] = []
        last_end = 0

        for match in heading_pattern.finditer(text):
            if match.start() > last_end:
                parts.append((text[last_end:match.start()], None, None))
            heading_text = match.group(2).strip()
            level = len(match.group(1))
            # Extract section reference (e.g., "Art. 5" from "5. Principles")
            section_ref = self._extract_section_ref(heading_text)
            parts.append((text[match.start():], heading_text, section_ref))
            last_end = match.start()

        if last_end < len(text):
            parts.append((text[last_end:], None, None))

        return parts if parts else [(text, None, None)]

    def _extract_section_ref(self, heading: str) -> str | None:
        """Extract section reference from a heading."""
        # Patterns: "Art. 5 —", "§ 1798.100", "Section 5.2", "Article 33"
        patterns = [
            r"(?:Art(?:icle)?\.?\s*)(\d+[a-z]?)",
            r"§\s*(\d+(?:\.\d+)*)",
            r"(?:Section|sec\.?)\s*(\d+(?:\.\d+)*)",
        ]
        for pattern in patterns:
            m = re.search(pattern, heading, re.IGNORECASE)
            if m:
                return m.group(0)
        return None

    def _split_by_sentences(self, text: str) -> list[str]:
        """Split text into sentence-level chunks respecting token limits."""
        # Sentence boundary: ., !, ? followed by space + capital
        sentence_pattern = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
        sentences = sentence_pattern.split(text)

        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if int((len(current) + len(sentence)) * TOKENS_PER_CHAR) <= self._max_tokens:
                current += (" " if current else "") + sentence
            else:
                if current:
                    chunks.append(current)
                # If single sentence exceeds limit, truncate it
                if int(len(sentence) * TOKENS_PER_CHAR) > self._max_tokens:
                    current = sentence[: int(float(self._max_tokens) / TOKENS_PER_CHAR) ]
                else:
                    current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text[: int(float(self._max_tokens) / TOKENS_PER_CHAR) ]]
