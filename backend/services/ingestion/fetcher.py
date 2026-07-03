"""
Fetch a source and turn it into clean, normalized text sections + a content hash.

- HTML: parsed with BeautifulSoup, boilerplate (nav/footer/script/style) stripped,
  content split into (heading, text) sections following the document's own <h1..h3>.
- PDF: extracted with pypdf, page by page.

The content hash is computed over the *normalized* text (collapsed whitespace) so
cosmetic markup changes don't trigger a false "content changed" during re-crawl,
but a real wording/number change does.

Network and parsing are blocking, so they run in a thread via asyncio.to_thread to
stay friendly to the async app.
"""

import hashlib
import io
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import asyncio
import httpx

logger = logging.getLogger(__name__)

# A browser-like UA. Several government sites (e.g. mohfw.gov.in) 403 non-browser
# clients, so we present as a real browser even on the plain httpx path.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 VERA-RAG-ingest/1.0"
)
_TIMEOUT = httpx.Timeout(30.0)
_MAX_BYTES = 8 * 1024 * 1024  # 8 MB safety cap


@dataclass
class Section:
    heading: str
    text: str


@dataclass
class FetchResult:
    final_url: str          # after redirects — may differ from the requested URL
    sections: list[Section] = field(default_factory=list)
    content_hash: str = ""
    published_date: Optional[str] = None   # ISO date string if the source exposes one
    full_text: str = ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_date(raw: Optional[str]) -> Optional[str]:
    """Best-effort parse of a source's own date into an ISO 'YYYY-MM-DD' string.

    Handles ISO timestamps and human formats like '26 January 2024'. Returns None
    if it can't be parsed cleanly — a null published_date is fine; a garbage one is not.
    """
    if not raw:
        return None
    raw = raw.strip()
    # ISO date / timestamp: take the leading date component if it is well-formed.
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return m.group(0)
    from datetime import datetime
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _hash_sections(sections: list[Section]) -> str:
    joined = "\n".join(f"{s.heading}\n{s.text}" for s in sections)
    return hashlib.sha256(_normalize(joined).encode("utf-8")).hexdigest()


# ── HTML ─────────────────────────────────────────────────────────────────────

def _parse_html(html: str) -> tuple[list[Section], Optional[str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()

    # NHS pages carry a "Page last reviewed" date we can use as published_date.
    published = None
    for meta_name in ("nhs.last-review", "article:modified_time", "last-modified"):
        m = soup.find("meta", attrs={"name": meta_name}) or soup.find(
            "meta", attrs={"property": meta_name}
        )
        if m and m.get("content"):
            published = _parse_date(m["content"])
            if published:
                break

    main = soup.find("main") or soup.find("article") or soup.body or soup

    sections: list[Section] = []
    current = Section(heading="", text="")
    for el in main.find_all(["h1", "h2", "h3", "p", "li"]):
        txt = _normalize(el.get_text(" "))
        if not txt:
            continue
        if el.name in ("h1", "h2", "h3"):
            if current.text:
                sections.append(current)
            current = Section(heading=txt, text="")
        else:
            current.text = f"{current.text} {txt}".strip()
    if current.text:
        sections.append(current)

    # Drop sections that ended up empty of prose.
    sections = [s for s in sections if s.text]
    return sections, published


# ── PDF ──────────────────────────────────────────────────────────────────────

def _parse_pdf(data: bytes) -> list[Section]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    sections: list[Section] = []
    for i, page in enumerate(reader.pages):
        txt = _normalize(page.extract_text() or "")
        if txt:
            sections.append(Section(heading=f"Page {i + 1}", text=txt))
    return sections


# ── Public API ───────────────────────────────────────────────────────────────

def _build_result(final_url: str, sections: list[Section], published: Optional[str], url: str) -> FetchResult:
    if not sections:
        raise ValueError(f"No extractable text from {url}")
    full_text = "\n\n".join(f"{s.heading}\n{s.text}".strip() for s in sections)
    return FetchResult(
        final_url=final_url,
        sections=sections,
        content_hash=_hash_sections(sections),
        published_date=published,
        full_text=full_text,
    )


def _fetch_sync(url: str, source_type: str) -> FetchResult:
    headers = {"User-Agent": _USER_AGENT}
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        final_url = str(resp.url)
        content = resp.content
        if len(content) > _MAX_BYTES:
            raise ValueError(f"Source exceeds {_MAX_BYTES} byte cap: {url}")

    published = None
    if source_type == "pdf":
        sections = _parse_pdf(content)
    else:
        sections, published = _parse_html(content.decode(resp.encoding or "utf-8", "replace"))
    return _build_result(final_url, sections, published, url)


async def _fetch_rendered(url: str, source_type: str) -> FetchResult:
    """Fetch a JS-rendered source via a headless browser (Playwright)."""
    from services.ingestion import browser_fetcher

    if source_type == "pdf":
        final_url, data = await browser_fetcher.fetch_binary(url)
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError(f"Rendered fetch did not return binary PDF for {url}")
        sections = await asyncio.to_thread(_parse_pdf, bytes(data))
        published = None
    else:
        final_url, html = await browser_fetcher.render_page(url)
        sections, published = await asyncio.to_thread(_parse_html, html)
    return _build_result(final_url, sections, published, url)


async def fetch_source(url: str, source_type: str, render: bool = False) -> FetchResult:
    """
    Fetch + extract a source. Raises on network/parse failure (caller records error).

    render=True routes through a headless browser for JS-rendered pages (SPAs like
    nha.gov.in). Default is the fast httpx path.
    """
    if render:
        return await _fetch_rendered(url, source_type)
    return await asyncio.to_thread(_fetch_sync, url, source_type)
