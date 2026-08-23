import json

from app.config import settings


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMRequestError(RuntimeError):
    pass


EXTRACTION_SYSTEM_PROMPT = """You extract structured candidate data from resume text.

STRICT RULES:
- Only use information explicitly present in the resume text.
- Never invent, infer, or embellish skills, experience, education, or dates.
- If a field is not present in the resume, use null (or an empty list for list fields).
- Do not upgrade qualifiers (e.g. if the resume says "Python", do not output "Advanced Python").
- Education: include ONLY degree entries that literally appear under an education/qualifications
  heading in the resume. Do not add a second degree, a higher/further degree, or any degree that
  is not explicitly written in the text — even if the candidate's skills suggest one.
- Never expand an abbreviation or acronym (e.g. "RAG", "MCP", "NLP", "API") into a full phrase
  unless that exact expansion is itself written in the resume text. If the resume just says "RAG",
  output "RAG" — do not guess what it stands for.
- "email" and "phone" must be copied exactly as written (usually in the header/contact section).
  Never construct or guess an email/phone from a name.
- "linkedin_url"/"github_url"/"portfolio_url": copy the URL as written if present (add "https://"
  only if the resume shows a bare domain like "linkedin.com/in/x" with no scheme). Use null if
  that platform isn't mentioned — do not assume a candidate has a GitHub/portfolio just because
  they're technical.
- "years_of_experience" should be your best numeric estimate based only on dates/durations
  explicitly stated in the resume; use null if it cannot be determined.
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

CANDIDATE_PROFILE_JSON_SCHEMA = {
    "name": "candidate_profile",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": ["string", "null"]},
            "email": {"type": ["string", "null"]},
            "phone": {"type": ["string", "null"]},
            "linkedin_url": {"type": ["string", "null"]},
            "github_url": {"type": ["string", "null"]},
            "portfolio_url": {"type": ["string", "null"]},
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "degree": {"type": ["string", "null"]},
                        "institution": {"type": ["string", "null"]},
                        "year": {"type": ["string", "null"]},
                        "field_of_study": {"type": ["string", "null"]},
                    },
                    "required": ["degree", "institution", "year", "field_of_study"],
                },
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": ["string", "null"]},
                        "company": {"type": ["string", "null"]},
                        "duration": {"type": ["string", "null"]},
                        "description": {"type": ["string", "null"]},
                    },
                    "required": ["title", "company", "duration", "description"],
                },
            },
            "internships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": ["string", "null"]},
                        "company": {"type": ["string", "null"]},
                        "duration": {"type": ["string", "null"]},
                        "description": {"type": ["string", "null"]},
                    },
                    "required": ["title", "company", "duration", "description"],
                },
            },
            "skills": {"type": "array", "items": {"type": "string"}},
            "technologies": {"type": "array", "items": {"type": "string"}},
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "description": {"type": ["string", "null"]},
                        "technologies": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name", "description", "technologies"],
                },
            },
            "certifications": {"type": "array", "items": {"type": "string"}},
            "locations": {"type": "array", "items": {"type": "string"}},
            "roles": {"type": "array", "items": {"type": "string"}},
            "years_of_experience": {"type": ["number", "null"]},
        },
        "required": [
            "name", "email", "phone", "linkedin_url", "github_url", "portfolio_url",
            "education", "experience", "internships", "skills", "technologies",
            "projects", "certifications", "locations", "roles", "years_of_experience",
        ],
    },
}


def _get_client():
    from openai import OpenAI

    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise LLMNotConfiguredError(
                "OPENAI_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
            )
        return OpenAI(api_key=settings.openai_api_key)

    if settings.llm_provider == "ollama":
        # Ollama's OpenAI-compatible endpoint ignores the API key but requires one to be set.
        # Local CPU inference on a large structured-output schema can be slow, so use a
        # generous timeout rather than the SDK default.
        return OpenAI(base_url=settings.ollama_base_url, api_key="ollama", timeout=600.0)

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMNotConfiguredError(
                "GEMINI_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
            )
        return OpenAI(base_url=settings.gemini_base_url, api_key=settings.gemini_api_key)

    if settings.llm_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMNotConfiguredError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
            )
        return OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key)

    raise LLMNotConfiguredError(f"Unsupported LLM_PROVIDER '{settings.llm_provider}'.")


def _extract_json_content(raw: str) -> dict:
    text = raw.strip()
    # Reasoning models (e.g. Qwen3) may emit a <think>...</think> block before the answer.
    if "<think>" in text and "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    # Some local models wrap JSON in a markdown code fence despite instructions not to.
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


MAX_RATE_LIMIT_RETRIES = 3


def _retry_delay_seconds(error: Exception, attempt: int) -> float:
    """Uses the provider's own suggested retry delay when it gives one, else a short backoff."""
    import re

    match = re.search(r"retry in ([\d.]+)s", str(error), re.IGNORECASE)
    if match:
        return float(match.group(1)) + 0.5
    return 2.0 * attempt


