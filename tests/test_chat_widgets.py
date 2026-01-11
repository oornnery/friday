"""Tests for TUI chat components."""

from textual.containers import Vertical

from friday.app.tui import AssistantResponse, ChatMessage, ToolResponse, UserPrompt


def test_user_prompt_is_chat_message():
    """UserPrompt should be a ChatMessage widget."""
    widget = UserPrompt("Hello")
    assert isinstance(widget, ChatMessage)
    assert isinstance(widget, Vertical)


def test_assistant_response_is_chat_message():
    """AssistantResponse should be a ChatMessage widget."""
    widget = AssistantResponse("Hi there")
    assert isinstance(widget, ChatMessage)
    assert isinstance(widget, Vertical)


def test_tool_response_is_chat_message():
    """ToolResponse should be a ChatMessage widget."""
    widget = ToolResponse("Tool result")
    assert isinstance(widget, ChatMessage)
    assert isinstance(widget, Vertical)


def test_widgets_accept_markdown_content():
    """Widgets should accept Markdown formatted content."""
    markdown_text = "# Heading\n\n**Bold** and *italic*"
    user = UserPrompt(markdown_text)
    assistant = AssistantResponse(markdown_text)
    tool = ToolResponse(markdown_text)

    # All should be valid ChatMessage widgets
    assert isinstance(user, ChatMessage)
    assert isinstance(assistant, ChatMessage)
    assert isinstance(tool, ChatMessage)


def test_assistant_response_with_thinking():
    """AssistantResponse should accept thinking parameter."""
    widget = AssistantResponse("Response", thinking="I need to think about this...")
    assert isinstance(widget, ChatMessage)
    assert widget._thinking == "I need to think about this..."
