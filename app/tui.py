import asyncio

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from components.chat import (
    ChatInput,
    ChatMessageAssistant,
    ChatMessageConfirm,
    ChatMessageTool,
    ChatMessageUser,
    ChatStatus,
    ChatViewer,
)


class FridayApp(App):
    CSS_PATH = "style.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield ChatViewer()
        yield ChatStatus(id="status")
        yield ChatInput()
        yield Footer()

    def on_mount(self) -> None:
        ci = self.query_one(ChatInput)
        ci.tool_suggestions = [("/tool-a", "Tool A"), ("/search", "Google")]
        ci.file_suggestions = ["main.py", "readme.md"]
        self.query_one(ChatStatus).status = "Ready"

        # Demo messages
        viewer = self.query_one(ChatViewer)
        viewer.add_message(ChatMessageUser("Hello! Show me valid message types."))
        viewer.add_message(
            ChatMessageAssistant(
                "I can show you tools and confirmations.",
                thinking="Demoing features...",
                cost=0.0001,
                tokens=45,
            )
        )
        viewer.add_message(
            ChatMessageTool("search_web", "Found 5 results for 'textual'.", "Tool log")
        )
        viewer.add_message(ChatMessageConfirm("Delete all files?"))

    async def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        self.query_one(ChatViewer).add_message(ChatMessageUser(event.value))
        self.query_one(ChatInput).clear()
        self.query_one(ChatStatus).status = "Thinking..."
        await asyncio.sleep(2)
        self.query_one(ChatStatus).status = "Ready"
        self.query_one(ChatViewer).add_message(
            ChatMessageAssistant(
                "I'm ready!", thinking="Thinking...", cost=0.0001, tokens=45
            )
        )

    @on(ChatMessageConfirm.Confirmed)
    async def on_confirm(self, event: ChatMessageConfirm.Confirmed) -> None:
        response = "User confirmed: Yes" if event.result else "User confirmed: No"
        self.query_one(ChatViewer).add_message(ChatMessageUser(response))


if __name__ == "__main__":
    app = FridayApp()
    app.run()
