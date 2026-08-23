"""Job Discovery Agent.

Responsibility: for each company discovered with a known official careers page, render that page
with a real browser (many career sites are JS-rendered SPAs) and find current job listings. Then,
for each listing with a known URL, visit its own detail page to extract the actual description
(requirements/qualifications/skills) — those fields genuinely live on the detail page, not the
listing page, so extracting them there keeps the model grounded instead of guessing.

Never fabricates a listing or a URL — everything must trace back to a rendered page.
"""
import asyncio
import json
import logging
import time
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Candidate, Company, Job
from app.services.apify_client import fetch_apify_jobs
from app.services.ats_detector import find_secondary_listing_link
from app.services.browser_client import BrowserFetchError, fetch_rendered_page
from app.services.date_utils import parse_posted_date
from app.services.llm_client import (
    LLMRequestError,
    extract_job_description,
    extract_job_listings,
)

# Local CPU inference is slow (~minutes per page for a complex schema), so these caps keep a
# single discovery run to a bounded wall-clock time. Raised to cover every discovered company
# (up to company_discovery_agent's own MAX_COMPANIES=25) at the user's request — a full run at
# this size can take a long time on local CPU inference.
MAX_COMPANIES_SCRAPED = 25
MAX_JOBS_TOTAL = 60

logger = logging.getLogger("job_discovery_agent")

# Companies are scraped one at a time, deliberately not in parallel. A ThreadPoolExecutor-based
# version was tried and reverted: Playwright's sync API proved unreliable under concurrent
# threads on this setup (a real 30+ minute hang was observed, not just slowness), and even before
# that, concurrent LLM calls all draw from one shared rate-limit budget (e.g. Gemini free tier's
# 15 requests/minute total, not per company) — so concurrency there doesn't add real throughput,
# it just causes contention. Sequential is slower (5-11 min for ~25 companies) but reliable.


