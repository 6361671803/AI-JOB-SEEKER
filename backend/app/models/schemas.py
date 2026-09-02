from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ExperienceEntry(BaseModel):
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None


class EducationEntry(BaseModel):
    degree: str | None = None
    institution: str | None = None
    year: str | None = None
    field_of_study: str | None = None


class ProjectEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    """Structured candidate info extracted from the resume. Unknown fields stay null — never invented."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    internships: list[ExperienceEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    years_of_experience: float | None = None


class CandidateResponse(BaseModel):
    id: str
    resume_filename: str
    state: str
    profile: CandidateProfile


class WorkMode(str, Enum):
    INDIA = "INDIA"
    REMOTE = "REMOTE"
    BOTH = "BOTH"


class ExperienceLevel(str, Enum):
    INTERNSHIP = "Internship"
    FRESHER = "Fresher"
    ENTRY_LEVEL = "Entry Level"
    ZERO_TO_TWO = "0-2 years"
    TWO_TO_FIVE = "2-5 years"
    FIVE_PLUS = "5+ years"
    ANY = "Any"


class PreferenceInput(BaseModel):
    """Raw preferences as submitted by the user (Step 2 of the workflow)."""

    work_mode: WorkMode
    cities: list[str] = Field(default_factory=list)
    experience_level: ExperienceLevel
    preferred_role: str | None = None

    @field_validator("cities")
    @classmethod
    def strip_and_dedupe_cities(cls, cities: list[str]) -> list[str]:
        cleaned = [c.strip() for c in cities if c and c.strip()]
        seen: list[str] = []
        for c in cleaned:
            if c.lower() not in [s.lower() for s in seen]:
                seen.append(c)
        return seen

    @field_validator("preferred_role")
    @classmethod
    def blank_role_is_none(cls, role: str | None) -> str | None:
        if role is None:
            return None
        role = role.strip()
        return role or None


class UserPreferences(PreferenceInput):
    """Preferences plus roles resolved by the Preference Agent (explicit or inferred)."""

    inferred_roles: list[str] = Field(default_factory=list)
    role_source: str = "user"  # "user" | "inferred_from_resume"


class PreferenceResponse(BaseModel):
    candidate_id: str
    state: str
    preferences: UserPreferences


class DiscoveredCompany(BaseModel):
    id: str
    name: str
    website: str | None = None
    careers_url: str | None = None
    discovery_role: str | None = None
    discovery_location: str | None = None


class CompanyDiscoveryResponse(BaseModel):
    candidate_id: str
    state: str
    companies: list[DiscoveredCompany]


class MatchBreakdown(BaseModel):
    skills_score: int
    semantic_score: int
    education_score: int
    experience_score: int
    role_score: int
    location_score: int


class JobMatch(BaseModel):
    overall_score: int
    breakdown: MatchBreakdown
    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    relevant_projects: list[str] = Field(default_factory=list)
    eligibility_issues: list[str] = Field(default_factory=list)
    location_match_reasoning: str
    education_reasoning: str
    experience_reasoning: str
    role_reasoning: str
    why_this_matches: str


class DiscoveredJob(BaseModel):
    id: str
    company_id: str
    company_name: str
    title: str
    job_id_external: str | None = None
    location: str | None = None
    work_mode: str | None = None
    date_posted: str | None = None
    posted_date_parsed: str | None = None
    closing_date: str | None = None
    employment_type: str | None = None
    experience_requirement: str | None = None
    education_requirement: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: str | None = None
    qualifications: str | None = None
    job_url: str | None = None
    application_url: str | None = None
    status: str = "DISCOVERED"
    match: JobMatch | None = None


class JobDiscoveryResponse(BaseModel):
    candidate_id: str
    state: str
    window_days: int
    recent_jobs: list[DiscoveredJob]
    unknown_date_jobs: list[DiscoveredJob]
    older_jobs_count: int
    companies_skipped: list[str] = Field(default_factory=list)


class SelectJobsInput(BaseModel):
    job_ids: list[str] = Field(default_factory=list)


class ApprovalResponse(BaseModel):
    candidate_id: str
    state: str
    selected_count: int


class PreparedField(BaseModel):
    label: str
    field_type: str | None = None
    value: str | None = None
    source: str | None = None
    filled: bool = False


class ApplicationPreparation(BaseModel):
    job_id: str
    company_name: str
    title: str
    application_url: str | None = None
    platform: str
    status: str  # WAITING_FOR_REVIEW | FAILED (SUBMITTED is historical only)
    message: str
    fields: list[PreparedField] = Field(default_factory=list)
    fields_completed: int = 0
    fields_needs_review: int = 0
    screenshot_available: bool = False


class ReviewFieldUpdateInput(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)  # label -> user-provided value


class TrackerEntry(BaseModel):
    job_id: str
    company_name: str
    title: str
    job_id_external: str | None = None
    match_score: int | None = None
    date_found: str
    date_posted: str | None = None
    application_date: str | None = None
    status: str
    job_url: str | None = None
    application_url: str | None = None


class TrackerResponse(BaseModel):
    candidate_id: str
    entries: list[TrackerEntry]
    status_counts: dict[str, int] = Field(default_factory=dict)
