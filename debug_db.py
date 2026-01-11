import uuid

from app.agent.agents import get_db, get_session_summary, list_sessions


def test_db():
    get_db()
    session_id = str(uuid.uuid4())
    print(f"Testing with session_id: {session_id}")

    # Check if we can rename/create
    from app.agent.agents import rename_session

    rename_session(session_id, "Test Session")
    print("Renamed session.")

    # List sessions
    sessions = list_sessions()
    print(f"Sessions count: {len(sessions)}")
    for s in sessions:
        print(f"- {s.get('session_id')}: {s.get('session_data')}")

    # Get summary (should be empty for new)
    summary = get_session_summary(session_id)
    print(f"Summary: '{summary}'")


if __name__ == "__main__":
    test_db()
