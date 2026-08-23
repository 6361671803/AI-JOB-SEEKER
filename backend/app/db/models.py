import uuid
from datetime import date as dt_date
from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    """Stores one uploaded resume: raw extracted text plus the structured profile."""

    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    resume_filename: Mapped[str] = mapped_column(String)
    resume_storage_path: Mapped[str] = mapped_column(String)
    raw_text: Mapped[str] = mapped_column(Text)
    profile_json: Mapped[str] = mapped_column(Text)  # CandidateProfile, JSON-serialized
    preferences_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # UserPreferences, JSON-serialized
    state: Mapped[str] = mapped_column(String, default="RESUME_UPLOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Company(Base):
    """A company discovered by the Company Career Discovery Agent for a given candidate's search."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    careers_url: Mapped[str | None] = mapped_column(String, nullable=True)
    discovery_role: Mapped[str | None] = mapped_column(String, nullable=True)
    discovery_location: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Job(Base):
    """A job listing discovered by the Job Discovery Agent on a company's careers page."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(String, index=True)
    company_id: Mapped[str] = mapped_column(String, index=True)
    company_name: Mapped[str] = mapped_column(String)

    title: Mapped[str] = mapped_column(String)
    job_id_external: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    date_posted: Mapped[str | None] = mapped_column(String, nullable=True)  # raw text as scraped
    posted_date_parsed: Mapped[dt_date | None] = mapped_column(Date, nullable=True)  # resolved date, for filtering
    closing_date: Mapped[str | None] = mapped_column(String, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    experience_requirement: Mapped[str | None] = mapped_column(String, nullable=True)
    education_requirement: Mapped[str | None] = mapped_column(String, nullable=True)
    required_skills_json: Mapped[str] = mapped_column(Text, default="[]")
    preferred_skills_json: Mapped[str] = mapped_column(Text, default="[]")
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_url: Mapped[str | None] = mapped_column(String, nullable=True)
    application_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Tracker status: DISCOVERED, MATCHED, SELECTED, PREPARING, WAITING_FOR_REVIEW, SUBMITTED, FAILED.
    status: Mapped[str] = mapped_column(String, default="DISCOVERED")

    # Resume/Job Matching Agent output (Phase 6) — null until matched.
    overall_score: Mapped[int | None] = mapped_column(nullable=True)
    skills_score: Mapped[int | None] = mapped_column(nullable=True)
    education_score: Mapped[int | None] = mapped_column(nullable=True)
    experience_score: Mapped[int | None] = mapped_column(nullable=True)
    role_score: Mapped[int | None] = mapped_column(nullable=True)
    location_score: Mapped[int | None] = mapped_column(nullable=True)
    semantic_score: Mapped[int | None] = mapped_column(nullable=True)  # TF-IDF cosine similarity, resume vs. job text
    matched_required_skills_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_required_skills_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_preferred_skills_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_preferred_skills_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant_projects_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_issues_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_match_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_this_matches: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Application Preparation Agent output (Phase 9) — null until prepared.
    application_platform: Mapped[str | None] = mapped_column(String, nullable=True)
    prepared_fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    prepared_fields_completed: Mapped[int | None] = mapped_column(nullable=True)
    prepared_fields_needs_review: Mapped[int | None] = mapped_column(nullable=True)
    preparation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String, nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Final review / submission tracking (Phase 10) — user-provided answers are for the
    # candidate's own checklist only; this app never re-submits anything itself.
    user_provided_fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
