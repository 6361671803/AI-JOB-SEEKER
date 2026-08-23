"""Detects which Applicant Tracking System (ATS) hosts a job application page.

Some platforms (Workday, Taleo) are multi-step wizards that often require account creation and
are known to be brittle/unreliable to automate blindly — for those we deliberately stop and hand
the user the official URL rather than risk a broken, misleading auto-fill attempt.
"""
import re
from urllib.parse import urlparse

_DOMAIN_TO_PLATFORM = {
    "greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "smartrecruiters.com": "smartrecruiters",
    "myworkdayjobs.com": "workday",
    "myworkday.com": "workday",
    "taleo.net": "taleo",
}

# Platforms known to be multi-step/login-heavy/inconsistent enough that a generic form-filler
# can't reliably automate them without a real risk of silently getting fields wrong.
NOT_RELIABLY_AUTOMATABLE = {"workday", "taleo"}

KNOWN_ATS_DOMAINS = tuple(_DOMAIN_TO_PLATFORM.keys())

_LISTING_LINK_TEXT_RE = re.compile(
    r"explore open roles|open roles|open positions|current openings|browse jobs|"
    r"search jobs|view all jobs|see all jobs|all open positions|job search|job listings",
    re.IGNORECASE,
)


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for domain, platform in _DOMAIN_TO_PLATFORM.items():
        if domain in host:
            return platform
    return "custom"


def find_ats_link(links: list[dict], exclude_url: str | None = None) -> str | None:
    """Scans rendered-page links for one hosted on a known ATS domain (Greenhouse, Lever, etc).

    Many company "careers" landing pages are just a JS search widget with no real listings in
    static markup, but link out to the actual job board they're built on. Following that link
    gives a second, still-genuine chance to find real listings instead of giving up.
    """
    exclude_host = urlparse(exclude_url).netloc.lower() if exclude_url else None
    for link in links:
        href = link.get("href") or ""
        host = urlparse(href).netloc.lower()
        if not host or host == exclude_host:
            continue
        if any(domain in host for domain in KNOWN_ATS_DOMAINS):
            return href
    return None


def find_secondary_listing_link(links: list[dict], exclude_url: str | None = None) -> str | None:
    """Best-effort second chance for a real job-listing page when the first page had none.

    Tries, in order: (1) a link to a known third-party ATS domain, (2) a same- or different-domain
    link whose own anchor text reads like "Explore open roles" / "View all jobs" / etc — the
    common pattern for a careers landing page that itself is just a widget/hero pointing at the
    real listings elsewhere on the same site. Never guesses a URL that isn't actually a link on
    the page.
    """
    ats_link = find_ats_link(links, exclude_url=exclude_url)
    if ats_link:
        return ats_link

    exclude_url_norm = (exclude_url or "").rstrip("/")
    for link in links:
        href = (link.get("href") or "").rstrip("/")
        text = link.get("text") or ""
        if not href or href == exclude_url_norm:
            continue
        if _LISTING_LINK_TEXT_RE.search(text):
            return link["href"]
    return None
