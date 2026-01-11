"""Test SmartInput widget keyboard behavior."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import ContentSwitcher, Footer, Input

from friday.app.tui import SmartInput


class SmartInputTestApp(App):
    """Test app with SmartInput in ContentSwitcher."""

    AUTO_FOCUS = "#smart-input-field"

    def compose(self) -> ComposeResult:
        with ContentSwitcher(initial="input", id="input-switcher"):
            yield SmartInput(placeholder="Type a message...", id="input")
        yield Footer()


@pytest.mark.asyncio
async def test_smartinput_backspace():
    """Test that backspace works in SmartInput."""
    app = SmartInputTestApp()
    async with app.run_test() as pilot:
        # Type some text
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause()

        inp = app.query_one("#smart-input-field", Input)
        assert inp.value == "hello", f"Expected 'hello', got {inp.value!r}"

        # Press backspace
        await pilot.press("backspace")
        await pilot.pause()

        assert inp.value == "hell", (
            f"Backspace failed: expected 'hell', got {inp.value!r}"
        )


@pytest.mark.asyncio
async def test_smartinput_enter_submits():
    """Test that enter submits the input value."""
    submitted: list[str] = []

    class TestApp(SmartInputTestApp):
        def on_smart_input_submitted(self, event: SmartInput.Submitted) -> None:
            submitted.append(event.value)

    app = TestApp()

    async with app.run_test() as pilot:
        # Type some text
        await pilot.press("t", "e", "s", "t")
        await pilot.pause()

        inp = app.query_one("#smart-input-field", Input)
        assert inp.value == "test"

        # Press enter
        await pilot.press("enter")
        await pilot.pause()

        assert submitted == ["test"], f"Enter/submit failed: {submitted!r}"


@pytest.mark.asyncio
async def test_smartinput_multiple_backspaces():
    """Test multiple backspace presses work correctly."""
    app = SmartInputTestApp()
    async with app.run_test() as pilot:
        # Type some text
        await pilot.press("a", "b", "c", "d", "e")
        await pilot.pause()

        inp = app.query_one("#smart-input-field", Input)
        assert inp.value == "abcde"

        # Press backspace 3 times
        await pilot.press("backspace")
        await pilot.pause()
        assert inp.value == "abcd"

        await pilot.press("backspace")
        await pilot.pause()
        assert inp.value == "abc"

        await pilot.press("backspace")
        await pilot.pause()
        assert inp.value == "ab"
