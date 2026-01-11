import asyncio
from typing import Any


class AgentQueue:
    """A simple asynchronous message queue for the agent to consume."""

    def __init__(self):
        self.queue = asyncio.Queue()

    async def put(self, message: Any):
        """Put a message into the queue."""
        await self.queue.put(message)

    async def get(self) -> Any:
        """Get a message from the queue."""
        return await self.queue.get()

    def task_done(self):
        """Mark the last retrieved task as done."""
        self.queue.task_done()

    @property
    def empty(self) -> bool:
        return self.queue.empty()


# Global queue instance
agent_queue = AgentQueue()
