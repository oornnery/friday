"""Screenshot tools backed by mss and OpenRouter."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

import httpx
import mss

from friday.storage.db import connect
from friday.storage.repos import artifacts as artifacts_repo
from friday.utils.time import now_ts


@dataclass(frozen=True)
class ScreenshotService:
    db_path: Path
    artifacts_dir: Path
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_vision_model: str
    openrouter_timeout_s: float

    def capture(self) -> str:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot_{now_ts()}.png"
        path = self.artifacts_dir / filename

        with mss.mss() as grabber:
            grabber.shot(output=str(path))

        self._record_artifact(path)
        return str(path)

    async def describe(self, file_path: str) -> str:
        if not self.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        if not self.openrouter_vision_model:
            raise RuntimeError("OPENROUTER_VISION_MODEL is not set")

        image_bytes = Path(file_path).read_bytes()
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.openrouter_vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Describe the screenshot succinctly.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this screenshot."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded}"},
                        },
                    ],
                },
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.openrouter_base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=self.openrouter_timeout_s) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = _first_choice_content(data)
        if not content:
            raise RuntimeError("No description returned from OpenRouter")
        return content

    def _record_artifact(self, path: Path) -> None:
        with connect(self.db_path) as conn:
            artifacts_repo.add_artifact(
                conn,
                artifacts_repo.Artifact(
                    id=f"artifact_{now_ts()}",
                    type="screenshot",
                    path=str(path),
                    meta=None,
                    ts=now_ts(),
                ),
            )


def _first_choice_content(payload: dict) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return None
