# Agentic Job Finder and Application Assistant
##demo video on youtube:https://youtu.be/2jT2LQv41R8
A multi-agent AI system that automates the most time-consuming parts of a job search: discovering real companies and job openings, matching them against a candidate's resume with an explainable score, and preparing — **never auto-submitting** — job applications on official company career pages.

Built as a full-stack application: a Python/FastAPI backend orchestrating six single-responsibility agents through **CrewAI** (real `Agent`/`Task`/`Crew` objects, not a hand-rolled prompt wrapper), and a React single-page frontend guiding the user through the workflow end-to-end.

## Why This Exists

Manually checking dozens of individual company career pages, judging how well each opening matches your own background, and retyping the same information into every application form does not scale. Most company career sites are JavaScript-rendered SPAs, so a plain HTTP request cannot even read the listings. This project discovers directly from primary sources (the employer's own career page, rendered with a real browser), explains every point of its match score, and keeps a human in control of the one action that genuinely matters — choosing to submit.

## Core Design Principle

**The system never invents information and never submits anything on the user's behalf.**

- Every job listing traces back to a link that was actually found on a real, rendered page.
- Every skill match is a literal string comparison against the resume's own extracted text — no LLM guessing.
- Two separate, explicit human approvals are required: one before any application preparation begins, and a second, independent one before a job is ever marked as submitted.
- No code path anywhere in the application clicks a final "Submit" button.

## How It Works

```
Resume Upload → Preferences → Company Discovery → Job Discovery → Matching & Ranking
      → User Selects Jobs → ★ Approval #1 → Application Preparation
      → Final Review → ★ Approval #2 → Application Tracker
```

1. **Resume Upload & Parsing** — extracts structured data (skills, education, experience, projects) from a PDF/DOCX resume without inventing anything not in the source document.
2. **Preferences** — collects work-mode, city, and experience preferences, or infers likely target roles from the resume via LLM.
3. **Company Discovery** — finds real companies and their official career pages via live web search (Tavily), with a deterministic filter that rejects place names (e.g. a city mis-extracted as a "company") and government/administrative bodies.
4. **Job Discovery** — renders each company's career page with a real headless browser (Playwright), extracts individual job listings (never navigation/category links), follows through to the real ATS board when the landing page is just a search widget, then visits each job's own detail page for its actual requirements. Optionally augmented with LinkedIn listings via Apify.
5. **Matching & Ranking** — scores every job with a six-factor weighted formula: skills (deterministic whole-word matching), semantic similarity (real Gemini embeddings + cosine similarity), education, experience, and role fit (LLM judgment, grounded in the job's own text), and location (deterministic rule-based comparison).
6. **Application Preparation** — auto-fills recognized text/dropdown form fields via Playwright, detecting and safely stopping (touching zero fields) on CAPTCHA, OTP, or login walls. Fields like work authorization and cover letters are never auto-filled — they always require the user's own input. It does **not** reliably attach the resume file to a real application form (most sites use a custom upload widget, not a plain file input) and it never logs in or submits on the user's behalf — see Honest Limitations below.
7. **Two-Gate Human Approval** — enforced at the backend state-machine level, not just the UI: Approval #1 gates whether any automation runs at all; Approval #2 (an explicit confirmation) gates whether a job is ever marked submitted.
8. **Application Tracker** — full status history for every job, end to end.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, Uvicorn, SQLAlchemy + SQLite |
| Agent Framework | **CrewAI** — every structured LLM call runs as a real `Agent` + `Task` inside a `Crew`, with `output_pydantic` enforcing the response shape |
| Resume Parsing | pypdf, python-docx |
| LLM (chat) | Swappable via one env var: Google Gemini, OpenRouter, OpenAI, or local Ollama — routed through CrewAI's own provider layer (native for Gemini/OpenAI, LiteLLM-backed for OpenRouter/Ollama) |
| LLM (embeddings) | Google Gemini `gemini-embedding-001`, always used for semantic matching regardless of the chat provider |
| Web Search | Tavily Search API |
| Additional Job Source | Apify (LinkedIn actor), optional and opt-in |
| Browser Automation | Playwright (Chromium) |
| Frontend | React 19, Vite — no router library, no state-management library, no UI kit; hand-written CSS design system |

## Key Engineering Decisions

- **CrewAI orchestrates every LLM call, but never decides anything on its own** — each of the 7 structured-extraction calls in the app is one narrow, pre-defined `Agent` + `Task`, invoked at one specific point in a linear, human-gated pipeline. No autonomous planning, no dynamic tool-calling loop — deliberately, so the two approval gates below stay fully deterministic.
- **JSON-schema-constrained LLM extraction** — every LLM call forces strict, schema-valid JSON output, never free-form prose.
- **Deterministic anti-hallucination backstops layered under every LLM call** — whole-word skill matching, URL grounding (a link must literally appear on the rendered page), date grounding (a date must be a verbatim substring of the page text), a hard-coded third-party job-board domain blocklist, and a place-name filter.
- **Two-stage job extraction** — listing-page fields (title/location/link) are extracted separately from detail-page fields (requirements/skills), since asking one call to guess fields that aren't actually on that page caused fabricated data during development.
- **Index-based link selection** — the model picks a link by its numeric position in a real, numbered list rather than typing a URL from memory, which was found to prevent fabricated-but-plausible-looking URLs.
- **Provider-agnostic LLM client with automatic rate-limit retry/backoff** — swap providers via one environment variable with zero code changes elsewhere.

## Project Structure

```
backend/
  app/
    main.py                    # All FastAPI REST endpoints
    config.py                  # Environment-based settings
    agents/                    # One agent per workflow phase
      resume_analyzer.py
      preference_agent.py
      company_discovery_agent.py
      job_discovery_agent.py
      matching_agent.py
      application_preparation_agent.py
    services/                  # Reusable, LLM-agnostic logic
      llm_client.py            # Every prompt/schema — calls into crewai_client.py
      crewai_client.py         # Real CrewAI Agent/Task/Crew orchestration + retry logic
      browser_client.py        # Playwright rendering + form-filling
      semantic_matcher.py      # Embeddings + cosine similarity
      apify_client.py          # Optional LinkedIn job source
      skill_matcher.py         # Deterministic skill matching
      ats_detector.py, form_filler.py, date_utils.py, job_filter.py, ...
    db/models.py                # Candidate, Company, Job ORM models
    models/schemas.py           # Every Pydantic API schema
frontend/
  src/
    App.jsx                    # Top-level view/state machine
    api/client.js               # Every backend call as a typed fetch wrapper
    components/                 # One component per screen + shared UI pieces
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) [Ollama](https://ollama.com) if running a local LLM instead of a cloud provider

### 1. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
python -m playwright install chromium

copy .env.example .env        # then fill in your own API keys
```

`requirements.txt` already includes `crewai[google-genai]`, since CrewAI's native Gemini provider (the default LLM here) needs that extra to work.

### 2. Configure `backend/.env`

Set `LLM_PROVIDER` to one of `openai` / `ollama` / `gemini` / `openrouter` and fill in the matching API key. A Tavily key is required for company/job discovery. A Gemini key is required for semantic matching specifically (used independently of whichever chat provider you choose). Apify is optional (adds LinkedIn listings). See `backend/.env.example` for the full list — never commit real values.

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Run both servers together

```bash
npm run dev
```

This starts the backend (`uvicorn app.main:app --port 8000`) and frontend (`vite`, port 5173) together. Open **http://localhost:5173**.

## Honest Limitations

- No automated test suite — verification during development was done manually against real, live data throughout.
- Some sites (e.g. TCS, EPAM, Naukri) actively block automated browser access; those sources are either excluded or shipped with a documented caveat rather than a fake result.
- Job Discovery runs sequentially per company (a parallelized version was tried and reverted after causing a real hang) — a full run against ~25 companies takes roughly 5–12 minutes.
- Semantic matching requires a Gemini API key specifically; it's unavailable if only a non-Gemini provider is configured, with a documented, non-silent fallback to a 5-factor score.
- Single-user, local application — no authentication/multi-user support, no production deployment configuration.
- Does not upload/attach the resume file into a real, external application form — most application pages use a custom JS upload widget rather than a plain file input, so this was never verified working end-to-end.
- Does not log in and cannot submit an application on the user's behalf — by design. Any application that requires signing in must be completed manually.

## License

Personal project — no license specified.