def _chat_json(system_prompt: str, user_content: str, json_schema: dict) -> dict:
    import time

    from openai import APIConnectionError, APIError, RateLimitError

    client = _get_client()
    if settings.llm_provider == "ollama":
        # Disable Qwen3's chain-of-thought output so the response is pure JSON.
        system_prompt = f"{system_prompt}\n/no_think"

    attempt = 0
    while True:
        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_schema", "json_schema": json_schema},
                temperature=0,
            )
            break
        except RateLimitError as e:
            # Free-tier per-minute quotas (e.g. Gemini's free tier) are hit routinely during a
            # discovery run that fires many calls back-to-back — worth a short backoff-and-retry
            # rather than failing the whole run on a transient minute-window limit.
            attempt += 1
            if attempt > MAX_RATE_LIMIT_RETRIES:
                raise LLMRequestError(f"LLM request failed after retries (rate limited): {e}") from e
            time.sleep(_retry_delay_seconds(e, attempt))
        except APIConnectionError as e:
            raise LLMRequestError(
                f"Could not reach LLM provider '{settings.llm_provider}' "
                f"(is Ollama running at {settings.ollama_base_url}?): {e}"
            ) from e
        except APIError as e:
            raise LLMRequestError(f"LLM request failed: {e}") from e

    content = response.choices[0].message.content
    try:
        return _extract_json_content(content)
    except json.JSONDecodeError as e:
        raise LLMRequestError(f"LLM returned non-JSON content that could not be parsed: {e}") from e


def extract_candidate_profile(resume_text: str) -> dict:
    """Calls the configured LLM provider to turn raw resume text into a structured profile dict."""
    return _chat_json(
        EXTRACTION_SYSTEM_PROMPT,
        f"Resume text:\n\n{resume_text}",
        CANDIDATE_PROFILE_JSON_SCHEMA,
    )


ROLE_INFERENCE_SYSTEM_PROMPT = """You suggest suitable job role titles for a candidate based ONLY
on the skills, technologies, projects, experience, and education given to you.

STRICT RULES:
- Do not restrict suggestions to software engineering roles — consider the candidate's actual
  background (e.g. finance, marketing, design, data, operations, HR, etc.) and suggest roles that
  fit whatever domain their skills/experience actually show.
- Every suggested role must be justifiable from the given skills/experience/projects — do not
  suggest roles that require skills or domain knowledge absent from the input.
- Return between 1 and 8 role titles, ranked most-suitable first.
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

ROLE_INFERENCE_JSON_SCHEMA = {
    "name": "role_inference",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "roles": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["roles"],
    },
}


def infer_target_roles(profile: dict, experience_level: str) -> list[str]:
    """Suggests suitable job roles from resume-derived skills/experience when the user didn't pick one."""
    candidate_summary = {
        "skills": profile.get("skills", []),
        "technologies": profile.get("technologies", []),
        "experience": profile.get("experience", []),
        "internships": profile.get("internships", []),
        "projects": profile.get("projects", []),
        "education": profile.get("education", []),
        "certifications": profile.get("certifications", []),
        "years_of_experience": profile.get("years_of_experience"),
        "user_selected_experience_level": experience_level,
    }
    result = _chat_json(
        ROLE_INFERENCE_SYSTEM_PROMPT,
        f"Candidate background:\n\n{json.dumps(candidate_summary, indent=2)}",
        ROLE_INFERENCE_JSON_SCHEMA,
    )
    return result.get("roles", [])


