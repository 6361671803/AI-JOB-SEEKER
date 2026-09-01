"""Thin wrapper around Playwright for fetching rendered page content and preparing applications.

Many company career pages (Workday, Greenhouse, Lever, custom SPAs) render job listings via
JavaScript, so a plain HTTP GET often returns an empty shell. This renders the page in a real
headless browser and returns visible text plus links, which the Job Discovery Agent then feeds
to the LLM for extraction.
"""

MAX_PAGE_TEXT_CHARS = 8000
PAGE_LOAD_TIMEOUT_MS = 20000


class BrowserFetchError(RuntimeError):
    pass


def fetch_rendered_page(url: str) -> dict:
    """Returns {"text": visible page text, "links": [{"text","href"}]} for a rendered page."""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass  # some career pages never go fully idle (polling widgets, etc.)

                # Many ATS job boards (Greenhouse, Lever, etc.) lazy-load listings as the user
                # scrolls or paginate via "Load more" — a couple of scroll passes surfaces real
                # listings that a single static render would otherwise miss.
                try:
                    for _ in range(3):
                        page.mouse.wheel(0, 3000)
                        page.wait_for_timeout(400)
                except Exception:
                    pass

                text = page.inner_text("body")
                links = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => ({text: e.innerText.trim(), href: e.href})).filter(l => l.text)",
                )
            finally:
                browser.close()
    except Exception as e:
        raise BrowserFetchError(f"Could not load '{url}': {e}") from e

    return {
        "text": text[:MAX_PAGE_TEXT_CHARS],
        "links": links[:100],
    }


def prepare_application_page(url: str, screenshot_path: str) -> None:
    """Opens the official application page in a real browser and screenshots it, so the user has
    a visual record of the page they're about to apply on.

    This never fills in or submits anything — the application itself is always completed by the
    user, on the official site, using the link handed back to them.
    """
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                try:
                    page.screenshot(path=screenshot_path, full_page=True)
                except Exception:
                    pass
            finally:
                browser.close()
    except Exception as e:
        raise BrowserFetchError(f"Could not load application page '{url}': {e}") from e
