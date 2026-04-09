"""REPL completions — slash commands and @ file references."""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

SLASH_COMMANDS: dict[str, str] = {
    '/help': 'Show available commands',
    '/mode': 'Interactive mode picker',
    '/model': 'Interactive model picker',
    '/models': 'List all available models',
    '/session': 'Session management',
    '/clear': 'Clear conversation',
    '/quit': 'Exit Friday',
    '/exit': 'Exit Friday',
}


class FridayCompleter(Completer):
    """Completer that handles / commands and @ file paths."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> list[Completion]:
        text = document.text_before_cursor

        # Slash commands: complete when line starts with /
        if text.startswith('/'):
            return list(self._complete_slash(text))

        # @ file paths: complete the token starting with @
        at_pos = text.rfind('@')
        if at_pos >= 0:
            partial = text[at_pos + 1 :]
            return list(self._complete_files(partial, len(partial)))

        return []

    def _complete_slash(self, text: str) -> list[Completion]:
        completions = []
        for cmd, desc in SLASH_COMMANDS.items():
            if cmd.startswith(text):
                completions.append(
                    Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=desc,
                    )
                )
        return completions

    def _complete_files(self, partial: str, word_len: int) -> list[Completion]:
        """Complete file paths relative to workspace root."""
        if '/' in partial:
            parent_str, prefix = partial.rsplit('/', 1)
            search_dir = self.workspace_root / parent_str
        else:
            parent_str = ''
            prefix = partial
            search_dir = self.workspace_root

        if not search_dir.is_dir():
            return []

        completions = []
        try:
            for entry in sorted(search_dir.iterdir()):
                name = entry.name
                if name.startswith('.'):
                    continue
                if prefix and not name.lower().startswith(prefix.lower()):
                    continue

                if parent_str:
                    rel = f'{parent_str}/{name}'
                else:
                    rel = name

                if entry.is_dir():
                    display = f'{name}/'
                    rel += '/'
                else:
                    display = name

                completions.append(
                    Completion(
                        rel,
                        start_position=-word_len,
                        display=display,
                        display_meta='dir' if entry.is_dir() else '',
                    )
                )
        except PermissionError:
            pass

        return completions[:50]
