"""Web search tool implementation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from friday.core.settings import Settings


class WebSearchProvider(Protocol):
    async def search(self, query: str) -> list[dict[str, str]]: ...


@dataclass(frozen=True)
class MissingConfigProvider:
    reason: str

    async def search(self, query: str) -> list[dict[str, str]]:
        _ = query
        raise RuntimeError(self.reason)


class PerplexitySearchProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float = 15.0,
        max_results: int = 5,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._max_results = max_results

    async def search(self, query: str) -> list[dict[str, str]]:
        payload = _build_perplexity_payload(self._model, query)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return _parse_perplexity_response(data, self._max_results)


class BraveSearchProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_s: float = 10.0,
        max_results: int = 5,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_results = max_results

    async def search(self, query: str) -> list[dict[str, str]]:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self._api_key,
        }
        params = {"q": query}
        url = f"{self._base_url}/res/v1/web/search"

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        return _parse_brave_response(data, self._max_results)


class DuckDuckGoSearchProvider:
    def __init__(
        self,
        user_agent: str,
        timeout_s: float = 10.0,
        max_results: int = 5,
    ) -> None:
        self._user_agent = user_agent
        self._timeout_s = timeout_s
        self._max_results = max_results

    async def search(self, query: str) -> list[dict[str, str]]:
        headers = {"User-Agent": self._user_agent}
        params = {"q": query, "kl": "us-en"}
        url = "https://duckduckgo.com/html/"

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            html = response.text

        return _parse_ddg_html(html, self._max_results)


def build_provider(settings: Settings) -> WebSearchProvider:
    provider = settings.web_search_provider.strip().lower()
    if provider == "auto":
        if settings.brave_search_api_key:
            return BraveSearchProvider(
                api_key=settings.brave_search_api_key,
                base_url=settings.brave_search_base_url,
                timeout_s=settings.brave_search_timeout_s,
                max_results=settings.brave_search_max_results,
            )
        if settings.perplexity_api_key:
            return PerplexitySearchProvider(
                api_key=settings.perplexity_api_key,
                base_url=settings.perplexity_base_url,
                model=settings.perplexity_model,
                timeout_s=settings.perplexity_timeout_s,
                max_results=settings.perplexity_max_results,
            )
        return DuckDuckGoSearchProvider(
            user_agent=settings.web_search_user_agent,
            max_results=settings.ddg_max_results,
        )

    if provider in {"perplexity", "pplx"}:
        if not settings.perplexity_api_key:
            return MissingConfigProvider("PERPLEXITY_API_KEY is not set")
        return PerplexitySearchProvider(
            api_key=settings.perplexity_api_key,
            base_url=settings.perplexity_base_url,
            model=settings.perplexity_model,
            timeout_s=settings.perplexity_timeout_s,
            max_results=settings.perplexity_max_results,
        )
    if provider in {"brave"}:
        if not settings.brave_search_api_key:
            return MissingConfigProvider("BRAVE_SEARCH_API_KEY is not set")
        return BraveSearchProvider(
            api_key=settings.brave_search_api_key,
            base_url=settings.brave_search_base_url,
            timeout_s=settings.brave_search_timeout_s,
            max_results=settings.brave_search_max_results,
        )
    if provider in {"ddg", "duckduckgo"}:
        return DuckDuckGoSearchProvider(
            user_agent=settings.web_search_user_agent,
            max_results=settings.ddg_max_results,
        )

    raise ValueError(f"Unsupported web search provider: {provider}")


def _build_perplexity_payload(model: str, query: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return JSON array of search results with keys "
                    "title, url, snippet. No markdown."
                ),
            },
            {"role": "user", "content": query},
        ],
        "temperature": 0.2,
    }


def _parse_perplexity_response(
    payload: dict[str, Any], max_results: int
) -> list[dict[str, str]]:
    content = _first_choice_content(payload)
    if content:
        extracted = _extract_json_results(content)
        if extracted:
            return extracted[:max_results]

    citations = _extract_citations(payload)
    if citations:
        snippet = content or ""
        return [
            {"title": _title_from_url(url), "url": url, "snippet": snippet}
            for url in citations[:max_results]
        ]

    return []


def _parse_brave_response(
    payload: dict[str, Any], max_results: int
) -> list[dict[str, str]]:
    web = payload.get("web")
    if not isinstance(web, dict):
        return []
    results = web.get("results")
    if not isinstance(results, list):
        return []
    parsed: list[dict[str, str]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        title = str(item.get("title", "")).strip() or url
        snippet = str(item.get("description", "")).strip()
        parsed.append({"title": title, "url": url, "snippet": snippet})
        if len(parsed) >= max_results:
            break
    return parsed


def _parse_ddg_html(html: str, max_results: int) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    parsed: list[dict[str, str]] = []

    for result in soup.select("div.result"):
        link = result.select_one("a.result__a")
        if link is None:
            continue
        url = str(link.get("href") or "").strip()
        if not url:
            continue
        title = link.get_text(" ", strip=True) or url
        snippet_node = result.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        parsed.append({"title": title, "url": url, "snippet": snippet})
        if len(parsed) >= max_results:
            return parsed

    if parsed:
        return parsed

    for link in soup.select("a.result__a"):
        url = str(link.get("href") or "").strip()
        if not url:
            continue
        title = link.get_text(" ", strip=True) or url
        parsed.append({"title": title, "url": url, "snippet": ""})
        if len(parsed) >= max_results:
            break

    return parsed


def _first_choice_content(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, Sequence) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def _extract_json_results(text: str) -> list[dict[str, str]] | None:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    results: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        title = str(item.get("title", "")).strip() or url
        snippet = str(item.get("snippet", "")).strip()
        results.append({"title": title, "url": url, "snippet": snippet})

    return results or None


def _extract_citations(payload: dict[str, Any]) -> list[str]:
    citations = payload.get("citations") or payload.get("sources") or []
    if not isinstance(citations, list):
        return []

    urls: list[str] = []
    for item in citations:
        if isinstance(item, str) and item.strip():
            urls.append(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("url"), str):
            url = item["url"].strip()
            if url:
                urls.append(url)
    return urls


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url
