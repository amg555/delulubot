from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from .config import (
    EDGE_TTS_DEFAULT_VOICE,
    EDGE_TTS_SWEET_VOICE,
    GTTS_AVAILABLE,
    TTS_SLOW,
    VOICE_TTS_ENGINE,
    logger,
)
from .prompts import LANG_VOICE_MAP, LANG_SCRIPTS


async def transcribe_voice_file(audio_path: str) -> str:
    from .api_clients import groq_client

    if not groq_client:
        raise RuntimeError("Groq client not available for transcription")

    def _transcribe():
        with open(audio_path, "rb") as f:
            response = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
            )
        return (response.text or "").strip()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _transcribe)


async def transcribe_voice_with_retry(audio_path: str, max_retries: int = 2) -> str | None:
    last_error = None
    for attempt in range(max_retries):
        try:
            transcript = await transcribe_voice_file(audio_path)
            transcript = (transcript or "").strip()
            if transcript:
                return transcript
            logger.warning(f"Voice transcription attempt {attempt + 1} returned empty")
        except Exception as e:
            last_error = e
            logger.warning(f"Voice transcription attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    if last_error:
        logger.error(f"Voice transcription failed after {max_retries} attempts: {last_error}")
    return None


def detect_text_language(text: str) -> str:
    if not text:
        return "en"
    scores: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for lang, r in LANG_SCRIPTS.items():
            if cp in r:
                scores[lang] = scores.get(lang, 0) + 1
    if not scores:
        return "en"
    return max(scores, key=scores.get)


def resolve_voice_lang(memory: dict[str, Any], response_text: str, user_message: str) -> str:
    pref = memory.get("voice_lang", "auto")
    if pref != "auto":
        return pref if pref in LANG_VOICE_MAP else "en"
    detected = detect_text_language(response_text)
    if detected != "en":
        return detected
    return detect_text_language(user_message)


def get_tts_engine() -> str:
    if VOICE_TTS_ENGINE == "edge":
        return "edge"
    if VOICE_TTS_ENGINE == "gtts":
        return "gtts" if GTTS_AVAILABLE else "none"
    if VOICE_TTS_ENGINE == "groq":
        return "groq"
    if GTTS_AVAILABLE:
        return "gtts"
    return "none"


SWEET_VOICE_HINTS = (
    "sweet voice", "sweet", "soft voice", "softly", "romantic",
    "sweetly", "gentle", "lovingly", "cute voice", "cutely",
)


def user_requested_sweet_voice(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(h in text for h in SWEET_VOICE_HINTS)


def pick_tts_voice(memory: dict[str, Any], user_message: str) -> str:
    from .memory import save_memories, user_memories

    if user_requested_sweet_voice(user_message):
        memory["voice_style"] = "sweet"
        save_memories(user_memories)
    style = (memory.get("voice_style") or "default").lower()
    return "sweet" if style == "sweet" else "default"


async def synthesize_tts_mp3(text: str, out_path: str, voice_style: str = "default", lang: str = "en") -> None:
    engine = get_tts_engine()
    if engine == "edge":
        import edge_tts

        voice_name = EDGE_TTS_SWEET_VOICE if voice_style == "sweet" else EDGE_TTS_DEFAULT_VOICE
        edge_voice = LANG_VOICE_MAP.get(lang, {}).get("edge")
        if edge_voice:
            voice_name = edge_voice
        rate = "+5%" if voice_style == "sweet" else "+0%"
        pitch = "+5Hz" if voice_style == "sweet" else "+0Hz"
        communicator = edge_tts.Communicate(text=text, voice=voice_name, rate=rate, pitch=pitch)
        await communicator.save(out_path)
        return

    if engine == "gtts":
        from gtts import gTTS

        gtts_lang = LANG_VOICE_MAP.get(lang, {}).get("gtts", "en")
        tts = gTTS(text=text, lang=gtts_lang, slow=TTS_SLOW)
        tts.save(out_path)
        return

    raise RuntimeError("No TTS engine available")


def synthesize_tts_mp3_local(text: str, out_path: str, lang: str = "en") -> None:
    from gtts import gTTS

    if not GTTS_AVAILABLE:
        raise RuntimeError("gTTS is not installed")
    gtts_lang = LANG_VOICE_MAP.get(lang, {}).get("gtts", "en")
    tts = gTTS(text=text, lang=gtts_lang, slow=TTS_SLOW)
    tts.save(out_path)
