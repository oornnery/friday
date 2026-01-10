"""Push-to-talk controller."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from friday.bus import topics
from friday.bus.broker import EventBus
from friday.bus.schemas import InputText, new_message_id
from friday.utils.time import now_ts
from friday.voice.audio import AudioConfig, AudioInput
from friday.voice.stt import STTProvider


@dataclass
class PTTController:
    audio_config: AudioConfig
    stt: STTProvider
    bus: EventBus
    session_id: str

    _recording: bool = False
    _frames: list[bytes] | None = None
    _task: asyncio.Task[None] | None = None

    async def toggle(self) -> None:
        if self._recording:
            await self.stop()
            return
        await self.start()

    async def start(self) -> None:
        if self._recording:
            return
        self._recording = True
        self._frames = []
        audio_input = AudioInput(self.audio_config)
        audio_input.start()

        async def _collect() -> None:
            while self._recording:
                frame = await audio_input.frames()
                if self._frames is not None:
                    self._frames.append(frame)
            audio_input.stop()

        self._task = asyncio.create_task(_collect())

    async def stop(self) -> None:
        if not self._recording:
            return
        self._recording = False
        if self._task is not None:
            await self._task
        frames = self._frames or []
        self._frames = None
        if not frames:
            return
        audio = b"".join(frames)
        text = await self.stt.transcribe(audio, self.audio_config.sample_rate)
        if not text:
            return
        message = InputText(
            session_id=self.session_id,
            message_id=new_message_id(),
            ts=now_ts(),
            text=text,
            source="voice",
        )
        await self.bus.publish(topics.INPUT_TEXT, message)

    def is_recording(self) -> bool:
        return self._recording
