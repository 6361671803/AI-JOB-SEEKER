"""Application Preparation Agent (with the Browser Automation Agent's logic folded in).

Responsibility: for a single SELECTED job, open its official application page, detect which ATS
hosts it, and — if the platform is reliably automatable and no CAPTCHA/login blocker is present —
fill in what can be confidently resolved from the resume. Takes a screenshot as proof of what was
filled, then closes the browser.

HARD REQUIREMENT: this agent never submits anything. There is no code path anywhere in this
agent or in browser_client.prepare_application_page that clicks a submit button. It always stops
and hands the user the official URL plus a field-by-field summary for their own review.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Candidate, Job
from app.services.ats_detector import NOT_RELIABLY_AUTOMATABLE, detect_platform
from app.services.browser_client import BrowserFetchError, prepare_application_page


class ApplicationPreparationAgent:
    def prepare(self, db: Session, candidate: Candidate, job: Job) -> Job:
        if job.status not in ("SELECTED", "WAITING_FOR_REVIEW", "FAILED"):
            raise ValueError("Job must be selected before its application can be prepared.")

        profile = json.loads(candidate.profile_json)
        preferences = json.loads(candidate.preferences_json) if candidate.preferences_json else {}
        target_url = job.application_url or job.job_url

        if not target_url:
            self._fail(db, job, "No official application URL was found for this job during discovery.")
            return job

        job.status = "PREPARING"
        db.add(job)
        db.commit()

        platform = detect_platform(target_url)
        job.application_platform = platform

        if platform in NOT_RELIABLY_AUTOMATABLE:
            self._stop_for_review(
                db, job,
                message=(
                    f"{platform.title()} application forms are typically multi-step and often "
                    "require account creation, so this agent doesn't attempt to auto-fill them. "
                    "Please open the official link below and apply directly."
                ),
                fields=[],
            )
            return job

        screenshot_dir = Path(settings.screenshot_storage_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(screenshot_dir / f"{job.id}.png")

        try:
            result = prepare_application_page(
                target_url, profile, preferences, candidate.resume_storage_path, screenshot_path
            )
        except BrowserFetchError as e:
            self._fail(db, job, f"Could not open the application page: {e}")
            return job

        job.screenshot_path = screenshot_path if Path(screenshot_path).exists() else None

        if result["blockers"]:
            self._stop_for_review(
                db, job,
                message=(
                    "Manual action required: " + "; ".join(result["blockers"]) + ". The agent stopped "
                    "without filling any fields — please complete this step yourself using the "
                    "official link below."
                ),
                fields=[],
            )
            return job

        fields = result["fields"]
        completed = sum(1 for f in fields if f["filled"])
        needs_review = len(fields) - completed
        message = (
            f"Filled {completed} of {len(fields)} detected fields from your resume. "
            f"{needs_review} field(s) need your review before you submit."
        ) if fields else "No fillable form fields were detected on this page."

        self._stop_for_review(db, job, message=message, fields=fields)
        return job

    @staticmethod
    def _stop_for_review(db: Session, job: Job, message: str, fields: list[dict]) -> None:
        completed = sum(1 for f in fields if f["filled"])
        job.status = "WAITING_FOR_REVIEW"
        job.preparation_message = message
        job.prepared_fields_json = json.dumps(fields)
        job.prepared_fields_completed = completed
        job.prepared_fields_needs_review = len(fields) - completed
        job.prepared_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        db.refresh(job)

    @staticmethod
    def _fail(db: Session, job: Job, message: str) -> None:
        job.status = "FAILED"
        job.preparation_message = message
        job.prepared_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        db.refresh(job)
