from app.config import settings


class SearchNotConfiguredError(RuntimeError):
    pass


class SearchRequestError(RuntimeError):
    pass


def web_search(query: str, max_results: int = 6) -> list[dict]:
    """Runs a web search via Tavily and returns raw results (title/url/content)."""
    if not settings.tavily_api_key:
        raise SearchNotConfiguredError(
            "TAVILY_API_KEY is not set. Add it to backend/.env (see backend/.env.example)."
        )

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    try:
        response = client.search(query=query, max_results=max_results, search_depth="basic")
    except Exception as e:
        raise SearchRequestError(f"Web search failed for query '{query}': {e}") from e

    return [
        {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
        for r in response.get("results", [])
        if r.get("url")
    ]