COMPANY_NAME_EXTRACTION_SYSTEM_PROMPT = """You identify real company names from web search results
about companies hiring for a given role and location.

STRICT RULES:
- Only include company names that literally appear in the provided search result titles or content.
- Never invent, guess, or embellish a company name.
- Exclude job boards / aggregators themselves (e.g. LinkedIn, Indeed, Naukri, Glassdoor, Monster,
  ZipRecruiter, AngelList, Wellfound, Instahyre) — those are sources, not employers.
- Exclude geographic place names (cities, states, provinces, countries, regions) even if they
  appear prominently in the results — e.g. "Hyderabad", "Telangana", "Bangalore", "India" are
  locations, never company names, even though they'll appear constantly since they describe
  where a job is based, not who is hiring.
- Exclude government departments, ministries, public service commissions, and recruitment
  boards (e.g. "Telangana State Public Service Commission", "Staff Selection Commission",
  "Department of School Education") — these publish exam/recruitment notifications, not a
  specific employer's job opening, and are out of scope for this job search.
- Return every distinct company name that genuinely appears in the results (do not artificially
  limit yourself to a small number) — there is no need to omit real companies to keep the list short.
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

COMPANY_NAME_EXTRACTION_JSON_SCHEMA = {
    "name": "company_names",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "companies": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["companies"],
    },
}


def extract_company_names(search_results: list[dict], role: str, location: str) -> list[str]:
    """Pulls real company names (only ones literally present in the search results) out of a search."""
    if not search_results:
        return []
    result = _chat_json(
        COMPANY_NAME_EXTRACTION_SYSTEM_PROMPT,
        f"Role: {role}\nLocation: {location}\n\nSearch results:\n\n"
        f"{json.dumps(search_results, indent=2)}",
        COMPANY_NAME_EXTRACTION_JSON_SCHEMA,
    )
    return result.get("companies", [])


CAREER_PAGE_RESOLUTION_SYSTEM_PROMPT = """You identify a company's official website and official
careers/jobs page from web search results.

STRICT RULES:
- You may ONLY return a URL that appears verbatim in the provided search results. Never fabricate,
  guess, construct, or modify a URL.
- Prefer the company's own domain over third-party job boards (LinkedIn, Indeed, Glassdoor, Naukri,
  Monster, ZipRecruiter, AngelList, Wellfound, Instahyre, etc.).
- If no result is confidently the company's own official site, set "official_website" to null.
- If no result is confidently the company's own official careers/jobs page, set "careers_url" to null
  — do NOT fall back to a third-party job board URL for this field.
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

CAREER_PAGE_RESOLUTION_JSON_SCHEMA = {
    "name": "career_page_resolution",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "official_website": {"type": ["string", "null"]},
            "careers_url": {"type": ["string", "null"]},
        },
        "required": ["official_website", "careers_url"],
    },
}


# Domains of third-party job boards/aggregators — never acceptable as a "careers_url", even if
# the model tries to return one (smaller local models don't always follow that instruction).
THIRD_PARTY_JOB_BOARD_DOMAINS = (
    "linkedin.com", "indeed.com", "glassdoor.com", "naukri.com", "monster.com",
    "ziprecruiter.com", "angel.co", "wellfound.com", "instahyre.com", "shine.com",
    "foundit.in", "timesjobs.com", "simplyhired.com",
)


def _is_third_party_job_board(url: str | None) -> bool:
    if not url:
        return False
    return any(domain in url.lower() for domain in THIRD_PARTY_JOB_BOARD_DOMAINS)