class JobDiscoveryAgent:
    def discover(self, db: Session, candidate: Candidate) -> tuple[list[Job], list[str]]:
        companies = db.query(Company).filter(Company.candidate_id == candidate.id).all()
        if not companies:
            raise ValueError("No companies discovered yet. Run company discovery first.")

        scrapeable = [c for c in companies if c.careers_url]
        skipped = [c.name for c in companies if not c.careers_url]

        db.query(Job).filter(Job.candidate_id == candidate.id).delete()

        jobs: list[Job] = []
        companies_to_scrape = scrapeable[:MAX_COMPANIES_SCRAPED]
        run_start = time.monotonic()
        logger.info("Job discovery starting: %d companies to scrape", len(companies_to_scrape))

        for i, company in enumerate(companies_to_scrape, start=1):
            if len(jobs) >= MAX_JOBS_TOTAL:
                logger.info("Hit MAX_JOBS_TOTAL=%d, stopping early", MAX_JOBS_TOTAL)
                break

            company_start = time.monotonic()
            listings_with_details = self._process_company(company)
            elapsed = time.monotonic() - company_start
            total_elapsed = time.monotonic() - run_start

            if listings_with_details is None:
                skipped.append(company.name)
                logger.info(
                    "[%d/%d] %s: SKIPPED (unreadable) in %.1fs | total elapsed %.1fs",
                    i, len(companies_to_scrape), company.name, elapsed, total_elapsed,
                )
                continue

            logger.info(
                "[%d/%d] %s: %d listing(s) in %.1fs | total jobs so far %d | total elapsed %.1fs",
                i, len(companies_to_scrape), company.name, len(listings_with_details), elapsed,
                len(jobs), total_elapsed,
            )

            for listing, details in listings_with_details:
                if len(jobs) >= MAX_JOBS_TOTAL:
                    break

                raw_date_posted = details.get("date_posted")

                job = Job(
                    candidate_id=candidate.id,
                    company_id=company.id,
                    company_name=company.name,
                    title=listing["title"],
                    job_id_external=details.get("job_id"),
                    location=details.get("location") or listing.get("location"),
                    work_mode=details.get("work_mode") or listing.get("work_mode"),
                    date_posted=raw_date_posted,
                    posted_date_parsed=parse_posted_date(raw_date_posted, date.today()),
                    closing_date=details.get("closing_date"),
                    employment_type=details.get("employment_type"),
                    experience_requirement=details.get("experience_requirement"),
                    education_requirement=details.get("education_requirement"),
                    required_skills_json=json.dumps(details.get("required_skills", [])),
                    preferred_skills_json=json.dumps(details.get("preferred_skills", [])),
                    responsibilities=details.get("responsibilities"),
                    qualifications=details.get("qualifications"),
                    job_url=listing.get("job_url"),
                    application_url=listing.get("job_url"),
                )
                db.add(job)
                jobs.append(job)

        # Additional job-board sources via Apify (Indeed/LinkedIn/Naukri) — entirely opt-in
        # (skipped with zero cost/error if APIFY_API_TOKEN isn't set). Search-driven rather than
        # tied to a specific discovered company, so it's added once here rather than per-company.
        if len(jobs) < MAX_JOBS_TOTAL:
            query, apify_location = self._apify_query(candidate)
            if query:
                apify_listings, _apify_errors = asyncio.run(fetch_apify_jobs(query, apify_location))
                for listing in apify_listings:
                    if len(jobs) >= MAX_JOBS_TOTAL:
                        break
                    if not listing.get("title") or not listing.get("job_url"):
                        continue

                    company = self._get_or_create_company(db, candidate, listing["company_name"])
                    raw_date_posted = listing.get("date_posted")

                    job = Job(
                        candidate_id=candidate.id,
                        company_id=company.id,
                        company_name=company.name,
                        title=listing["title"],
                        location=listing.get("location"),
                        work_mode=listing.get("work_mode"),
                        date_posted=raw_date_posted,
                        posted_date_parsed=parse_posted_date(raw_date_posted, date.today()),
                        employment_type=listing.get("employment_type"),
                        experience_requirement=listing.get("experience_requirement"),
                        responsibilities=listing.get("responsibilities"),
                        job_url=listing["job_url"],
                        application_url=listing["job_url"],
                    )
                    db.add(job)
                    jobs.append(job)

        candidate.state = "JOBS_DISCOVERED"
        db.add(candidate)
        db.commit()
        for j in jobs:
            db.refresh(j)
        return jobs, skipped

    @staticmethod
    def _apify_query(candidate: Candidate) -> tuple[str | None, str]:
        """Derives (role, location) for the Apify job-board search from the candidate's own
        stated preferences — same fields Company Discovery already uses, never invented."""
        if not candidate.preferences_json:
            return None, ""
        preferences = json.loads(candidate.preferences_json)
        role = preferences.get("preferred_role") or next(
            (r for r in preferences.get("inferred_roles", []) if r), None
        )
        cities = [c for c in preferences.get("cities", []) if c]
        location = cities[0] if cities else ("Remote" if preferences.get("work_mode") == "REMOTE" else "")
        return role, location

    @staticmethod
    def _get_or_create_company(db: Session, candidate: Candidate, name: str) -> Company:
        """Reuses a Company row already discovered under this name for this candidate, or
        creates a lightweight one — Apify results are search-driven, not tied to a specific
        careers page, so website/careers_url stay unset for these."""
        existing = (
            db.query(Company)
            .filter(Company.candidate_id == candidate.id, Company.name == name)
            .first()
        )
        if existing:
            return existing
        company = Company(candidate_id=candidate.id, name=name, discovery_role="apify")
        db.add(company)
        db.flush()
        return company

    @classmethod
    def _process_company(cls, company: Company) -> list[tuple[dict, dict]] | None:
        """Runs on a worker thread: discovers this company's listings, then visits each
        listing's own detail page. Returns a list of (listing, details) pairs, or None if the
        company's careers page couldn't be read at all (distinct from "read but had zero
        listings", which returns an empty list)."""
        listings = cls._discover_listings(company)
        if listings is None:
            return None

        pairs = []
        for listing in listings:
            if not listing.get("title") or not listing.get("job_url"):
                # A job with no title, or no verified link to its own posting, can't be taken
                # to "the exact job post" — skip it rather than show a broken/missing link.
                continue
            details = cls._fetch_details(listing)
            pairs.append((listing, details))
        return pairs

    # Some "careers" landing pages are just a JS search widget or hero page with no real
    # listings in rendered markup, but link out to the actual job board (either a third-party
    # ATS like Greenhouse, or a same-site "Explore open roles" page). Follow up to this many
    # hops looking for real listings — still grounded in real rendered pages, never fabricated.
    MAX_LISTING_PAGE_HOPS = 3

    @classmethod
    def _discover_listings(cls, company: Company) -> list[dict] | None:
        """Returns the basic listings for a company's careers page, or None if it couldn't be
        read/extracted at all. An empty list means the page was genuinely read and the LLM
        confirmed no listings — distinct from None, which means the attempt failed (page
        unreachable, or the LLM call itself errored, e.g. after exhausting rate-limit retries).
        Conflating those would silently treat a failed extraction as "confirmed zero jobs" —
        exactly the bug that showed up under concurrent load hitting Gemini's rate limit."""
        url = company.careers_url
        visited: set[str] = set()
        got_confirmed_result = False
        last_listings: list[dict] = []

        for _ in range(cls.MAX_LISTING_PAGE_HOPS):
            if not url or url in visited:
                break
            visited.add(url)

            try:
                page = fetch_rendered_page(url)
            except BrowserFetchError:
                break

            try:
                listings = extract_job_listings(company.name, page["text"], page["links"])
            except LLMRequestError:
                break

            got_confirmed_result = True
            if listings:
                return listings
            last_listings = listings

            url = find_secondary_listing_link(page["links"], exclude_url=url)

        return last_listings if got_confirmed_result else None

    @staticmethod
    def _fetch_details(listing: dict) -> dict:
        """Best-effort visit to a listing's own detail page; returns {} if unavailable."""
        job_url = listing.get("job_url")
        if not job_url:
            return {}
        try:
            detail_page = fetch_rendered_page(job_url)
            return extract_job_description(listing["title"], detail_page["text"])
        except (BrowserFetchError, LLMRequestError):
            return {}
