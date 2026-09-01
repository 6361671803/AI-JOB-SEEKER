"""Application Preparation Agent.

Responsibility: for a single SELECTED job, open its official application page in a real browser,
detect which ATS hosts it (informational only), and take a screenshot so the user has a visual
record of the page before they apply. It never inspects or fills in any form fields.

HARD REQUIREMENT: this agent never submits anything, and never touches a form field. There is no
code path anywhere in this agent or in browser_client.prepare_application_page that fills a field
or clicks a submit button. It always stops and hands the user the official URL for them to
complete and submit the application themselves.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Candidate, Job
from app.services.ats_detector import detect_platform
from app.services.browser_client import BrowserFetchError, prepare_application_page


class ApplicationPreparationAgent:
    def prepare(self, db: Session, candidate: Candidate, job: Job) -> Job:
        if job.status not in ("SELECTED", "WAITING_FOR_REVIEW", "FAILED"):
            raise ValueError("Job must be selected before its application can be prepared.")

        target_url = job.application_url or job.job_url

        if not target_url:
            self._fail(db, job, "No official application URL was found for this job during discovery.")
            return job

        job.status = "PREPARING"
        db.add(job)
        db.commit()

        job.application_platform = detect_platform(target_url)

        screenshot_dir = Path(settings.screenshot_storage_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(screenshot_dir / f"{job.id}.png")

        try:
            prepare_application_page(target_url, screenshot_path)
        except BrowserFetchError as e:
            self._fail(db, job, f"Could not open the application page: {e}")
            return job

        job.screenshot_path = screenshot_path if Path(screenshot_path).exists() else None

        message = "Official application page opened below. Please review it and complete the application yourself using the link."
        self._stop_for_review(db, job, message=message, fields=[])
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
