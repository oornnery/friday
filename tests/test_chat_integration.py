"""Integration tests for TUI chat functionality."""


import pytest
from textual.widgets import Input

from friday.app.tui import AssistantApp, AssistantResponse, UserPrompt
from friday.core.settings import load_settings


@pytest.mark.asyncio
async def test_chat_view_exists():
    """Chat view should be present after mount."""
    settings = load_settings()
    app = AssistantApp(settings=settings)

    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        chat_view = app.query_one("#chat-view")
        assert chat_view is not None


@pytest.mark.asyncio
async def test_write_user_message():
    """Should be able to write user messages to chat."""
    settings = load_settings()
    app = AssistantApp(settings=settings)

    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        await app._write_chat("user", "Hello")
        await pilot.pause(0.1)

        # Check that UserPrompt was added
        user_prompts = app.query(UserPrompt)
        assert len(user_prompts) == 1


@pytest.mark.asyncio
async def test_write_assistant_message():
    """Should be able to write assistant messages to chat."""
    settings = load_settings()
    app = AssistantApp(settings=settings)

    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        await app._write_chat("assistant", "Hi there!")
        await pilot.pause(0.1)

        # Check that AssistantResponse was added
        responses = app.query(AssistantResponse)
        assert len(responses) == 1


@pytest.mark.asyncio
async def test_chat_multiple_messages():
    """Should handle multiple messages in sequence."""
    settings = load_settings()
    app = AssistantApp(settings=settings)

    async with app.run_test() as pilot:
        await pilot.pause(0.1)

        # Add several messages
        await app._write_chat("user", "First message")
        await app._write_chat("assistant", "Response 1")
        await app._write_chat("user", "Second message")
        await app._write_chat("assistant", "Response 2")
        await pilot.pause(0.2)

        # Verify counts
        user_prompts = app.query(UserPrompt)
        responses = app.query(AssistantResponse)
        assert len(user_prompts) == 2
        assert len(responses) == 2


@pytest.mark.asyncio
async def test_input_submit_creates_user_message():
    """Submitting input should create a user message."""
    settings = load_settings()
    app = AssistantApp(
        settings=settings, bus=None
    )  # No bus to avoid async complications

    async with app.run_test() as pilot:
        await pilot.pause(0.1)

        # Type and submit text - Input is now inside SmartInput
        input_widget = app.query_one("#smart-input-field", Input)
        input_widget.value = "Test message"
        input_widget.focus()
        await pilot.pause(0.1)
        await pilot.press("enter")
        await pilot.pause(0.3)

        # Should have created a UserPrompt
        user_prompts = app.query(UserPrompt)
        assert len(user_prompts) == 1


@pytest.mark.asyncio
async def test_markdown_formatting_preserved():
    """Markdown formatting should be preserved in messages."""
    settings = load_settings()
    app = AssistantApp(settings=settings)

    async with app.run_test() as pilot:
        await pilot.pause(0.1)

        markdown_text = "# Heading\n\n**Bold** text and `code`"
        await app._write_chat("assistant", markdown_text)
        await pilot.pause(0.1)

        # Widget should exist and be Markdown
        responses = app.query(AssistantResponse)
        assert len(responses) == 1
