"""Tasks tool backed by SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.core.scheduling import next_run_ts
from friday.storage.db import connect
from friday.storage.repos import tasks as tasks_repo
from friday.utils.time import now_ts


@dataclass(frozen=True)
class TasksService:
    db_path: Path

    def create(self, title: str, schedule: str, payload: dict | None = None) -> str:
        next_run = next_run_ts(schedule, now_ts())
        if next_run is None:
            raise ValueError("Schedule does not produce a future run")
        with connect(self.db_path) as conn:
            task = tasks_repo.create_task(
                conn, title, schedule, payload=payload, next_run=next_run
            )
        return task.id

    def run(self, task_id: str) -> dict[str, str]:
        with connect(self.db_path) as conn:
            task = tasks_repo.get_task(conn, task_id)
        if task is None:
            raise ValueError("Task not found")
        return {"status": "queued", "task_id": task.id}

    def search(self, query: str) -> list[dict[str, str]]:
        q = query.strip().lower()
        tasks = self.list_tasks()
        if not q:
            return tasks
        return [task for task in tasks if q in task["title"].lower()]

    def list_tasks(self) -> list[dict[str, str]]:
        with connect(self.db_path) as conn:
            tasks = tasks_repo.list_tasks(conn)
        return [
            {
                "id": task.id,
                "title": task.title,
                "schedule": task.schedule,
                "enabled": str(task.enabled),
                "next_run": str(task.next_run) if task.next_run else "",
            }
            for task in tasks
        ]
