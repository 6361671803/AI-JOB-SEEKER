"""Classifies application-form fields and resolves values from the candidate's resume.

Deterministic (no LLM) by design: matching a form field's label to a category like "email" or
"first name" is a well-defined pattern-matching problem, and getting personal-info field mapping
wrong is exactly the kind of mistake that must never come from a guess.
"""
import re

# Sensitive/free-text fields the agent must never auto-answer, even if it could guess a plausible
# value — these require the candidate's own judgment (legal status, personal pitch, etc.).
NEVER_AUTO_FILL = {"work_authorization", "cover_letter"}

FIELD_PATTERNS = [
    ("first_name", r"first\s*name"),
    ("last_name", r"last\s*name|surname"),
    ("email", r"e-?mail"),
    ("phone", r"phone|mobile(?!\s*app)|contact\s*number"),
    ("linkedin_url", r"linkedin"),
    ("github_url", r"github"),
    ("portfolio_url", r"portfolio|personal\s*website|website\b"),
    ("resume_upload", r"resume|\bcv\b"),
    ("work_authorization", r"work\s*authoriz|require.*visa|need.*sponsor|legally\s*(eligible|authorized)"),
    ("cover_letter", r"cover\s*letter"),
    ("location", r"location|current\s*city|current\s*address"),
    ("full_name", r"^\s*name\s*$|full\s*name|your\s*name"),
]


def classify_field(label: str, name: str, field_id: str, input_type: str) -> str | None:
    if input_type == "file":
        return "resume_upload"
    text = f"{label} {name} {field_id}".lower()
    for field_type, pattern in FIELD_PATTERNS:
        if re.search(pattern, text):
            return field_type
    return None


def resolve_value(field_type: str, profile: dict, preferences: dict | None) -> tuple[str | None, str]:
    """Returns (value, source). value is None if the resume/preferences don't have it."""
    preferences = preferences or {}

    if field_type == "first_name":
        name = profile.get("name")
        return (name.split()[0], "resume") if name and name.split() else (None, "missing_from_resume")

    if field_type == "last_name":
        name = profile.get("name")
        parts = name.split() if name else []
        return (" ".join(parts[1:]), "resume") if len(parts) >= 2 else (None, "missing_from_resume")

    if field_type == "full_name":
        name = profile.get("name")
        return (name, "resume") if name else (None, "missing_from_resume")

    if field_type in ("email", "phone", "linkedin_url", "github_url", "portfolio_url"):
        value = profile.get(field_type)
        return (value, "resume") if value else (None, "missing_from_resume")

    if field_type == "location":
        locations = profile.get("locations") or []
        cities = preferences.get("cities") or []
        if locations:
            return locations[0], "resume"
        if cities:
            return cities[0], "your_stated_preference"
        return None, "missing_from_resume"

    return None, "unsupported_field_type"
