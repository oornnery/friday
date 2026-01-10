"""Text-to-speech providers."""

from __future__ import annotations

import asyncio
import importlib
import threading
from dataclasses import dataclass


class TTSProvider:
    async def speak(self, text: str) -> None: ...

    def stop(self) -> None: ...


@dataclass(frozen=True)
class Pyttsx3Config:
    rate: int
    volume: float
    voice: str | None


class Pyttsx3TTS(TTSProvider):
    def __init__(self, config: Pyttsx3Config) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._engine = _build_engine()
        if self._engine is None:
            raise RuntimeError("pyttsx3 is not available")
        self._engine.setProperty("rate", config.rate)
        self._engine.setProperty("volume", config.volume)
        if config.voice:
            self._engine.setProperty("voice", config.voice)

    async def speak(self, text: str) -> None:
        await asyncio.to_thread(self._speak_sync, text)

    def stop(self) -> None:
        if self._engine is None:
            return
        self._engine.stop()

    def _speak_sync(self, text: str) -> None:
        if self._engine is None:
            return
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()


def _build_engine():
    try:
        module = importlib.import_module("pyttsx3")
    except Exception:
        return None
    init = getattr(module, "init", None)
    if init is None:
        return None
    return init()
