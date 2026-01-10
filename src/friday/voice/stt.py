"""Speech-to-text providers."""

from __future__ import annotations

import asyncio
import importlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


class STTProvider(Protocol):
    async def transcribe(self, audio: bytes, sample_rate: int) -> str: ...

    def stream_transcribe(
        self, frames: list[bytes], sample_rate: int
    ) -> AsyncIterator[str]: ...


@dataclass(frozen=True)
class FasterWhisperConfig:
    model: str
    device: str
    compute_type: str
    language: str | None
    beam_size: int
    partial_interval_s: float


class FasterWhisperSTT(STTProvider):
    def __init__(self, config: FasterWhisperConfig) -> None:
        self._config = config
        self._model = _load_whisper_model(
            config.model, config.device, config.compute_type
        )
        if self._model is None:
            raise RuntimeError("faster-whisper is not available")

    async def transcribe(self, audio: bytes, sample_rate: int) -> str:
        return await asyncio.to_thread(self._transcribe_sync, audio, sample_rate)

    async def stream_transcribe(
        self, frames: list[bytes], sample_rate: int
    ) -> AsyncIterator[str]:
        if not frames:
            return
        buffer = bytearray()
        next_emit = time.monotonic() + self._config.partial_interval_s
        last_text = ""
        for frame in frames:
            buffer.extend(frame)
            now = time.monotonic()
            if now < next_emit:
                continue
            next_emit = now + self._config.partial_interval_s
            text = await self.transcribe(bytes(buffer), sample_rate)
            if text and text != last_text:
                last_text = text
                yield text
        final_text = await self.transcribe(bytes(buffer), sample_rate)
        if final_text and final_text != last_text:
            yield final_text

    def _transcribe_sync(self, audio: bytes, sample_rate: int) -> str:
        if self._model is None:
            raise RuntimeError("faster-whisper is not available")
        np = _require_numpy()
        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(
            audio_np,
            language=self._config.language,
            beam_size=self._config.beam_size,
            vad_filter=True,
        )
        parts = [segment.text.strip() for segment in segments if segment.text]
        return " ".join([part for part in parts if part]).strip()


def _load_whisper_model(model: str, device: str, compute_type: str):
    try:
        module = importlib.import_module("faster_whisper")
    except Exception:
        return None
    whisper_model = getattr(module, "WhisperModel", None)
    if whisper_model is None:
        return None
    return whisper_model(model, device=device, compute_type=compute_type)


def _require_numpy():
    try:
        return importlib.import_module("numpy")
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("numpy is required for speech-to-text") from exc
