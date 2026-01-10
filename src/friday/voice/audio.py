"""Audio input/output utilities."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from typing import Protocol


class AudioStream(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


@dataclass
class AudioConfig:
    sample_rate: int
    frame_ms: int
    input_device: str | None = None
    output_device: str | None = None

    @property
    def frame_size(self) -> int:
        return int(self.sample_rate * self.frame_ms / 1000)


class AudioInput:
    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._stream: AudioStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        if self._stream is not None:
            return
        self._loop = asyncio.get_running_loop()
        sd = _require_sounddevice()
        self._stream = sd.RawInputStream(
            samplerate=self._config.sample_rate,
            blocksize=self._config.frame_size,
            channels=1,
            dtype="int16",
            device=self._config.input_device,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    async def frames(self) -> bytes:
        return await self._queue.get()

    def clear(self) -> None:
        while not self._queue.empty():
            self._queue.get_nowait()

    def _callback(self, indata, frames, time_info, status) -> None:
        _ = (frames, time_info, status)
        if self._loop is None:
            return
        data = bytes(indata)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, data)


class AudioOutput:
    def __init__(self, config: AudioConfig) -> None:
        self._config = config

    async def play_pcm(self, pcm: bytes) -> None:
        if not pcm:
            return
        await asyncio.to_thread(self._play_sync, pcm)

    def _play_sync(self, pcm: bytes) -> None:
        np = _require_numpy()
        sd = _require_sounddevice()
        audio = np.frombuffer(pcm, dtype=np.int16)
        sd.play(
            audio,
            samplerate=self._config.sample_rate,
            device=self._config.output_device,
            blocking=True,
        )


def _require_numpy():
    try:
        return importlib.import_module("numpy")
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("numpy is required for audio playback") from exc


def _require_sounddevice():
    try:
        return importlib.import_module("sounddevice")
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("sounddevice is required for audio input/output") from exc
