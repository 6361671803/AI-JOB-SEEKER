"""Thin wrapper around Playwright for fetching rendered page content.

Many company career pages (Workday, Greenhouse, Lever, custom SPAs) render job listings via
JavaScript, so a plain HTTP GET often returns an empty shell. This renders the page in a real
headless browser and returns visible text plus links, which the Job Discovery Agent then feeds
to the LLM for extraction.

Uses Playwright's async API so multiple pages can be rendered concurrently from one shared
browser instance within a single event loop. An earlier attempt at concurrency used the sync API
from a ThreadPoolExecutor instead — Playwright's sync API is not thread-safe, and that caused a
real 30+ minute hang. The async API's single-event-loop model avoids that failure mode.
"""
import asyncio

MAX_PAGE_TEXT_CHARS = 8000
PAGE_LOAD_TIMEOUT_MS = 20000


class BrowserFetchError(RuntimeError):
    pass


async def fetch_rendered_page_async(browser, url: str) -> dict:
    """Renders `url` using a page opened on the given (already-launched) async Playwright
    `browser`, and returns {"text": visible page text, "links": [{"text","href"}]}. Opens and
    closes its own page/tab so concurrent calls against the same shared browser don't interfere
    with each other."""
    try:
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # some career pages never go fully idle (polling widgets, etc.)

            # Many ATS job boards (Greenhouse, Lever, etc.) lazy-load listings as the user
            # scrolls or paginate via "Load more" — a couple of scroll passes surfaces real
            # listings that a single static render would otherwise miss.
            try:
                for _ in range(3):
                    await page.mouse.wheel(0, 3000)
                    await page.wait_for_timeout(400)
            except Exception:
                pass

            text = await page.inner_text("body")
            links = await page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => ({text: e.innerText.trim(), href: e.href})).filter(l => l.text)",
            )
        finally:
            await page.close()
    except Exception as e:
        raise BrowserFetchError(f"Could not load '{url}': {e}") from e

    return {
        "text": text[:MAX_PAGE_TEXT_CHARS],
        "links": links[:100],
    }


def fetch_rendered_page(url: str) -> dict:
    """Sync convenience wrapper: launches its own short-lived browser for a single page fetch.
    Kept for any one-off caller that doesn't need a shared browser across multiple concurrent
    fetches (see fetch_rendered_page_async for that)."""
    from playwright.async_api import async_playwright

    async def _run() -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                return await fetch_rendered_page_async(browser, url)
            finally:
                await browser.close()

    return asyncio.run(_run())