def resolve_official_career_page(company_name: str, search_results: list[dict]) -> tuple[str | None, str | None]:
    """Picks the official website/careers URL for a company out of search results — never fabricated."""
    if not search_results:
        return None, None
    result = _chat_json(
        CAREER_PAGE_RESOLUTION_SYSTEM_PROMPT,
        f"Company: {company_name}\n\nSearch results:\n\n{json.dumps(search_results, indent=2)}",
        CAREER_PAGE_RESOLUTION_JSON_SCHEMA,
    )
    website = result.get("official_website")
    careers_url = result.get("careers_url")

    # Belt-and-braces: never trust a URL the model didn't actually copy from the results.
    valid_urls = {r["url"] for r in search_results if r.get("url")}
    if website not in valid_urls:
        website = None
    if careers_url not in valid_urls:
        careers_url = None

    # Belt-and-braces #2: never accept a third-party job board as the "official" careers page,
    # even if the model returned one despite being told not to.
    if _is_third_party_job_board(website):
        website = None
    if _is_third_party_job_board(careers_url):
        careers_url = None

    return website, careers_url


# Stage 1: the careers/listing page itself usually only shows title, location, and an apply
# link per job — NOT requirements/qualifications/skills (those live on each job's own detail
# page). Asking the model to fill those fields from a listing page that doesn't have them caused
# it to hallucinate, so this stage only extracts what a listing page actually contains.
#
# Local models were also found to fabricate plausible-looking-but-fake URLs when asked to type
# out a full href (e.g. guessing a Greenhouse-style URL pattern with the wrong ID). Asking the
# model to instead pick a link by its INDEX in a numbered list is far more reliable for weaker
# models — it's a closed-set choice rather than free recall.
JOB_LISTING_EXTRACTION_SYSTEM_PROMPT = """You extract the list of INDIVIDUAL job postings shown
on a company's careers/jobs LISTING page (not an individual job description page).

CRITICAL — DO NOT CONFUSE NAVIGATION/CATEGORY LINKS WITH REAL JOB POSTINGS:
Many career pages mix real job postings together with site navigation, career-path categories,
and general program pages. You must extract ONLY genuine individual openings, each with its own
specific job title (e.g. "Software Engineer II", "Data Analyst - Mumbai", "Senior AI Developer").
Do NOT extract entries like these, even if they appear in a "careers" context — they are
navigation/category links, not job postings, and including them would send the candidate to the
wrong page:
  - Broad career-path or audience categories: "Students and graduates", "Experienced
    professionals", "Executives", "Professions", "Early Careers", "Graduate Programs"
  - Named leadership/development PROGRAMS rather than a specific role: "Leadership Program",
    "Accelerated Leadership Track", "Future Shapers", "Leadership University"
  - Generic site links: "Careers", "About Us", "Employee", "Life at [Company]", "Benefits"
  - Department or team names with no specific role attached: "Engineering", "Sales", "Marketing"
If a page consists mostly of this kind of navigation/category content and you cannot find
genuinely distinct individual job postings, return an EMPTY list rather than including any of
the above — an empty list is the correct, honest answer for that page.

STRICT RULES FOR ENTRIES YOU DO EXTRACT:
- Only extract jobs that are actually listed on this page. Do not invent job openings.
- Listing pages typically show only a title, a location, and an "Apply"/"View" link per job —
  do NOT try to guess responsibilities, requirements, qualifications, or skills; those aren't on
  this page. Only extract "title", "location", "work_mode", and "link_index".
- "link_index" must be the number (from the numbered links list below the page text) of the link
  that goes to this specific job. You may ONLY use a number that appears in that list. If you
  cannot find a matching link, use null. Never invent a link or URL yourself.
- "location" and "work_mode" must be null if not shown next to that specific listing — do not
  guess based on the company's general location.
- "work_mode" (Remote / Hybrid / On-site) must only be set if the page explicitly states it for
  that listing.
- Each job in your output must correspond to a genuinely distinct listing on the page. Never
  repeat the same job more than once.
- Extract at most 8 of the listings shown.
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

JOB_LISTING_ENTRY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "location": {"type": ["string", "null"]},
        "work_mode": {"type": ["string", "null"]},
        "link_index": {"type": ["integer", "null"]},
    },
    "required": ["title", "location", "work_mode", "link_index"],
}

JOB_LISTING_EXTRACTION_JSON_SCHEMA = {
    "name": "job_listings",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "jobs": {"type": "array", "items": JOB_LISTING_ENTRY_SCHEMA},
        },
        "required": ["jobs"],
    },
}


def extract_job_listings(company_name: str, page_text: str, links: list[dict]) -> list[dict]:
    """Pulls the basic job listing (title/location/work_mode/job_url) from a careers page."""
    if not page_text.strip():
        return []

    numbered_links = [f"[{i}] {l['text']} -> {l['href']}" for i, l in enumerate(links) if l.get("href")]

    result = _chat_json(
        JOB_LISTING_EXTRACTION_SYSTEM_PROMPT,
        f"Company: {company_name}\n\nPage text:\n\n{page_text}\n\nNumbered links on page:\n\n"
        + "\n".join(numbered_links),
        JOB_LISTING_EXTRACTION_JSON_SCHEMA,
    )
    jobs = result.get("jobs", [])

    seen_titles: set[str] = set()
    deduped = []
    for job in jobs:
        idx = job.get("link_index")
        job["job_url"] = links[idx]["href"] if isinstance(idx, int) and 0 <= idx < len(links) else None
        job.pop("link_index", None)

        # Backstop: only trust an explicit "Remote"/"Hybrid"/"On-site" claim if that word also
        # appears in this listing's own location text — otherwise the model is likely guessing.
        location = (job.get("location") or "").lower()
        work_mode = (job.get("work_mode") or "").lower()
        if work_mode and work_mode.split()[0] not in location:
            job["work_mode"] = None

        key = (job.get("title") or "").strip().lower()
        if key and key not in seen_titles:
            seen_titles.add(key)
            deduped.append(job)

    return deduped


# Stage 2: for a single job's own detail page, extract the actual description fields. This page
# genuinely contains the requirements/qualifications, so asking for them here is well-grounded.
JOB_DETAIL_EXTRACTION_SYSTEM_PROMPT = """You extract structured details from a single job
posting's own description page.

