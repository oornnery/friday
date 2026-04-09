"""Popconfirm — interactive approval for risky tool calls."""

from __future__ import annotations

from rich.panel import Panel

from friday.cli.output import console
from friday.cli.theme import COLORS
from friday.domain.models import ApprovalPolicy


def confirm_action(
    tool_name: str,
    description: str,
    detail: str = '',
    policy: ApprovalPolicy = ApprovalPolicy.ASK,
) -> bool:
    """Prompt the user to approve a risky action."""
    if policy == ApprovalPolicy.AUTO:
        return True
    if policy == ApprovalPolicy.NEVER:
        return False

    content = f'[warning]{tool_name}[/warning]: {description}'
    if detail:
        content += f'\n\n{detail}'

    console.print()
    console.print(
        Panel(
            content,
            title='[warning]Confirm[/warning]',
            border_style=COLORS['warning'],
            padding=(0, 1),
        )
    )

    try:
        answer = console.input('[muted]Allow? [y/N] [/muted]').strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print('[error]Denied[/error]')
        return False

    approved = answer in {'y', 'yes'}
    if approved:
        console.print('[success]Approved[/success]')
    else:
        console.print('[error]Denied[/error]')
    return approved


def confirm_write(path: str, content: str, policy: ApprovalPolicy) -> bool:
    """Confirm a file write operation."""
    preview = content[:500]
    if len(content) > 500:
        preview += f'\n...[{len(content) - 500} more chars]'
    return confirm_action(
        'write_file',
        f'Write to [accent]{path}[/accent] ({len(content)} chars)',
        detail=preview,
        policy=policy,
    )


def confirm_patch(path: str, old: str, new: str, policy: ApprovalPolicy) -> bool:
    """Confirm a file patch operation."""
    detail = f'[error]- {old[:200]}[/error]\n[success]+ {new[:200]}[/success]'
    return confirm_action(
        'patch_file',
        f'Patch [accent]{path}[/accent]',
        detail=detail,
        policy=policy,
    )


def confirm_shell(command: str, policy: ApprovalPolicy) -> bool:
    """Confirm a shell command execution."""
    return confirm_action(
        'run_shell',
        'Execute shell command',
        detail=command,
        policy=policy,
    )
