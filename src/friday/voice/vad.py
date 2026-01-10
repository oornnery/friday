"""Voice activity detection implementations."""

from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class VADConfig:
    sensitivity: int
    sample_rate: int
    frame_ms: int
    energy_threshold: float = 0.02


class WebRtcVAD:
    def __init__(self, config: VADConfig) -> None:
        self._config = config
        self._vad = _build_webrtcvad(config.sensitivity)

    def is_speech(self, frame: bytes) -> bool:
        if self._vad is None:
            return _energy_vad(frame, self._config)
        return bool(self._vad.is_speech(frame, self._config.sample_rate))


def _build_webrtcvad(sensitivity: int):
    try:
        module = importlib.import_module("webrtcvad")
    except Exception:
        return None
    sensitivity = max(0, min(3, sensitivity))
    return module.Vad(sensitivity)


def _energy_vad(frame: bytes, config: VADConfig) -> bool:
    np = _require_numpy()
    audio = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
    if audio.size == 0:
        return False
    rms = np.sqrt(np.mean(np.square(audio)))
    return rms >= config.energy_threshold


def _require_numpy():
    try:
        return importlib.import_module("numpy")
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("numpy is required for VAD fallback") from exc