STRICT RULES:
- Only use information explicitly present in the page text. Never invent, infer, or embellish
  requirements, qualifications, dates, or skills.
- If a field is not present on the page, use null (or an empty list for skill lists).
- "date_posted" and "closing_date" must be copied exactly as written on the page (e.g.
  "3 days ago", "2026-08-01"). Never calculate, estimate, or guess a date — use null if none is
  shown.
- "work_mode" (Remote / Hybrid / On-site) must only be set if the page explicitly states it.
- Separate "required_skills" (must-have) from "preferred_skills" (nice-to-have) based on how the
  page itself frames them (e.g. "Requirements" vs "Nice to have" / "Preferred").
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

JOB_DETAIL_EXTRACTION_JSON_SCHEMA = {
    "name": "job_detail",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "job_id": {"type": ["string", "null"]},
            "location": {"type": ["string", "null"]},
            "work_mode": {"type": ["string", "null"]},
            "date_posted": {"type": ["string", "null"]},
            "closing_date": {"type": ["string", "null"]},
            "employment_type": {"type": ["string", "null"]},
            "experience_requirement": {"type": ["string", "null"]},
            "education_requirement": {"type": ["string", "null"]},
            "required_skills": {"type": "array", "items": {"type": "string"}},
            "preferred_skills": {"type": "array", "items": {"type": "string"}},
            "responsibilities": {"type": ["string", "null"]},
            "qualifications": {"type": ["string", "null"]},
        },
        "required": [
            "job_id", "location", "work_mode", "date_posted", "closing_date", "employment_type",
            "experience_requirement", "education_requirement", "required_skills",
            "preferred_skills", "responsibilities", "qualifications",
        ],
    },
}


def extract_job_description(job_title: str, page_text: str) -> dict:
    """Extracts requirements/qualifications/etc. from a job's own description page."""
    if not page_text.strip():
        return {}
    result = _chat_json(
        JOB_DETAIL_EXTRACTION_SYSTEM_PROMPT,
        f"Job title: {job_title}\n\nPage text:\n\n{page_text}",
        JOB_DETAIL_EXTRACTION_JSON_SCHEMA,
    )

    # Belt-and-braces: dates are load-bearing for the later 30-day filter, and small local
    # models have been observed to invent a plausible-looking date that isn't on the page at
    # all. Only trust a date the model claims if it's actually a verbatim substring of the page.
    for date_field in ("date_posted", "closing_date"):
        value = result.get(date_field)
        if value and value not in page_text:
            result[date_field] = None

    return result


