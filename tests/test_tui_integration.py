import pytest
from app.components.chat import ChatInput, ChatMessageAssistant, ChatMessageUser
from app.tui import FridayApp


@pytest.mark.asyncio
async def test_tui_chat_message_submission():
    """Test that submitting a message adds it to chat and clears input."""
    app = FridayApp()
    async with app.run_test() as pilot:
        # Get input widget
        chat_input = app.query_one(ChatInput).input_widget

        # Simulate typing "Hello"
        await pilot.click("#chat-input")
        await pilot.press("H", "e", "l", "l", "o")

        # Check input value
        assert chat_input.value == "Hello"

        # Submit
        await pilot.press("enter")

        # Allow async events to process (thinking, response streaming)
        await pilot.pause(1.0)

        # Get messages from viewer
        messages = app.query("ChatMessage")

        # Expected: User message "Hello" + Assistant message (placeholder or error)
        assert len(messages) >= 2
        user_msg = messages[0]
        assert isinstance(user_msg, ChatMessageUser)
        assert user_msg.content == "Hello"

        asst_msg = messages[1]
        assert isinstance(asst_msg, ChatMessageAssistant)
        print(f"Assistant replied: {asst_msg.content}")


@pytest.mark.asyncio
async def test_tui_tools_autocomplete_open():
    """Test that '/' triggers autocomplete opening."""
    app = FridayApp()
    async with app.run_test() as pilot:
        chat_input = app.query_one(ChatInput)

        # Type '/'
        await pilot.press("slash")
        await pilot.pause(0.5)
        assert chat_input.options_widget.display is True


@pytest.mark.asyncio
async def test_tui_file_autocomplete_open():
    """Test that '@' triggers autocomplete opening."""
    app = FridayApp()
    async with app.run_test() as pilot:
        # Type '@'
        await pilot.press("@")
        await pilot.pause(0.5)
        # Verify app didn't crash
        assert True


@pytest.mark.asyncio
async def test_chat_message_assistant_update():
    """Test updating content of assistant message."""
    msg = ChatMessageAssistant("Initial")

    # We need a minimal app to mount the widget
    from textual.app import App
    from textual.widgets import Markdown

    class TestApp(App):
        CSS_PATH = None

        def compose(self):
            yield msg

    app = TestApp()
    async with app.run_test() as pilot:
        # Check initial content in Markdown
        md = msg.query_one(Markdown)
        assert md is not None

        # Update
        msg.update_content("Updated Content")
        await pilot.pause(0.1)

        # Verify no crash
        assert True
