"""Task scheduler loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from friday.bus import topics
from friday.bus.broker import EventBus
from friday.bus.schemas import OutputText, new_message_id
from friday.core.scheduling import next_run_ts
from friday.storage.db import connect
from friday.storage.repos import tasks as tasks_repo
from friday.utils.time import now_ts


@dataclass
class TaskScheduler:
    db_path: Path
    bus: EventBus
    session_id: str
    interval_s: float = 30.0

    _running: bool = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            await self._tick()
            await asyncio.sleep(self.interval_s)

    def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        now = now_ts()
        due = await asyncio.to_thread(self._load_due_tasks, now)
        for task in due:
            await self._emit_task(task)
            await asyncio.to_thread(self._mark_task_run, task.id, task.schedule, now)

    def _load_due_tasks(self, now: int) -> list[tasks_repo.TaskRecord]:
        with connect(self.db_path) as conn:
            return tasks_repo.due_tasks(conn, now)

    async def _emit_task(self, task: tasks_repo.TaskRecord) -> None:
        payload = task.payload or {}
        message = payload.get("message") or task.title
        text = f"Task due: {message}"
        output = OutputText(
            session_id=self.session_id,
            message_id=new_message_id(),
            ts=now_ts(),
            text=text,
        )
        await self.bus.publish(topics.OUTPUT_TEXT, output)

    def _mark_task_run(self, task_id: str, schedule: str, last_run: int) -> None:
        next_run = next_run_ts(schedule, last_run)
        with connect(self.db_path) as conn:
            if next_run is None:
                tasks_repo.disable_task(conn, task_id)
                tasks_repo.update_task_run(conn, task_id, last_run, None)
                return
            tasks_repo.update_task_run(conn, task_id, last_run, next_run)
