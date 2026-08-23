"""Resume/Job Matching Agent.

Responsibility: for every discovered job, compare it against the candidate's resume and produce
an explainable 0-100 score with a breakdown. Skills and location matching are deterministic (pure
string/preference comparison) since those claims are safety-critical; semantic match is a real
embedding-based cosine-similarity signal (see semantic_matcher.py) over the full resume vs. job
text, computed in one batched call for the whole run; education/experience/role fit and
eligibility notes come from a single grounded LLM call per job (see llm_client.py).
"""
import json

from sqlalchemy.orm import Session

from app.db.models import Candidate, Job
from app.services.llm_client import LLMRequestError, assess_job_match
from app.services.semantic_matcher import compute_semantic_scores
from app.services.skill_matcher import compute_skills_score, find_matches

VERDICT_SCORE = {"meets": 100, "partial": 60, "does_not_meet": 10, "unclear": 50}
ROLE_SCORE = {"strong": 100, "moderate": 60, "weak": 20}

# Used when a semantic score is available for a job (the normal case when LLM_PROVIDER=gemini).
WEIGHTS = {
    "skills": 0.30, "semantic": 0.20, "education": 0.10,
    "experience": 0.15, "role": 0.10, "location": 0.15,
}
# Falls back to this (the original formula) for a job whose semantic score is unavailable —
# never silently treats a missing score as 0, which would unfairly tank that job's ranking.
WEIGHTS_NO_SEMANTIC = {
    "skills": 0.35, "education": 0.15, "experience": 0.20, "role": 0.15, "location": 0.15,
}


