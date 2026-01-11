import json
from datetime import datetime
from pathlib import Path
from typing import Any


def get_notes_file() -> Path:
    return Path("data/notes.json")


def get_tasks_file() -> Path:
    return Path("data/tasks.json")


def _ensure_file(path: Path, default_content: Any | None = None):
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    if not path.exists():
        if default_content is None:
            default_content = []
        path.write_text(json.dumps(default_content))


class NotesTools:
    def read_notes(self) -> str:
        """Read all notes from persistence."""
        file = get_notes_file()
        _ensure_file(file, [])
        return file.read_text()

    def add_note(self, content: str) -> str:
        """Add a new note."""
        file = get_notes_file()
        _ensure_file(file, [])
        notes = json.loads(file.read_text())
        notes.append(
            {"id": len(notes) + 1, "content": content, "timestamp": datetime.now().isoformat()}
        )
        file.write_text(json.dumps(notes))
        return f"Note added: {content}"


class TasksTools:
    def list_tasks(self) -> str:
        """List all tasks."""
        file = get_tasks_file()
        _ensure_file(file, [])
        return file.read_text()

    def add_task(self, title: str) -> str:
        """Add a new task."""
        file = get_tasks_file()
        _ensure_file(file, [])
        tasks = json.loads(file.read_text())
        tasks.append(
            {
                "id": len(tasks) + 1,
                "title": title,
                "completed": False,
                "timestamp": datetime.now().isoformat(),
            }
        )
        file.write_text(json.dumps(tasks))
        return f"Task added: {title}"

    def complete_task(self, task_id: int) -> str:
        """Mark a task as completed."""
        file = get_tasks_file()
        _ensure_file(file, [])
        tasks = json.loads(file.read_text())
        for task in tasks:
            if task["id"] == task_id:
                task["completed"] = True
                file.write_text(json.dumps(tasks))
                return f"Task {task_id} marked as completed."
        return f"Task {task_id} not found."


class FileTools:
    def read_file(self, filepath: str) -> str:
        """Read a file from disk."""
        path = Path(filepath)
        if not path.exists():
            return f"Error: File {filepath} does not exist."
        return path.read_text()

    def write_file(self, filepath: str, content: str) -> str:
        """Write content to a file on disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"File {filepath} written successfully."

    def list_files(self, directory: str = ".") -> str:
        """List files in a directory."""
        path = Path(directory)
        if not path.is_dir():
            return f"Error: {directory} is not a directory."
        files = [f.name for f in path.iterdir()]
        return json.dumps(files)
