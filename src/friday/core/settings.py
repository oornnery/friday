"""Settings loader for Friday."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from dotenv import find_dotenv, load_dotenv

VoiceMode = Literal["ptt", "vad", "both"]


@dataclass(frozen=True)
class Settings:
    workspace_path: Path
    data_dir: Path
    broker_url: str | None
    voice_mode: VoiceMode
    session_id: str
    mcp_config_path: Path
    perplexity_api_key: str | None
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_model: str
    openrouter_timeout_s: float
    openrouter_vision_model: str
    perplexity_base_url: str
    perplexity_model: str
    perplexity_timeout_s: float
    perplexity_max_results: int
    web_search_provider: str
    web_search_user_agent: str
    brave_search_api_key: str | None
    brave_search_base_url: str
    brave_search_timeout_s: float
    brave_search_max_results: int
    ddg_max_results: int
    voice_input_device: str | None
    voice_output_device: str | None
    voice_sample_rate: int
    voice_frame_ms: int
    voice_vad_sensitivity: int
    voice_vad_min_speech_ms: int
    voice_vad_silence_ms: int
    voice_stt_model: str
    voice_stt_device: str
    voice_stt_compute_type: str
    voice_stt_language: str | None
    voice_stt_beam_size: int
    voice_stt_partial_interval_s: float
    voice_tts_enabled: bool
    voice_tts_rate: int
    voice_tts_volume: float
    voice_tts_voice: str | None


def _parse_voice_mode(value: str) -> VoiceMode:
    normalized = value.strip().lower()
    if normalized not in {"ptt", "vad", "both"}:
        raise ValueError(f"Invalid voice mode: {value}")
    return cast(VoiceMode, normalized)


def load_settings() -> Settings:
    load_dotenv(find_dotenv(usecwd=True))
    workspace_path = Path(
        os.environ.get("FRIDAY_WORKSPACE", "~/.friday/workspace")
    ).expanduser()
    data_dir = Path(os.environ.get("FRIDAY_DATA_DIR", "~/.friday")).expanduser()
    broker_url = os.environ.get("FRIDAY_BROKER_URL")
    voice_mode = _parse_voice_mode(os.environ.get("FRIDAY_VOICE_MODE", "ptt"))
    session_id = os.environ.get("FRIDAY_SESSION_ID", uuid.uuid4().hex)
    default_mcp = str(data_dir / "mcp.json")
    mcp_config_path = Path(
        os.environ.get("FRIDAY_MCP_CONFIG", default_mcp)
    ).expanduser()
    perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    openrouter_base_url = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    openrouter_model = os.environ.get("OPENROUTER_MODEL", "openrouter/auto")
    openrouter_timeout_s = _parse_float(
        os.environ.get("OPENROUTER_TIMEOUT_S", "30"), "OPENROUTER_TIMEOUT_S"
    )
    openrouter_vision_model = os.environ.get(
        "OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini"
    )
    perplexity_base_url = os.environ.get(
        "PERPLEXITY_BASE_URL", "https://api.perplexity.ai"
    )
    perplexity_model = os.environ.get("PERPLEXITY_MODEL", "sonar")
    perplexity_timeout_s = _parse_float(
        os.environ.get("PERPLEXITY_TIMEOUT_S", "15"), "PERPLEXITY_TIMEOUT_S"
    )
    perplexity_max_results = _parse_int(
        os.environ.get("PERPLEXITY_MAX_RESULTS", "5"), "PERPLEXITY_MAX_RESULTS"
    )
    web_search_provider = os.environ.get("FRIDAY_WEB_SEARCH_PROVIDER", "auto")
    web_search_user_agent = os.environ.get(
        "FRIDAY_WEB_SEARCH_UA", "FridayBot/0.1 (+https://localhost)"
    )
    brave_search_api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    brave_search_base_url = os.environ.get(
        "BRAVE_SEARCH_BASE_URL", "https://api.search.brave.com"
    )
    brave_search_timeout_s = _parse_float(
        os.environ.get("BRAVE_SEARCH_TIMEOUT_S", "10"), "BRAVE_SEARCH_TIMEOUT_S"
    )
    brave_search_max_results = _parse_int(
        os.environ.get("BRAVE_SEARCH_MAX_RESULTS", "5"), "BRAVE_SEARCH_MAX_RESULTS"
    )
    ddg_max_results = _parse_int(
        os.environ.get("DDG_MAX_RESULTS", "5"), "DDG_MAX_RESULTS"
    )
    voice_input_device = os.environ.get("FRIDAY_VOICE_INPUT_DEVICE") or None
    voice_output_device = os.environ.get("FRIDAY_VOICE_OUTPUT_DEVICE") or None
    voice_sample_rate = _parse_int(
        os.environ.get("FRIDAY_VOICE_SAMPLE_RATE", "16000"),
        "FRIDAY_VOICE_SAMPLE_RATE",
    )
    voice_frame_ms = _parse_int(
        os.environ.get("FRIDAY_VOICE_FRAME_MS", "30"), "FRIDAY_VOICE_FRAME_MS"
    )
    if voice_frame_ms not in {10, 20, 30}:
        raise ValueError("FRIDAY_VOICE_FRAME_MS must be 10, 20, or 30")
    voice_vad_sensitivity = _parse_int(
        os.environ.get("FRIDAY_VAD_SENSITIVITY", "2"), "FRIDAY_VAD_SENSITIVITY"
    )
    voice_vad_min_speech_ms = _parse_int(
        os.environ.get("FRIDAY_VAD_MIN_SPEECH_MS", "180"),
        "FRIDAY_VAD_MIN_SPEECH_MS",
    )
    voice_vad_silence_ms = _parse_int(
        os.environ.get("FRIDAY_VAD_SILENCE_MS", "600"),
        "FRIDAY_VAD_SILENCE_MS",
    )
    voice_stt_model = os.environ.get("FRIDAY_STT_MODEL", "base")
    voice_stt_device = os.environ.get("FRIDAY_STT_DEVICE", "cpu")
    voice_stt_compute_type = os.environ.get("FRIDAY_STT_COMPUTE_TYPE", "int8")
    voice_stt_language = os.environ.get("FRIDAY_STT_LANGUAGE") or None
    voice_stt_beam_size = _parse_int(
        os.environ.get("FRIDAY_STT_BEAM_SIZE", "5"),
        "FRIDAY_STT_BEAM_SIZE",
    )
    voice_stt_partial_interval_s = _parse_float(
        os.environ.get("FRIDAY_STT_PARTIAL_INTERVAL_S", "1.5"),
        "FRIDAY_STT_PARTIAL_INTERVAL_S",
    )
    voice_tts_enabled = _parse_bool(
        os.environ.get("FRIDAY_TTS_ENABLED", "true"), "FRIDAY_TTS_ENABLED"
    )
    voice_tts_rate = _parse_int(
        os.environ.get("FRIDAY_TTS_RATE", "180"), "FRIDAY_TTS_RATE"
    )
    voice_tts_volume = _parse_float(
        os.environ.get("FRIDAY_TTS_VOLUME", "0.9"), "FRIDAY_TTS_VOLUME"
    )
    voice_tts_voice = os.environ.get("FRIDAY_TTS_VOICE") or None

    return Settings(
        workspace_path=workspace_path,
        data_dir=data_dir,
        broker_url=broker_url,
        voice_mode=voice_mode,
        session_id=session_id,
        mcp_config_path=mcp_config_path,
        perplexity_api_key=perplexity_api_key,
        openrouter_api_key=openrouter_api_key,
        openrouter_base_url=openrouter_base_url,
        openrouter_model=openrouter_model,
        openrouter_timeout_s=openrouter_timeout_s,
        openrouter_vision_model=openrouter_vision_model,
        perplexity_base_url=perplexity_base_url,
        perplexity_model=perplexity_model,
        perplexity_timeout_s=perplexity_timeout_s,
        perplexity_max_results=perplexity_max_results,
        web_search_provider=web_search_provider,
        web_search_user_agent=web_search_user_agent,
        brave_search_api_key=brave_search_api_key,
        brave_search_base_url=brave_search_base_url,
        brave_search_timeout_s=brave_search_timeout_s,
        brave_search_max_results=brave_search_max_results,
        ddg_max_results=ddg_max_results,
        voice_input_device=voice_input_device,
        voice_output_device=voice_output_device,
        voice_sample_rate=voice_sample_rate,
        voice_frame_ms=voice_frame_ms,
        voice_vad_sensitivity=voice_vad_sensitivity,
        voice_vad_min_speech_ms=voice_vad_min_speech_ms,
        voice_vad_silence_ms=voice_vad_silence_ms,
        voice_stt_model=voice_stt_model,
        voice_stt_device=voice_stt_device,
        voice_stt_compute_type=voice_stt_compute_type,
        voice_stt_language=voice_stt_language,
        voice_stt_beam_size=voice_stt_beam_size,
        voice_stt_partial_interval_s=voice_stt_partial_interval_s,
        voice_tts_enabled=voice_tts_enabled,
        voice_tts_rate=voice_tts_rate,
        voice_tts_volume=voice_tts_volume,
        voice_tts_voice=voice_tts_voice,
    )


def _parse_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {value}") from exc


def _parse_float(value: str, name: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {value}") from exc


def _parse_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {value}")
