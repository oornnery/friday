from __future__ import annotations

import asyncio

import pytest

from friday.tools.local import web_search


def test_parse_perplexity_response_from_json() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '[{"title": "Example", "url": "https://example.com", '
                        '"snippet": "Result"}]'
                    )
                }
            }
        ]
    }
    results = web_search._parse_perplexity_response(payload, max_results=5)
    assert results == [
        {
            "title": "Example",
            "url": "https://example.com",
            "snippet": "Result",
        }
    ]


def test_parse_perplexity_response_from_citations() -> None:
    payload = {
        "choices": [{"message": {"content": "Summary text."}}],
        "citations": ["https://example.org"],
    }
    results = web_search._parse_perplexity_response(payload, max_results=5)
    assert results == [
        {
            "title": "example.org",
            "url": "https://example.org",
            "snippet": "Summary text.",
        }
    ]


def test_missing_config_provider_raises() -> None:
    provider = web_search.MissingConfigProvider("missing key")
    with pytest.raises(RuntimeError, match="missing key"):
        asyncio.run(provider.search("query"))


def test_parse_brave_response() -> None:
    payload = {
        "web": {
            "results": [
                {
                    "title": "Example Brave",
                    "url": "https://brave.example.com",
                    "description": "Brave snippet",
                }
            ]
        }
    }
    results = web_search._parse_brave_response(payload, max_results=5)
    assert results == [
        {
            "title": "Example Brave",
            "url": "https://brave.example.com",
            "snippet": "Brave snippet",
        }
    ]


def test_parse_ddg_html() -> None:
    html = """
    <div class="results">
      <div class="result">
        <a class="result__a" href="https://ddg.example.com">DuckDuckGo</a>
        <span class="result__snippet">DDG snippet</span>
      </div>
    </div>
    """
    results = web_search._parse_ddg_html(html, max_results=5)
    assert results == [
        {
            "title": "DuckDuckGo",
            "url": "https://ddg.example.com",
            "snippet": "DDG snippet",
        }
    ]
