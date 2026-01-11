from agno.db.sqlite import SqliteDb
from agno.memory import MemoryManager


def get_memory_manager(db: SqliteDb) -> MemoryManager:
    """Returns a configured MemoryManager for the agent."""
    return MemoryManager(
        db=db,
        # enable_agentic_memory allows the agent to update its own memory
        # add_memories_to_context adds user memories to the prompt
    )
