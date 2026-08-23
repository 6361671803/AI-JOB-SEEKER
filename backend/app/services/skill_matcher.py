"""Deterministic (non-LLM) skill/technology matching.

Whether a resume "has" a skill a job requires is safety-critical — job seekers act on these
claims — so this is plain string comparison, not an LLM guess. Zero hallucination risk by
construction: a skill is only ever reported "matched" if it's a real substring/whole-word overlap
with something literally in the candidate's resume-derived skills/technologies.
"""
import re


def _normalize(term: str) -> str:
    return term.strip().lower()


def _contains_whole(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    return re.search(r"\b" + re.escape(needle) + r"\b", haystack) is not None


def skill_matches(job_skill: str, candidate_term: str) -> bool:
    a, b = _normalize(job_skill), _normalize(candidate_term)
    if not a or not b:
        return False
    if a == b:
        return True
    # Whole-word containment both directions (e.g. "React" matches within "React.js"),
    # guarding against short substrings causing false positives (e.g. "AI" inside "Maintainability").
    if len(a) >= 2 and _contains_whole(b, a):
        return True
    if len(b) >= 2 and _contains_whole(a, b):
        return True
    return False


def find_matches(job_skills: list[str], candidate_terms: list[str]) -> tuple[list[str], list[str]]:
    """Returns (matched, missing) subsets of job_skills, matched against candidate_terms."""
    matched, missing = [], []
    for skill in job_skills:
        if any(skill_matches(skill, term) for term in candidate_terms):
            matched.append(skill)
        else:
            missing.append(skill)
    return matched, missing


def compute_skills_score(
    matched_required: list[str], missing_required: list[str],
    matched_preferred: list[str], missing_preferred: list[str],
) -> int:
    total_required = len(matched_required) + len(missing_required)
    total_preferred = len(matched_preferred) + len(missing_preferred)

    if total_required > 0:
        base = 100 * len(matched_required) / total_required
        if total_preferred > 0:
            base = min(100, base + 10 * (len(matched_preferred) / total_preferred))
        return round(base)

    if total_preferred > 0:
        return round(50 + 50 * len(matched_preferred) / total_preferred)

    # Job listed no required or preferred skills at all — can't assess confidently either way.
    return 60