# Resume/Job Matching Agent — the judgment-based half.
#
# Skills/technology matching and location matching are handled deterministically elsewhere
# (skill_matcher.py) since those claims are safety-critical and string comparison has zero
# hallucination risk. This call only handles the parts that genuinely need judgment: whether
# stated education/experience requirements are met, how relevant the role is, and eligibility
# notes explicitly written in the posting. It's given the already-computed matched skills so its
# "why this matches" text can reference them accurately instead of re-deriving (and potentially
# getting wrong) which skills actually matched.
JOB_MATCH_ASSESSMENT_SYSTEM_PROMPT = """You assess how well a candidate fits a specific job, based
ONLY on the candidate and job information given to you.

STRICT RULES:
- Base "education_verdict" only on the job's stated education_requirement vs the candidate's
  actual education entries. If the job doesn't state an education requirement, use "unclear".
- Base "experience_verdict" only on the job's stated experience_requirement vs the candidate's
  actual years_of_experience/experience entries. If the job doesn't state a requirement, use
  "unclear".
- "role_relevance" must be judged from the candidate's actual skills/experience/projects vs the
  job title and responsibilities — not from the job title alone.
- "relevant_projects" must ONLY contain project names copied verbatim from the candidate's
  project list given to you. Never invent a project or reference one not in that list.
- "eligibility_issues" must ONLY include issues EXPLICITLY stated in the job's own text (e.g.
  "must have current work authorization", "on-site only, no relocation assistance", "PhD
  required", "security clearance required"). Never invent a generic eligibility concern that
  isn't literally written in the job posting.
- "why_this_matches" must ONLY reference skills from the "matched_required_skills" and
  "matched_preferred_skills" lists given to you, and/or projects from "relevant_projects". Do not
  claim any skill or experience not explicitly given to you. Keep it to 2-3 sentences.
- Output must be valid JSON matching the given schema exactly, with no extra commentary.
"""

JOB_MATCH_ASSESSMENT_JSON_SCHEMA = {
    "name": "job_match_assessment",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "education_verdict": {"type": "string", "enum": ["meets", "partial", "does_not_meet", "unclear"]},
            "education_reasoning": {"type": "string"},
            "experience_verdict": {"type": "string", "enum": ["meets", "partial", "does_not_meet", "unclear"]},
            "experience_reasoning": {"type": "string"},
            "role_relevance": {"type": "string", "enum": ["strong", "moderate", "weak"]},
            "role_reasoning": {"type": "string"},
            "relevant_projects": {"type": "array", "items": {"type": "string"}},
            "eligibility_issues": {"type": "array", "items": {"type": "string"}},
            "why_this_matches": {"type": "string"},
        },
        "required": [
            "education_verdict", "education_reasoning", "experience_verdict", "experience_reasoning",
            "role_relevance", "role_reasoning", "relevant_projects", "eligibility_issues", "why_this_matches",
        ],
    },
}


def assess_job_match(
    profile: dict,
    preferences: dict,
    job: dict,
    matched_required_skills: list[str],
    matched_preferred_skills: list[str],
) -> dict:
    candidate_summary = {
        "education": profile.get("education", []),
        "years_of_experience": profile.get("years_of_experience"),
        "experience": profile.get("experience", []),
        "internships": profile.get("internships", []),
        "projects": [p.get("name") for p in profile.get("projects", []) if p.get("name")],
        "experience_level_selected": preferences.get("experience_level"),
    }
    job_summary = {
        "title": job.get("title"),
        "education_requirement": job.get("education_requirement"),
        "experience_requirement": job.get("experience_requirement"),
        "responsibilities": job.get("responsibilities"),
        "qualifications": job.get("qualifications"),
    }
    context = {
        "candidate": candidate_summary,
        "job": job_summary,
        "matched_required_skills": matched_required_skills,
        "matched_preferred_skills": matched_preferred_skills,
    }
    return _chat_json(
        JOB_MATCH_ASSESSMENT_SYSTEM_PROMPT,
        json.dumps(context, indent=2),
        JOB_MATCH_ASSESSMENT_JSON_SCHEMA,
    )
