"""Additional job source via Apify — LinkedIn Jobs.

Unlike the direct-ATS discovery in job_discovery_agent.py (which renders each company's own
careers page), this is a third-party job board reached via a real, well-established public
actor on the Apify store (verified against its store page and, live, against real API
responses before being wired in — not guessed):

  LinkedIn: curious_coder/linkedin-jobs-scraper (~138K users)

(Indeed and Naukri were both intentionally removed — both sites block automated browser access,
which meant their results couldn't be independently re-verified as real, specific job pages the
way LinkedIn's could. LinkedIn is the only source here that's been directly confirmed to lead to
a genuine job description + apply page.)

Entirely opt-in: if APIFY_API_TOKEN is unset, fetch_apify_jobs() returns an empty list
immediately — no network call, no cost, no error. The actor is billed per result by Apify, so
settings.apify_max_items_per_source is kept low by default.

Each actor already returns the full job description in one call (unlike the ATS listing pages,
which need a second visit to each job's own detail page) — so results here are ready to store
directly, no separate detail-fetch step needed.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger("apify_client")

_RUN_SYNC_URL = "https://api.apify.com/v2/actors/{actor}/run-sync-get-dataset-items"


def _flatten_text(value) -> str | None:
    """Actor fields documented as strings sometimes come back as a list — every DB column here
    is a plain string, so normalize rather than pass the raw type through and let it fail at
    insert time."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v) or None
    return str(value)


async def _run_actor(client: httpx.AsyncClient, actor: str, payload: dict) -> list[dict]:
    url = _RUN_SYNC_URL.format(actor=actor)
    resp = await client.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {settings.apify_api_token}"},
        timeout=120.0,  # a real actor run (a real scrape), not a plain API call
    )
    resp.raise_for_status()
    return resp.json()


async def _fetch_linkedin(client: httpx.AsyncClient, query: str, location: str) -> list[dict]:
    items = await _run_actor(client, settings.apify_linkedin_actor, {
        "keywords": query,
        "location": location or "",
        "limitPerSource": settings.apify_max_items_per_source,
    })
    jobs = []
    for item in items:
        title = item.get("title")
        apply_url = item.get("link")
        if not title or not apply_url:
            continue
        jobs.append({
            "source": "linkedin",
            "company_name": _flatten_text(item.get("companyName")) or "Unknown",
            "title": _flatten_text(title),
            "location": _flatten_text(item.get("location")),
            "work_mode": None,
            "date_posted": _flatten_text(item.get("postedAt")),
            "employment_type": _flatten_text(item.get("employmentType")),
            "responsibilities": _flatten_text(item.get("descriptionText")),
            "job_url": apply_url,
        })
    return jobs


async def fetch_apify_jobs(query: str, location: str) -> tuple[list[dict], dict[str, str]]:
    """Returns (jobs, errors). errors maps source name -> error message for any source that
    failed, so the caller can report honestly rather than silently returning fewer jobs."""
    if not settings.apify_api_token or not query:
        return [], {}

    sources = {"linkedin": _fetch_linkedin}
    jobs: list[dict] = []
    errors: dict[str, str] = {}

    async with httpx.AsyncClient() as client:
        for name, fetcher in sources.items():
            try:
                jobs.extend(await fetcher(client, query, location))
            except (httpx.HTTPStatusError, httpx.RequestError, ValueError, KeyError) as e:
                logger.warning("Apify source '%s' failed: %s", name, e)
                errors[name] = str(e)

    return jobs, errors