class MatchingAgent:
    def match(self, db: Session, candidate: Candidate) -> list[Job]:
        jobs = db.query(Job).filter(Job.candidate_id == candidate.id).all()
        if not jobs:
            raise ValueError("No jobs discovered yet. Run job discovery first.")

        profile = json.loads(candidate.profile_json)
        preferences = json.loads(candidate.preferences_json) if candidate.preferences_json else {}
        candidate_terms = profile.get("skills", []) + profile.get("technologies", [])
        project_names = {p.get("name") for p in profile.get("projects", []) if p.get("name")}

        job_dicts = [
            (
                {
                    "title": j.title,
                    "education_requirement": j.education_requirement,
                    "experience_requirement": j.experience_requirement,
                    "responsibilities": j.responsibilities,
                    "qualifications": j.qualifications,
                },
                json.loads(j.required_skills_json),
                json.loads(j.preferred_skills_json),
            )
            for j in jobs
        ]
        semantic_scores = compute_semantic_scores(profile, job_dicts)

        for job, semantic_score in zip(jobs, semantic_scores):
            self._match_one(db, job, profile, preferences, candidate_terms, project_names, semantic_score)

        candidate.state = "JOBS_RANKED"
        db.add(candidate)
        db.commit()
        for j in jobs:
            db.refresh(j)

        jobs.sort(key=lambda j: (j.overall_score is None, -(j.overall_score or 0)))
        return jobs

    def _match_one(
        self, db: Session, job: Job, profile: dict, preferences: dict,
        candidate_terms: list[str], project_names: set[str], semantic_score: int | None,
    ) -> None:
        required = json.loads(job.required_skills_json)
        preferred = json.loads(job.preferred_skills_json)
        matched_required, missing_required = find_matches(required, candidate_terms)
        matched_preferred, missing_preferred = find_matches(preferred, candidate_terms)
        skills_score = compute_skills_score(matched_required, missing_required, matched_preferred, missing_preferred)
        location_score, location_reasoning = self._compute_location_match(preferences, job)

        job_dict = {
            "title": job.title,
            "education_requirement": job.education_requirement,
            "experience_requirement": job.experience_requirement,
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications,
        }

        try:
            assessment = assess_job_match(profile, preferences, job_dict, matched_required, matched_preferred)
        except LLMRequestError:
            assessment = {}  # degrade gracefully — deterministic scores still apply

        education_verdict = assessment.get("education_verdict", "unclear")
        experience_verdict = assessment.get("experience_verdict", "unclear")
        role_relevance = assessment.get("role_relevance", "moderate")

        education_score = VERDICT_SCORE.get(education_verdict, 50)
        experience_score = VERDICT_SCORE.get(experience_verdict, 50)
        role_score = ROLE_SCORE.get(role_relevance, 50)

        relevant_projects = [p for p in assessment.get("relevant_projects", []) if p in project_names]
        eligibility_issues = assessment.get("eligibility_issues", [])

        if semantic_score is not None:
            overall = round(
                WEIGHTS["skills"] * skills_score
                + WEIGHTS["semantic"] * semantic_score
                + WEIGHTS["education"] * education_score
                + WEIGHTS["experience"] * experience_score
                + WEIGHTS["role"] * role_score
                + WEIGHTS["location"] * location_score
            )
        else:
            overall = round(
                WEIGHTS_NO_SEMANTIC["skills"] * skills_score
                + WEIGHTS_NO_SEMANTIC["education"] * education_score
                + WEIGHTS_NO_SEMANTIC["experience"] * experience_score
                + WEIGHTS_NO_SEMANTIC["role"] * role_score
                + WEIGHTS_NO_SEMANTIC["location"] * location_score
            )

        job.status = "MATCHED"
        job.overall_score = overall
        job.skills_score = skills_score
        job.semantic_score = semantic_score
        job.education_score = education_score
        job.experience_score = experience_score
        job.role_score = role_score
        job.location_score = location_score
        job.matched_required_skills_json = json.dumps(matched_required)
        job.missing_required_skills_json = json.dumps(missing_required)
        job.matched_preferred_skills_json = json.dumps(matched_preferred)
        job.missing_preferred_skills_json = json.dumps(missing_preferred)
        job.relevant_projects_json = json.dumps(relevant_projects)
        job.eligibility_issues_json = json.dumps(eligibility_issues)
        job.location_match_reasoning = location_reasoning
        job.education_reasoning = assessment.get("education_reasoning") or \
            "Job posting did not state an education requirement."
        job.experience_reasoning = assessment.get("experience_reasoning") or \
            "Job posting did not state an experience requirement."
        job.role_reasoning = assessment.get("role_reasoning") or \
            "Role relevance could not be assessed (LLM unavailable)."
        job.why_this_matches = assessment.get("why_this_matches") or \
            self._fallback_why(matched_required, matched_preferred)
        db.add(job)

    @staticmethod
    def _fallback_why(matched_required: list[str], matched_preferred: list[str]) -> str:
        parts = []
        if matched_required:
            parts.append(f"Your resume shows {', '.join(matched_required[:5])}, matching this role's required skills.")
        if matched_preferred:
            parts.append(f"You also have {', '.join(matched_preferred[:3])}, listed as preferred.")
        return " ".join(parts) or "Limited overlap was found between your resume and this job's listed requirements."

    @staticmethod
    def _compute_location_match(preferences: dict, job: Job) -> tuple[int, str]:
        work_mode_pref = preferences.get("work_mode")
        cities = [c.lower() for c in preferences.get("cities", [])]
        job_location = (job.location or "").lower()
        job_work_mode = (job.work_mode or "").lower()
        is_remote_job = "remote" in job_work_mode or "remote" in job_location

        if work_mode_pref == "REMOTE":
            if is_remote_job:
                return 100, "Job is explicitly remote, matching your remote preference."
            if not job.work_mode and not job.location:
                return 50, "Job's location/work mode wasn't stated — could not confirm remote compatibility."
            return 20, (
                f"You're looking for remote work, but this job is listed as "
                f"{job.location or 'a fixed location'} ({job.work_mode or 'work mode unspecified'})."
            )

        if work_mode_pref == "INDIA":
            if is_remote_job:
                return 70, "Job is remote, which is location-flexible, though your preference was India-based cities."
            if not cities:
                return (80, "Job has a stated location; you didn't restrict to specific cities.") if job_location \
                    else (50, "Job location wasn't stated — could not confirm it's in India.")
            if any(city in job_location for city in cities):
                return 100, f"Job location ({job.location}) matches one of your preferred cities."
            if job_location:
                return 30, f"Job location ({job.location}) doesn't match your preferred cities."
            return 50, "Job location wasn't stated — could not confirm a city match."

        if work_mode_pref == "BOTH":
            if is_remote_job:
                return 100, "Job is remote, matching your openness to remote work."
            if cities and any(city in job_location for city in cities):
                return 100, f"Job location ({job.location}) matches one of your preferred cities."
            if job_location:
                return 50, f"Job location ({job.location}) is neither remote nor one of your preferred cities."
            return 50, "Job location/work mode wasn't stated — could not confirm compatibility."

        return 50, "Location preference not set — could not assess location match."
