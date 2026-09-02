"""CrewAI-based LLM orchestration — the low-level primitive every structured extraction call in
this project goes through.

Replaces the previous hand-rolled `_chat_json()` (raw openai SDK client + manual JSON-schema
response_format) with real CrewAI `Agent`/`Task`/`Crew` objects, using `output_pydantic` for
schema-constrained output. This changes *how* a structured answer is obtained from the LLM; it
does not change *what* is asked of it — every system prompt's exact wording (including every
"never invent" rule) is passed through unchanged as the Task description, and every deterministic
grounding/backstop check downstream of this call is untouched.

Provider model-string format (verified live, not assumed from docs):
  Gemini:     "gemini/<model>"      — CrewAI's native provider, needs the `google-genai` extra
                                       (`pip install "crewai[google-genai]"`), api_key only.
  OpenAI:     "openai/<model>"      — CrewAI's native provider.
  OpenRouter: "openrouter/<model>"  — routed through CrewAI's LiteLLM integration.
  Ollama:     "ollama/<model>"      — routed through CrewAI's LiteLLM integration, base_url only.
"""
import itertools
import logging
import re
import threading
import time
from typing import Type, TypeVar

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger("crewai_client")

MAX_RATE_LIMIT_RETRIES = 3

T = TypeVar("T", bound=BaseModel)

# Round-robins between GEMINI_API_KEY and the optional GEMINI_API_KEY_2 so concurrent Job
# Discovery calls spread across two separate rate-limit budgets instead of one. If only one key
# is configured, this always returns that same key — identical to the old single-key behavior.
_gemini_key_cycle_lock = threading.Lock()
_gemini_key_cycle = None


def _next_gemini_key() -> str:
    global _gemini_key_cycle
    with _gemini_key_cycle_lock:
        if _gemini_key_cycle is None:
            keys = [k for k in (settings.gemini_api_key, settings.gemini_api_key_2) if k]
            _gemini_key_cycle = itertools.cycle(keys)
        return next(_gemini_key_cycle)


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMRequestError(RuntimeError):
    pass


def _build_llm():
    from crewai import LLM

    provider = settings.llm_provider
    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMNotConfiguredError(
                "OPENAI_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
            )
        return LLM(model=f"openai/{settings.llm_model}", api_key=settings.openai_api_key)

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMNotConfiguredError(
                "GEMINI_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
            )
        return LLM(model=f"gemini/{settings.llm_model}", api_key=_next_gemini_key())

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMNotConfiguredError(
                "OPENROUTER_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
            )
        return LLM(model=f"openrouter/{settings.llm_model}", api_key=settings.openrouter_api_key)

    if provider == "ollama":
        # Local CPU inference on a large structured-output schema can be slow, same reasoning as
        # the original _chat_json's generous Ollama timeout.
        return LLM(
            model=f"ollama/{settings.llm_model}",
            base_url=settings.ollama_base_url.removesuffix("/v1"),
            timeout=600,
        )

    raise LLMNotConfiguredError(f"Unsupported LLM_PROVIDER '{provider}'.")


def _retry_delay_seconds(error: Exception, attempt: int) -> float:
    """Same logic as the original _chat_json: use the provider's own suggested delay when its
    error message includes one, else a short linear backoff."""
    match = re.search(r"retry in ([\d.]+)s", str(error), re.IGNORECASE)
    if match:
        return float(match.group(1)) + 0.5
    return 2.0 * attempt


def run_structured_task(
    role: str,
    goal: str,
    backstory: str,
    task_description: str,
    expected_output: str,
    output_model: Type[T],
    inputs: dict | None = None,
) -> T:
    """Runs one CrewAI Agent + one Task in a single-task sequential Crew, and returns the
    schema-validated Pydantic output. Retries on rate-limit errors the same way the original
    _chat_json did (up to 3 attempts, honoring a provider's own suggested retry delay)."""
    from crewai import Agent, Crew, Process, Task

    llm = _build_llm()
    agent = Agent(role=role, goal=goal, backstory=backstory, llm=llm, verbose=False)
    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
        output_pydantic=output_model,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)

    attempt = 0
    while True:
        try:
            result = crew.kickoff(inputs=inputs or {})
            break
        except Exception as e:  # noqa: BLE001 - CrewAI/LiteLLM raise varying exception types
            # per provider; rate-limit errors are identified by message content (same approach
            # the original _chat_json used for the provider's own "retry in Ns" hint), since a
            # single shared exception class across every provider/backend isn't guaranteed here.
            is_rate_limit = "rate" in str(e).lower() and "limit" in str(e).lower()
            if not is_rate_limit:
                raise LLMRequestError(f"LLM request failed: {e}") from e
            attempt += 1
            if attempt > MAX_RATE_LIMIT_RETRIES:
                raise LLMRequestError(f"LLM request failed after retries (rate limited): {e}") from e
            logger.info("Rate limited, retrying (attempt %d/%d)", attempt, MAX_RATE_LIMIT_RETRIES)
            time.sleep(_retry_delay_seconds(e, attempt))

    if result.pydantic is None:
        raise LLMRequestError(
            f"LLM response did not match the required schema ({output_model.__name__}): {result.raw[:500]}"
        )
    return result.pydantic
