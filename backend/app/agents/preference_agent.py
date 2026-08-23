"""User Preference Agent.

Responsibility: collect the user's work-location/city/experience/role preferences and,
when no role is given, infer suitable roles from the resume (never inventing new skills —
only reasoning over what the Resume Analyzer Agent already extracted).
"""
import json

from sqlalchemy.orm import Session

from app.db.models import Candidate
from app.models.schemas import PreferenceInput, UserPreferences
from app.services.llm_client import infer_target_roles


class PreferenceAgent:
    def collect(self, db: Session, candidate: Candidate, payload: PreferenceInput) -> Candidate:
        cities = [] if payload.work_mode.value == "REMOTE" else payload.cities

        if payload.preferred_role:
            inferred_roles: list[str] = []
            role_source = "user"
        else:
            profile = json.loads(candidate.profile_json)
            inferred_roles = infer_target_roles(profile, payload.experience_level.value)
            role_source = "inferred_from_resume"

        preferences = UserPreferences(
            work_mode=payload.work_mode,
            cities=cities,
            experience_level=payload.experience_level,
            preferred_role=payload.preferred_role,
            inferred_roles=inferred_roles,
            role_source=role_source,
        )

        candidate.preferences_json = preferences.model_dump_json()
        candidate.state = "PREFERENCES_COLLECTED"
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate
