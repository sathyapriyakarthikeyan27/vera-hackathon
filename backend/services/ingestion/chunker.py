"""
Heading-aware chunking with overlap.

Strategy:
- Respect the document's own section boundaries (from the fetcher). A chunk never
  spans two headings, so each chunk stays topically coherent and carries its heading
  as context.
- Within a long section, split on sentence boundaries into ~TARGET_TOKENS windows
  with SENTENCE overlap, so a fact split across a boundary is still retrievable.
- Very short adjacent sections under the same heading are packed together rather
  than emitted as tiny, low-signal chunks.

Token counts are estimated (~4 chars/token) — good enough for sizing without pulling
in a tokenizer dependency. The embedding model has plenty of headroom over these sizes.
"""

import re
from dataclasses import dataclass

from services.ingestion.fetcher import Section

TARGET_TOKENS = 350
MAX_TOKENS = 500
OVERLAP_SENTENCES = 1
MIN_CHUNK_CHARS = 80


@dataclass
class Chunk:
    heading: str
    content: str
    token_estimate: int


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _split_sentences(text: str) -> list[str]:
    # Lightweight sentence split; avoids a heavy NLP dependency.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _chunk_section(heading: str, text: str) -> list[Chunk]:
    if _est_tokens(text) <= MAX_TOKENS:
        return [Chunk(heading=heading, content=text, token_estimate=_est_tokens(text))]

    sentences = _split_sentences(text)
    chunks: list[Chunk] = []
    window: list[str] = []
    window_tokens = 0

    for sent in sentences:
        st = _est_tokens(sent)
        if window and window_tokens + st > TARGET_TOKENS:
            body = " ".join(window)
            chunks.append(Chunk(heading=heading, content=body, token_estimate=window_tokens))
            # carry overlap sentences into the next window
            window = window[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []
            window_tokens = sum(_est_tokens(s) for s in window)
        window.append(sent)
        window_tokens += st

    if window:
        body = " ".join(window)
        chunks.append(Chunk(heading=heading, content=body, token_estimate=window_tokens))
    return chunks


def chunk_sections(sections: list[Section]) -> list[Chunk]:
    """Turn fetched sections into embeddable chunks."""
    chunks: list[Chunk] = []
    for sec in sections:
        heading = sec.heading or ""
        text = sec.text.strip()
        if len(text) < MIN_CHUNK_CHARS and chunks and chunks[-1].heading == heading:
            # merge a tiny fragment into the previous chunk under the same heading
            prev = chunks[-1]
            merged = f"{prev.content} {text}".strip()
            chunks[-1] = Chunk(heading=heading, content=merged, token_estimate=_est_tokens(merged))
            continue
        chunks.extend(_chunk_section(heading, text))
    return chunks
