"""Shell tool — run commands with timeout and containment."""

import subprocess

from pydantic_ai import RunContext

from friday.agent.deps import AgentDeps
from friday.cli.confirm import confirm_shell
from friday.domain.permissions import clip


async def run_shell(ctx: RunContext[AgentDeps], command: str, timeout: int = 30) -> str:
    """Run a shell command in the workspace root. Timeout in seconds (max 120)."""
    if not confirm_shell(command, ctx.deps.settings.approval_policy):
        return 'error: user denied run_shell'

    timeout = min(timeout, 120)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=ctx.deps.workspace_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = result.stdout + result.stderr
        exit_info = f'[exit {result.returncode}]'
        return clip(f'{exit_info}\n{output.strip()}')
    except subprocess.TimeoutExpired:
        return f'error: command timed out after {timeout}s'
