"""Dynamic model listing — queries provider APIs via OpenAI SDK."""

from __future__ import annotations

import os

import httpx
from anthropic import Anthropic
from openai import OpenAI

from friday.cli.output import console, print_error
from friday.infra.config import FridaySettings

# Provider configs: (prefix, env_key for api_key, base_url or None)
_PROVIDERS: list[tuple[str, str, str | None]] = [
    ('openai', 'OPENAI_API_KEY', None),
    ('mistral', 'MISTRAL_API_KEY', 'https://api.mistral.ai/v1'),
    ('zai', 'ZAI_API_KEY', None),
]


def _list_from_api(prefix: str, api_key: str, base_url: str | None) -> list[str]:
    """Query /v1/models via the OpenAI SDK and return prefixed IDs."""
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.models.list()
        return sorted(f'{prefix}:{m.id}' for m in response.data)
    except Exception as exc:
        print_error(f'{prefix}: {exc}')
        return []


def _list_ollama() -> list[str]:
    """List local Ollama models."""
    try:
        resp = httpx.get('http://localhost:11434/api/tags', timeout=3)
        resp.raise_for_status()
        data = resp.json()
        return sorted(f'ollama:{m["name"]}' for m in data.get('models', []))
    except Exception:
        return []


def _list_anthropic() -> list[str]:
    """List Anthropic models via their API."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return []
    try:
        client = Anthropic(api_key=api_key)
        response = client.models.list()
        return sorted(f'anthropic:{m.id}' for m in response.data)
    except Exception:
        return []


def fetch_models(settings: FridaySettings, provider_filter: str | None = None) -> list[str]:
    """Fetch available models from all configured providers. Returns a flat list."""
    all_models: list[str] = []

    if not provider_filter or provider_filter == 'anthropic':
        all_models.extend(_list_anthropic())

    for prefix, env_key, base_url in _PROVIDERS:
        if provider_filter and provider_filter != prefix:
            continue
        api_key = os.environ.get(env_key, '')
        if not api_key:
            continue
        if prefix == 'zai':
            base_url = settings.zai_base_url
        all_models.extend(_list_from_api(prefix, api_key, base_url))

    if not provider_filter or provider_filter == 'ollama':
        all_models.extend(_list_ollama())

    return all_models


def list_models(settings: FridaySettings, provider_filter: str | None = None) -> None:
    """List models to console output."""
    all_models = fetch_models(settings, provider_filter)

    if not all_models:
        console.print('[muted]No models found. Set API keys in .env or start Ollama.[/muted]')
        return

    for model in all_models:
        console.print(model)
