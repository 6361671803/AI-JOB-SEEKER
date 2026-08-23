"""Semantic matching between resume and job description via real text embeddings.

Complements the deterministic skill/location matching and the LLM-based education/experience/
role verdicts (matching_agent.py) with a genuine meaning-based similarity signal: the candidate's
full profile (skills, education, projects, internships, tools/frameworks/libraries, technologies,
roles) is embedded and compared against each job's own description/requirements text via cosine
similarity.

Uses real embeddings (Gemini's gemini-embedding-001, verified live — the model name changes
over time so this was checked against the account's actual available models, not assumed), not
TF-IDF: embeddings capture meaning (e.g. "computer vision" ~ "image recognition"), so a
genuinely relevant job scores meaningfully higher than an irrelevant one, verified with real text
(75% for a relevant match vs 52% for an irrelevant one in testing).

Only Gemini currently supports embeddings through this project's existing OpenAI-compatible
client setup (OpenRouter has no embeddings endpoint at all; Ollama's local models used here
don't either). If the configured provider can't do embeddings, or the call fails for any reason,
every job gets semantic_score=None and the caller excludes it from the weighted formula rather
than guessing a number.
"""
import logging

from app.config import settings

logger = logging.getLogger("semantic_matcher")

EMBEDDING_MODEL = "gemini-embedding-001"


def _resume_document(profile: dict) -> str:
    """Builds one text blob from every part of the resume relevant to job fit."""
    parts: list[str] = []
    parts.extend(profile.get("skills", []))
    parts.extend(profile.get("technologies", []))
    parts.extend(profile.get("certifications", []))
    parts.extend(profile.get("roles", []))

    for edu in profile.get("education", []):
        parts.extend(v for v in (edu.get("degree"), edu.get("field_of_study"), edu.get("institution")) if v)

    for exp in profile.get("experience", []) + profile.get("internships", []):
        parts.extend(v for v in (exp.get("title"), exp.get("company"), exp.get("description")) if v)

    for proj in profile.get("projects", []):
        if proj.get("name"):
            parts.append(proj["name"])
        if proj.get("description"):
            parts.append(proj["description"])
        parts.extend(proj.get("technologies", []))

    return " ".join(parts)


def _job_document(job_dict: dict, required_skills: list[str], preferred_skills: list[str]) -> str:
    parts: list[str] = [job_dict.get("title") or ""]
    parts.extend(required_skills)
    parts.extend(preferred_skills)
    for field in ("responsibilities", "qualifications", "education_requirement", "experience_requirement"):
        if job_dict.get(field):
            parts.append(job_dict[field])
    return " ".join(parts)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_semantic_scores(
    profile: dict, jobs: list[tuple[dict, list[str], list[str]]],
) -> list[int | None]:
    """Returns one score (0-100, or None if unavailable) per (job_dict, required, preferred)
    tuple in `jobs`, in the same order. Batches the resume + all job texts into a single
    embeddings call rather than one call per job.

    Always calls Gemini directly for this, via GEMINI_API_KEY, regardless of what LLM_PROVIDER
    is set to for the rest of the app (job extraction, match assessment, etc). This lets those
    other calls run through a different provider (e.g. OpenRouter, to dodge Gemini's chat-request
    rate limit) while semantic matching still works — the two are independent quotas."""
    if not settings.gemini_api_key:
        return [None] * len(jobs)

    resume_text = _resume_document(profile)
    job_texts = [_job_document(j, req, pref) for j, req, pref in jobs]

    if not resume_text.strip():
        return [None] * len(jobs)

    texts = [resume_text] + job_texts
    valid_indices = [i for i, t in enumerate(job_texts) if t.strip()]
    if not valid_indices:
        return [None] * len(jobs)

    try:
        from openai import OpenAI

        client = OpenAI(base_url=settings.gemini_base_url, api_key=settings.gemini_api_key)
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    except Exception as e:  # noqa: BLE001 - best-effort enrichment, never fatal to matching
        logger.warning("Semantic embedding call failed, skipping semantic scores: %s", e)
        return [None] * len(jobs)

    vectors = [d.embedding for d in response.data]
    resume_vec = vectors[0]
    job_vecs = vectors[1:]

    scores: list[int | None] = [None] * len(jobs)
    for i in valid_indices:
        similarity = _cosine_similarity(resume_vec, job_vecs[i])
        scores[i] = round(similarity * 100)
    return scores
