"""Resume Analyzer Agent.

Responsibility: turn an uploaded resume file into a structured CandidateProfile.
Does not invent information — fields not found in the resume are left null/empty.
"""
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Candidate
from app.models.schemas import CandidateProfile
from app.services import resume_parser
from app.services.llm_client import extract_candidate_profile


class ResumeAnalyzerAgent:
    def analyze(self, db: Session, filename: str, content: bytes) -> Candidate:
        raw_text = resume_parser.extract_text(filename, content)
        if not raw_text.strip():
            raise ValueError(
                "No extractable text found in this resume. It may be a scanned/image-based "
                "file, which is not currently supported."
            )

        storage_path = self._save_file(filename, content)

        extracted = extract_candidate_profile(raw_text)
        profile = CandidateProfile.model_validate(extracted)

        candidate = Candidate(
            resume_filename=filename,
            resume_storage_path=str(storage_path),
            raw_text=raw_text,
            profile_json=profile.model_dump_json(),
            state="RESUME_ANALYZED",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    @staticmethod
    def _save_file(filename: str, content: bytes) -> Path:
        storage_dir = Path(settings.resume_storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix
        unique_name = f"{uuid.uuid4()}{suffix}"
        path = storage_dir / unique_name
        path.write_bytes(content)
        return path
