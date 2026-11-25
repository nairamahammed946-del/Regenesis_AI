"""Optional live web search for REGENESIS AI. Search results are untrusted evidence, not facts."""
from typing import Any, Dict, List
import httpx
from backend.app.core.config import settings


async def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    if not settings.WEB_SEARCH_ENABLED:
        return []
    query = (query or "").strip()[:500]
    if not query:
        return []
    timeout = httpx.Timeout(settings.WEB_SEARCH_TIMEOUT_SECONDS)
    provider = settings.WEB_SEARCH_PROVIDER.lower().strip()
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if provider == "tavily" and settings.TAVILY_API_KEY:
            response = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": settings.TAVILY_API_KEY, "query": query, "search_depth": "basic",
                      "max_results": max(1, min(max_results, 8)), "include_answer": False},
            )
            response.raise_for_status()
            rows = response.json().get("results", [])
            return [{"title": str(x.get("title", ""))[:300], "url": str(x.get("url", ""))[:1000],
                     "snippet": str(x.get("content", ""))[:1200]} for x in rows if x.get("url")]
        if provider == "brave" and settings.BRAVE_SEARCH_API_KEY:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max(1, min(max_results, 8))},
                headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY, "Accept": "application/json"},
            )
            response.raise_for_status()
            rows = response.json().get("web", {}).get("results", [])
            return [{"title": str(x.get("title", ""))[:300], "url": str(x.get("url", ""))[:1000],
                     "snippet": str(x.get("description", ""))[:1200]} for x in rows if x.get("url")]
    return []


def needs_web_search(query: str) -> bool:
    q = (query or "").lower()
    signals = ("ابحث", "بحث", "على الانترنت", "على النت", "مصانع", "شركات", "مصنع",
               "سعر اليوم", "الاسعار الحالية", "أحدث", "اخر", "آخر", "قانون", "قرار",
               "latest", "search the web", "find factories", "companies", "current price",
               "regulation", "recent research", "supplier", "buyer")
    return any(term in q for term in signals)


def format_search_context(results: List[Dict[str, str]]) -> str:
    if not results:
        return "لا توجد نتائج ويب متاحة. لا تدّعِ أنك بحثت على الإنترنت."
    return "\n".join(
        f"[WEB {i}] {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        for i, r in enumerate(results, 1)
    )
