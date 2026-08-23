"""Thin wrapper around Playwright for fetching rendered page content and preparing applications.

Many company career pages (Workday, Greenhouse, Lever, custom SPAs) render job listings via
JavaScript, so a plain HTTP GET often returns an empty shell. This renders the page in a real
headless browser and returns visible text plus links, which the Job Discovery Agent then feeds
to the LLM for extraction.
"""
import re

MAX_PAGE_TEXT_CHARS = 8000
PAGE_LOAD_TIMEOUT_MS = 20000

_FIELD_SELECTOR = (
    "form input:not([type=hidden]):not([type=submit]):not([type=button])"
    ":not([type=checkbox]):not([type=radio]), form select, form textarea"
)

_LABEL_JS = """el => {
  function textOf(node) { return node ? node.innerText.trim() : ''; }
  const id = el.id || '';
  let label = '';
  if (id) {
    try {
      const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lab) label = textOf(lab);
    } catch (e) {}
  }
  if (!label) {
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel) label = ariaLabel;
  }
  if (!label) {
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      const ref = document.getElementById(labelledBy);
      if (ref) label = textOf(ref);
    }
  }
  if (!label) {
    const wrapping = el.closest('label');
    if (wrapping) label = textOf(wrapping);
  }
  if (!label && el.placeholder) label = el.placeholder;
  return {
    tag: el.tagName.toLowerCase(),
    type: (el.getAttribute('type') || '').toLowerCase(),
    name: el.name || '',
    id: id,
    label: label.replace(/\\s+/g, ' ').trim(),
  };
}"""

_BLOCKER_PATTERNS = [
    ("CAPTCHA", r"recaptcha|hcaptcha|g-recaptcha|are you a robot"),
    ("OTP/verification code", r"one[-\s]?time password|verification code|\botp\b"),
]


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


def _detect_blockers(page) -> list[str]:
    """Text-pattern based (deterministic) — flags CAPTCHA/OTP/login so we stop rather than guess."""
    blockers = []
    try:
        html = page.content().lower()
    except Exception:
        html = ""
    for name, pattern in _BLOCKER_PATTERNS:
        if re.search(pattern, html):
            blockers.append(name)
    try:
        if page.query_selector('input[type="password"]'):
            blockers.append("Login or account creation appears required")
    except Exception:
        pass
    return blockers


def prepare_application_page(
    url: str, profile: dict, preferences: dict, resume_path: str | None, screenshot_path: str,
) -> dict:
    """Opens a real application page, fills in what can be safely and confidently resolved from
    the resume, screenshots the result, then closes the browser.

    Never submits anything — there is no code path here that clicks a submit button. If a
    CAPTCHA/OTP/login is detected, no fields are touched at all; the caller decides what to do
    (stop and tell the user manual action is required).
    """
    from playwright.sync_api import sync_playwright

    from app.services.form_filler import NEVER_AUTO_FILL, classify_field, resolve_value

    fields_report: list[dict] = []
    blockers: list[str] = []

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

                blockers = _detect_blockers(page)

                if not blockers:
                    handles = page.query_selector_all(_FIELD_SELECTOR)
                    for h in handles:
                        try:
                            if not h.is_visible():
                                continue
                            meta = h.evaluate(_LABEL_JS)
                        except Exception:
                            continue

                        field_type = classify_field(meta["label"], meta["name"], meta["id"], meta["type"])
                        entry = {
                            "label": meta["label"] or meta["name"] or meta["id"] or "(unlabeled field)",
                            "field_type": field_type,
                            "value": None,
                            "source": None,
                            "filled": False,
                        }

                        if field_type is None:
                            entry["source"] = "unrecognized_field"
                        elif field_type in NEVER_AUTO_FILL:
                            entry["source"] = "requires_your_input"
                        elif field_type == "resume_upload":
                            if resume_path:
                                try:
                                    h.set_input_files(resume_path)
                                    entry["value"] = "(resume file attached)"
                                    entry["source"] = "resume_file"
                                    entry["filled"] = True
                                except Exception:
                                    entry["source"] = "could_not_attach_file"
                            else:
                                entry["source"] = "no_resume_file_available"
                        else:
                            value, source = resolve_value(field_type, profile, preferences)
                            entry["source"] = source
                            if value:
                                try:
                                    if meta["tag"] == "select":
                                        h.select_option(label=value)
                                    else:
                                        h.fill(value)
                                    entry["value"] = value
                                    entry["filled"] = True
                                except Exception:
                                    entry["source"] = "could_not_fill"

                        fields_report.append(entry)

                try:
                    page.screenshot(path=screenshot_path, full_page=True)
                except Exception:
                    pass
            finally:
                browser.close()
    except Exception as e:
        raise BrowserFetchError(f"Could not load application page '{url}': {e}") from e

    return {"blockers": blockers, "fields": fields_report}
