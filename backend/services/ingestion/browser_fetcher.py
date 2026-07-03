"""
Headless-browser fetch (Playwright/Chromium) for JS-rendered and bot-gated sources.

Only used when a source registry entry sets `render: "browser"`. Most sources go
through the fast httpx path in fetcher.py; a real browser is reserved for SPAs (e.g.
nha.gov.in / PM-JAY) whose content is not in the server HTML.

Cost note: each call launches and tears down a Chromium instance (~1-2s). That is fine
for ingestion, which runs rarely and over a handful of sources, and keeps the lifecycle
simple (no shared browser to manage). Requires Chromium installed in the image
(see Dockerfile: `playwright install --with-deps chromium`).
"""

import logging

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_NAV_TIMEOUT = 45000  # ms
# Flags required to run Chromium as a constrained/non-root user inside a container.
_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


async def render_page(url: str) -> tuple[str, str]:
    """Load `url` in Chromium, let it render, return (final_url, rendered_html)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=_LAUNCH_ARGS)
        try:
            ctx = await browser.new_context(user_agent=_UA)
            page = await ctx.new_page()
            # networkidle: wait for the SPA's XHRs to settle before snapshotting.
            await page.goto(url, wait_until="networkidle", timeout=_NAV_TIMEOUT)
            html = await page.content()
            final_url = page.url
            return final_url, html
        finally:
            await browser.close()


async def fetch_binary(url: str) -> tuple[str, bytes]:
    """
    Fetch a binary asset (e.g. a PDF) using the browser's request context, so it carries
    a real browser UA and any cookies the site set. Returns (final_url, body_bytes).

    NB: if the URL is actually caught by an SPA router (returns HTML, not the file), the
    caller's PDF parse will fail — that is surfaced as a source error, not hidden.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=_LAUNCH_ARGS)
        try:
            ctx = await browser.new_context(user_agent=_UA)
            resp = await ctx.request.get(url, timeout=_NAV_TIMEOUT)
            body = await resp.body()
            return resp.url, body
        finally:
            await browser.close()
