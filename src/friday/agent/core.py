"""Agent core — wraps pydantic-ai with Friday's context, tools, and modes."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.exceptions import UserError
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from friday.agent.context import WorkspaceContext
from friday.agent.deps import AgentDeps
from friday.agent.modes import MODE_CONFIGS, ModeConfig, load_prompt
from friday.domain.models import AgentMode
from friday.infra.config import FridaySettings
from friday.tools import filesystem, shell

__all__ = ['TOOL_FUNCTIONS', 'AgentDeps', 'create_agent']

log = logging.getLogger(__name__)

# Tool function lookup — maps name to the actual async function
TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    'read_file': filesystem.read_file,
    'write_file': filesystem.write_file,
    'patch_file': filesystem.patch_file,
    'list_files': filesystem.list_files,
    'search': filesystem.search,
    'run_shell': shell.run_shell,
}


def _resolve_model(model_name: str, settings: FridaySettings) -> Model:
    """Resolve model string to a pydantic-ai Model eagerly.

    Forces provider creation so missing API keys fail immediately
    (not deferred to .run()).
    """
    if model_name.startswith('zai:'):
        api_key = settings.zai_api_key or os.environ.get('ZAI_API_KEY', '')
        base_url = settings.zai_base_url or os.environ.get('ZAI_BASE_URL', '')
        if not api_key:
            msg = 'Set `ZAI_API_KEY` in .env to use the zai: provider.'
            raise UserError(msg)
        return OpenAIChatModel(
            model_name.removeprefix('zai:'),
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
    # Eagerly resolve — triggers provider init (checks API keys)
    from pydantic_ai.models import infer_model

    return infer_model(model_name)


def resolve_model_with_fallback(model_name: str, settings: FridaySettings) -> Model | str:
    """Try to resolve the model, fall back to fallback_model if available."""
    try:
        return _resolve_model(model_name, settings)
    except UserError:
        if settings.fallback_model and settings.fallback_model != model_name:
            log.info(
                'Default model %s unavailable, falling back to %s',
                model_name,
                settings.fallback_model,
            )
            return _resolve_model(settings.fallback_model, settings)
        raise


def _build_model_settings(mode_config: ModeConfig) -> ModelSettings | None:
    """Build ModelSettings from mode config (thinking, etc.)."""
    if not mode_config.thinking:
        return None
    return ModelSettings(thinking=mode_config.thinking)


def _build_agent(
    model: Model | str,
    system_prompt: str,
    tools: list[Callable[..., Any]],
    model_settings: ModelSettings | None,
) -> Agent[AgentDeps, str]:
    """Construct the pydantic-ai Agent."""
    return Agent(
        model=model,
        system_prompt=system_prompt,
        deps_type=AgentDeps,
        tools=tools,
        model_settings=model_settings,
        retries=2,
        defer_model_check=True,
    )


def create_agent(
    mode: AgentMode,
    settings: FridaySettings,
    context: WorkspaceContext,
) -> Agent[AgentDeps, str]:
    """Build a pydantic-ai Agent configured for the given mode.

    Tries the default model first. If it fails (missing API key),
    falls back to fallback_model from config.
    """
    mode_config = MODE_CONFIGS[mode]
    tools = [TOOL_FUNCTIONS[name] for name in mode_config.tool_names]
    system_prompt = f'{load_prompt(mode)}\n\n## Workspace\n{context.render()}'
    model_settings = _build_model_settings(mode_config)

    model_name = mode_config.model or settings.default_model
    try:
        model = _resolve_model(model_name, settings)
        return _build_agent(model, system_prompt, tools, model_settings)
    except UserError:
        if settings.fallback_model and settings.fallback_model != model_name:
            log.info(
                'Model %s unavailable, falling back to %s', model_name, settings.fallback_model
            )
            model = _resolve_model(settings.fallback_model, settings)
            return _build_agent(model, system_prompt, tools, model_settings)
        raise
