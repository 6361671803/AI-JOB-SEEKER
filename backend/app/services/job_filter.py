"""30-day (or 7/14/60/90-day) posting-recency filter.

Splits discovered jobs into three groups instead of silently dropping anything:
- recent: confidently posted within the window — the main results.
- unknown_date: no posting date could be determined — shown separately, never claimed as recent.
- older: confidently posted outside the window — excluded from main results.
"""
from datetime import date

from app.db.models import Job

ALLOWED_WINDOW_DAYS = (7, 14, 30, 60, 90)
DEFAULT_WINDOW_DAYS = 30


def filter_jobs_by_window(jobs: list[Job], window_days: int, today: date | None = None) -> dict:
    today = today or date.today()
    cutoff = today.toordinal() - window_days

    recent, unknown_date, older = [], [], []
    for job in jobs:
        if job.posted_date_parsed is None:
            unknown_date.append(job)
        elif job.posted_date_parsed.toordinal() >= cutoff:
            recent.append(job)
        else:
            older.append(job)

    return {"recent": recent, "unknown_date": unknown_date, "older": older}
