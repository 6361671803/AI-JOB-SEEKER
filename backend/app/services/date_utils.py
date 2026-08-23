"""Parses the free-text "date_posted" strings scraped from job pages (e.g. "3 days ago",
"2026-08-01", "Posted today") into real dates, so the 30-day filter has something to compare
against. Returns None whenever the text can't be confidently parsed — callers must treat that as
"posting date unavailable", never as "recent".
"""
import re
from datetime import date, timedelta

_RELATIVE_PATTERN = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>hour|hours|day|days|week|weeks|month|months|year|years)\s*ago",
    re.IGNORECASE,
)

_UNIT_TO_DAYS = {
    "hour": 0, "hours": 0,
    "day": 1, "days": 1,
    "week": 7, "weeks": 7,
    "month": 30, "months": 30,
    "year": 365, "years": 365,
}


def parse_posted_date(raw: str | None, reference_date: date) -> date | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip().lower()

    if text in ("today", "just posted", "posted today", "new"):
        return reference_date
    if text == "yesterday":
        return reference_date - timedelta(days=1)

    match = _RELATIVE_PATTERN.search(text)
    if match:
        n = int(match.group("num"))
        unit_days = _UNIT_TO_DAYS[match.group("unit").lower()]
        return reference_date - timedelta(days=n * unit_days)

    try:
        from dateutil import parser as dateutil_parser

        parsed = dateutil_parser.parse(raw.strip())
        parsed_date = parsed.date()
        # Guard against dateutil silently inventing a year/month for partial/ambiguous input
        # (e.g. it defaults missing fields to today's date) — only trust dates that don't land
        # implausibly in the future relative to the reference.
        if parsed_date > reference_date + timedelta(days=1):
            return None
        return parsed_date
    except (ValueError, OverflowError, TypeError):
        return None
