"""Router agent — conversational front that delegates to sub-agents."""

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UserError
from pydantic_ai.settings import ModelSettings

from friday.agent.context import WorkspaceContext
from friday.agent.core import TOOL_FUNCTIONS, _build_agent, _resolve_model, create_agent
from friday.agent.deps import AgentDeps
from friday.agent.modes import _PROMPTS_DIR, _parse_prompt_file
from friday.agent.run_stats import record_turn_result
from friday.domain.models import AgentMode
from friday.infra.config import FridaySettings


def _load_router_prompt() -> str:
    """Load the router system prompt from its .md file."""
    _, body = _parse_prompt_file(_PROMPTS_DIR / 'router.md')
    return body


def _load_router_meta() -> dict:
    meta, _ = _parse_prompt_file(_PROMPTS_DIR / 'router.md')
    return meta


async def _run_sub_agent(
    ctx: RunContext[AgentDeps],
    mode: AgentMode,
    task: str,
) -> str:
    """Spawn a sub-agent, run the task, return its output."""
    agent = create_agent(mode, ctx.deps.settings, ctx.deps.context)
    result = await agent.run(task, deps=ctx.deps)
    record_turn_result(ctx.deps.turn_stats, result, ctx.deps.settings.default_model)
    return result.output


# ── Delegate tools ─────────────────────────────────────────────


async def delegate_code(ctx: RunContext[AgentDeps], task: str) -> str:
    """Delegate a coding task (write, edit, refactor, test code).

    Provide a clear, specific description of what needs to be done.
    Include file paths, function names, and relevant context.
    """
    return await _run_sub_agent(ctx, AgentMode.CODE, task)


async def delegate_reader(ctx: RunContext[AgentDeps], task: str) -> str:
    """Delegate a reading/analysis task (explain code, trace logic).

    Specify which files or functions to analyze and what question
    to answer about them.
    """
    return await _run_sub_agent(ctx, AgentMode.READER, task)


async def delegate_writer(ctx: RunContext[AgentDeps], task: str) -> str:
    """Delegate a writing task (generate docs, READMEs, text).

    Describe what documentation to create, for which code,
    and in what style.
    """
    return await _run_sub_agent(ctx, AgentMode.WRITE, task)


async def delegate_debug(ctx: RunContext[AgentDeps], task: str) -> str:
    """Delegate a debugging task (diagnose errors, trace bugs).

    Include the error message, stack trace, or symptom description.
    Mention which command failed or which test is broken.
    """
    return await _run_sub_agent(ctx, AgentMode.DEBUG, task)


# ── Delegate tool registry ─────────────────────────────────────

DELEGATE_TOOLS = {
    'delegate_code': delegate_code,
    'delegate_reader': delegate_reader,
    'delegate_writer': delegate_writer,
    'delegate_debug': delegate_debug,
}


def create_router_agent(
    settings: FridaySettings,
    context: WorkspaceContext,
) -> Agent[AgentDeps, str]:
    """Build the router agent — the main conversational interface."""
    meta = _load_router_meta()
    prompt = _load_router_prompt()

    # Router tools = delegate tools + direct tools from frontmatter
    tool_names = meta.get('tools', [])
    tools = []
    for name in tool_names:
        if name in DELEGATE_TOOLS:
            tools.append(DELEGATE_TOOLS[name])
        elif name in TOOL_FUNCTIONS:
            tools.append(TOOL_FUNCTIONS[name])

    system_prompt = f'{prompt}\n\n## Workspace\n{context.render()}'

    thinking = meta.get('thinking', False)
    model_settings: ModelSettings | None = None
    if thinking:
        model_settings = ModelSettings(thinking=thinking)

    model_name = meta.get('model') or settings.default_model
    try:
        model = _resolve_model(model_name, settings)
        return _build_agent(model, system_prompt, tools, model_settings)
    except UserError:
        if settings.fallback_model and settings.fallback_model != model_name:
            model = _resolve_model(settings.fallback_model, settings)
            return _build_agent(model, system_prompt, tools, model_settings)
        raise
