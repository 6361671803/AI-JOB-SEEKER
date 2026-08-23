"""Company Career Discovery Agent.

Responsibility: given the candidate's target roles and location preference, find real companies
and, where possible, their official website + official careers page. Never fabricates a company
or a URL — everything must trace back to an actual web search result.
"""
import json
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.db.models import Candidate, Company
from app.services.llm_client import extract_company_names, resolve_official_career_page
from app.services.search_client import SearchRequestError, web_search

MAX_ROLES_SEARCHED = 2
MAX_LOCATIONS_SEARCHED = 3
MAX_COMPANIES = 25

# Deterministic backstop, independent of LLM prompt compliance: place names and generic
# administrative-body words that have leaked through as "company names" in real runs (e.g. a
# search result mentioning "...jobs in Hyderabad, Telangana" caused the LLM to extract
# "Hyderabad" and "Telangana" as if they were employers). Not an exhaustive gazetteer — just a
# bounded, practical list covering the terms most likely to appear in an India-focused job search.
_INDIAN_STATES_AND_UTS = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat",
    "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh",
    "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal", "delhi", "chandigarh", "puducherry", "ladakh",
    "jammu and kashmir", "andaman and nicobar islands", "dadra and nagar haveli",
    "daman and diu", "lakshadweep",
}
_GENERIC_LOCATION_TERMS = {
    "india", "remote", "remote / work from home", "work from home", "hyderabad", "bangalore",
    "bengaluru", "mumbai", "delhi", "chennai", "pune", "kolkata", "noida", "gurgaon", "gurugram",
    "ahmedabad", "usa", "united states", "united kingdom", "uk", "canada", "singapore",
}
_ADMINISTRATIVE_BODY_KEYWORDS = (
    "public service commission", "staff selection commission", "recruitment board",
    "department of", "ministry of", "government of",
)


def _is_place_or_administrative_body(name: str) -> bool:
    key = name.strip().lower()
    if key in _INDIAN_STATES_AND_UTS or key in _GENERIC_LOCATION_TERMS:
        return True
    return any(kw in key for kw in _ADMINISTRATIVE_BODY_KEYWORDS)


class CompanyDiscoveryAgent:
    def discover(self, db: Session, candidate: Candidate) -> list[Company]:
        if not candidate.preferences_json:
            raise ValueError("Preferences must be collected before discovering companies.")

        preferences = json.loads(candidate.preferences_json)
        roles = self._target_roles(preferences)
        locations = self._location_terms(preferences)

        name_meta: dict[str, tuple[str, str, str]] = {}  # lower(name) -> (name, role, location)
        queries_attempted = 0
        queries_failed = 0
        last_error: str | None = None

        for role in roles[:MAX_ROLES_SEARCHED]:
            for location in locations[:MAX_LOCATIONS_SEARCHED]:
                if len(name_meta) >= MAX_COMPANIES:
                    break
                query = f"companies currently hiring {role} in {location}"
                queries_attempted += 1
                try:
                    results = web_search(query, max_results=10)
                    names = extract_company_names(results, role, location)
                except SearchRequestError as e:
                    # One failed query shouldn't stop the whole discovery run — but if every
                    # query fails (e.g. an expired/invalid search API key), that's a systemic
                    # problem the user needs to know about, not a silent "0 companies found".
                    queries_failed += 1
                    last_error = str(e)
                    continue

                for name in names:
                    key = name.strip().lower()
                    if not key or key in name_meta:
                        continue
                    if key == location.strip().lower():
                        continue
                    if _is_place_or_administrative_body(name):
                        continue
                    name_meta[key] = (name.strip(), role, location)
            if len(name_meta) >= MAX_COMPANIES:
                break

        if queries_attempted > 0 and queries_failed == queries_attempted:
            raise SearchRequestError(
                f"All {queries_attempted} company searches failed — the search provider may be "
                f"misconfigured or its API key may be invalid/expired. Last error: {last_error}"
            )

        company_entries = list(name_meta.values())[:MAX_COMPANIES]

        # Re-running discovery for the same candidate replaces the previous result set.
        db.query(Company).filter(Company.candidate_id == candidate.id).delete()

        companies: list[Company] = []
        for name, role, location in company_entries:
            website, careers_url = self._resolve_urls(name)

            company = Company(
                candidate_id=candidate.id,
                name=name,
                website=website,
                careers_url=careers_url,
                discovery_role=role,
                discovery_location=location,
            )
            db.add(company)
            companies.append(company)

        candidate.state = "COMPANIES_DISCOVERED"
        db.add(candidate)
        db.commit()
        for c in companies:
            db.refresh(c)
        return companies

    @staticmethod
    def _resolve_urls(name: str) -> tuple[str | None, str | None]:
        """Resolves (website, careers_url) for a company — real URLs only, with two accuracy
        improvements over a single search: deriving the website from the careers URL's own
        domain when a separate website result wasn't found, and retrying with a differently
        worded query if the first attempt found neither."""
        website, careers_url = None, None
        try:
            results = web_search(f"{name} official careers page", max_results=5)
            website, careers_url = resolve_official_career_page(name, results)
        except SearchRequestError:
            pass  # keep the company with unresolved URLs rather than dropping it

        if not website and not careers_url:
            # First query came up empty — try a differently worded query before giving up.
            try:
                results = web_search(f"{name} official company website", max_results=5)
                website, careers_url = resolve_official_career_page(name, results)
            except SearchRequestError:
                pass

        if not website and careers_url:
            # Derive the root domain from the careers URL we already validated — not a new
            # fact, just a transformation of a real URL we already have in hand.
            parsed = urlparse(careers_url)
            if parsed.scheme and parsed.netloc:
                website = f"{parsed.scheme}://{parsed.netloc}"

        return website, careers_url

    @staticmethod
    def _target_roles(preferences: dict) -> list[str]:
        if preferences.get("preferred_role"):
            return [preferences["preferred_role"]]
        return [r for r in preferences.get("inferred_roles", []) if r] or ["suitable roles for this candidate"]

    @staticmethod
    def _location_terms(preferences: dict) -> list[str]:
        mode = preferences.get("work_mode")
        cities = [c for c in preferences.get("cities", []) if c]
        if mode == "REMOTE":
            return ["remote / work from home"]
        if mode == "INDIA":
            return cities or ["India"]
        if mode == "BOTH":
            return (cities or ["India"]) + ["remote / work from home"]
        return ["India"]
