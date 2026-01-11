"""Voice coordinator for PTT and VAD modes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from friday.bus.broker import EventBus
from friday.core.settings import Settings
from friday.voice.audio import AudioConfig
from friday.voice.ptt import PTTController
from friday.voice.realtime import RealtimeVoiceEngine, VADSettings
from friday.voice.stt import FasterWhisperConfig, FasterWhisperSTT
from friday.voice.tts import Pyttsx3Config, Pyttsx3TTS, TTSProvider
from friday.voice.vad import VADConfig


@dataclass
class VoiceController:
    settings: Settings
    bus: EventBus

    _vad_task: asyncio.Task[None] | None = None
    _vad_engine: RealtimeVoiceEngine | None = None
    _ptt: PTTController | None = None
    _tts: TTSProvider | None = None
    _error: str | None = None

    def build(self) -> None:
        if self._error is not None:
            return
        audio_config = AudioConfig(
            sample_rate=self.settings.voice_sample_rate,
            frame_ms=self.settings.voice_frame_ms,
            input_device=self.settings.voice_input_device,
            output_device=self.settings.voice_output_device,
        )
        vad_config = VADConfig(
            sensitivity=self.settings.voice_vad_sensitivity,
            sample_rate=self.settings.voice_sample_rate,
            frame_ms=self.settings.voice_frame_ms,
        )
        vad_settings = VADSettings(
            min_speech_ms=self.settings.voice_vad_min_speech_ms,
            silence_ms=self.settings.voice_vad_silence_ms,
        )
        try:
            stt = FasterWhisperSTT(
                FasterWhisperConfig(
                    model=self.settings.voice_stt_model,
                    device=self.settings.voice_stt_device,
                    compute_type=self.settings.voice_stt_compute_type,
                    language=self.settings.voice_stt_language,
                    beam_size=self.settings.voice_stt_beam_size,
                    partial_interval_s=self.settings.voice_stt_partial_interval_s,
                )
            )
        except Exception as exc:
            self._error = str(exc)
            return
        self._tts = None
        if self.settings.voice_tts_enabled:
            try:
                self._tts = Pyttsx3TTS(
                    Pyttsx3Config(
                        rate=self.settings.voice_tts_rate,
                        volume=self.settings.voice_tts_volume,
                        voice=self.settings.voice_tts_voice,
                    )
                )
            except Exception as exc:
                self._error = str(exc)
                return
        self._ptt = PTTController(
            audio_config=audio_config,
            stt=stt,
            bus=self.bus,
            session_id=self.settings.session_id,
        )
        self._vad_engine = RealtimeVoiceEngine(
            audio_config=audio_config,
            vad_config=vad_config,
            vad_settings=vad_settings,
            stt=stt,
            tts=self._tts,
            bus=self.bus,
            session_id=self.settings.session_id,
        )

    async def toggle_ptt(self) -> None:
        if self._ptt is None:
            self.build()
        if self._error is not None:
            raise RuntimeError(self._error)
        if self._ptt is None:
            return
        await self._ptt.toggle()

    async def toggle_vad(self) -> None:
        if self._vad_engine is None:
            self.build()
        if self._error is not None:
            raise RuntimeError(self._error)
        if self._vad_engine is None:
            return
        if self._vad_task and not self._vad_task.done():
            self._vad_engine.stop()
            self._vad_task.cancel()
            self._vad_task = None
            return
        self._vad_task = asyncio.create_task(self._vad_engine.run())

    async def speak(self, text: str) -> None:
        if self._vad_engine is None:
            self.build()
        if self._error is not None:
            raise RuntimeError(self._error)
        if self._vad_engine is None:
            return
        await self._vad_engine.speak(text)

    def stop_speaking(self) -> None:
        if self._vad_engine is None:
            return
        self._vad_engine.stop_speaking()

    def ptt_recording(self) -> bool:
        return bool(self._ptt and self._ptt.is_recording())

    def vad_running(self) -> bool:
        return bool(self._vad_task and not self._vad_task.done())

    def error(self) -> str | None:
        return self._error

    async def stop(self) -> None:
        """Stop all voice activities and clean up resources."""
        # Stop VAD if running
        if self._vad_task and not self._vad_task.done():
            if self._vad_engine:
                self._vad_engine.stop()
            self._vad_task.cancel()
            self._vad_task = None

        # Stop PTT if recording
        if self._ptt and self._ptt.is_recording():
            self._ptt.stop()

        # Stop any ongoing speech
        if self._vad_engine:
            self._vad_engine.stop_speaking()
