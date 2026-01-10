"""Realtime voice engine with VAD and barge-in."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from friday.bus import topics
from friday.bus.broker import EventBus
from friday.bus.schemas import InputText, InputTextPartial, new_message_id
from friday.utils.time import now_ts
from friday.voice.audio import AudioConfig, AudioInput
from friday.voice.stt import STTProvider
from friday.voice.tts import TTSProvider
from friday.voice.vad import VADConfig, WebRtcVAD


@dataclass
class VADSettings:
    min_speech_ms: int
    silence_ms: int


class RealtimeVoiceEngine:
    def __init__(
        self,
        audio_config: AudioConfig,
        vad_config: VADConfig,
        vad_settings: VADSettings,
        stt: STTProvider,
        tts: TTSProvider | None,
        bus: EventBus,
        session_id: str,
    ) -> None:
        self._audio_config = audio_config
        self._vad_config = vad_config
        self._vad_settings = vad_settings
        self._stt = stt
        self._tts = tts
        self._bus = bus
        self._session_id = session_id
        self._audio_input = AudioInput(audio_config)
        self._running = False
        self._speaking = False
        self._lock = asyncio.Lock()

    async def run(self) -> None:
        if self._running:
            return
        self._running = True
        self._audio_input.start()
        try:
            await self._loop()
        finally:
            self._audio_input.stop()
            self._running = False

    def stop(self) -> None:
        self._running = False

    async def speak(self, text: str) -> None:
        if self._tts is None:
            return
        async with self._lock:
            self._speaking = True
            try:
                await self._tts.speak(text)
            finally:
                self._speaking = False

    def stop_speaking(self) -> None:
        if self._tts is None:
            return
        self._tts.stop()
        self._speaking = False

    async def _loop(self) -> None:
        vad = WebRtcVAD(self._vad_config)
        buffer: list[bytes] = []
        speech_ms = 0
        silence_ms = 0
        partial_task: asyncio.Task[None] | None = None

        while self._running:
            frame = await self._audio_input.frames()
            if vad.is_speech(frame):
                speech_ms += self._vad_config.frame_ms
                silence_ms = 0
                buffer.append(frame)
                if self._speaking:
                    self.stop_speaking()

                if speech_ms >= self._vad_settings.min_speech_ms and (
                    partial_task is None or partial_task.done()
                ):
                    partial_task = asyncio.create_task(self._emit_partial(list(buffer)))
                continue

            if buffer:
                silence_ms += self._vad_config.frame_ms
                buffer.append(frame)
                if silence_ms >= self._vad_settings.silence_ms:
                    if partial_task is not None:
                        await partial_task
                    await self._emit_final(buffer)
                    buffer = []
                    speech_ms = 0
                    silence_ms = 0
                continue

    async def _emit_partial(self, frames: list[bytes]) -> None:
        async for text in self._stt.stream_transcribe(
            frames, self._audio_config.sample_rate
        ):
            if not text:
                continue
            message = InputTextPartial(
                session_id=self._session_id,
                message_id=new_message_id(),
                ts=now_ts(),
                text=text,
                source="voice",
            )
            await self._bus.publish(topics.INPUT_TEXT_PARTIAL, message)

    async def _emit_final(self, frames: list[bytes]) -> None:
        audio = b"".join(frames)
        text = await self._stt.transcribe(audio, self._audio_config.sample_rate)
        if not text:
            return
        message = InputText(
            session_id=self._session_id,
            message_id=new_message_id(),
            ts=now_ts(),
            text=text,
            source="voice",
        )
        await self._bus.publish(topics.INPUT_TEXT, message)
