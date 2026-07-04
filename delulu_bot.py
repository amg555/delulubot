#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════
SARVAM MAYA AI — DELULU BOT v4.0 (Multi-Provider Edition)
"It's me, Delulu!" 👻
100% FREE — Groq (chat) + Jina (embeddings) + Gemini (fallback)
═══════════════════════════════════════════════════
"""

import os
import json
import logging
import random
import asyncio
import re
import math
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import google.generativeai as genai
from openai import OpenAI
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    WHISPER_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    gTTS = None
    GTTS_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False



load_dotenv()

# ═══════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-2.0-flash",
    ).split(",")
]

TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))
GEMINI_QUOTA_COOLDOWN_SECONDS = int(
    os.getenv("GEMINI_QUOTA_COOLDOWN_SECONDS", "60")
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

JINA_API_KEYS = [
    k.strip()
    for k in os.getenv("JINA_API_KEYS", "").split(",")
    if k.strip()
]
JINA_MODEL = os.getenv("JINA_MODEL", "jina-embeddings-v3")

PORT = int(os.getenv("PORT", "10000"))



RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
RAG_DIR = Path(os.getenv("RAG_DIR", "rag_data"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_CHUNK_WORDS = int(os.getenv("RAG_CHUNK_WORDS", "120"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "30"))
RAG_MAX_SNIPPET_CHARS = int(os.getenv("RAG_MAX_SNIPPET_CHARS", "600"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "1.5"))
CHARACTER_BIBLE_FILE = Path(
    os.getenv(
        "CHARACTER_BIBLE_FILE",
        "rag_data/delulu_character_bible.md",
    )
)
CHARACTER_GUARD_ENABLED = os.getenv(
    "CHARACTER_GUARD_ENABLED",
    "true",
).lower() in ("1", "true", "yes", "on")
CHARACTER_GUARD_RETRIES = int(
    os.getenv("CHARACTER_GUARD_RETRIES", "0")
)
PERSONAL_FACTS_LIMIT = int(
    os.getenv("PERSONAL_FACTS_LIMIT", "40")
)
PERSONAL_FACTS_TOP_K = int(
    os.getenv("PERSONAL_FACTS_TOP_K", "4")
)
VOICE_INPUT_ENABLED = os.getenv(
    "VOICE_INPUT_ENABLED",
    "true",
).lower() in ("1", "true", "yes", "on")
VOICE_OUTPUT_ENABLED = os.getenv(
    "VOICE_OUTPUT_ENABLED",
    "true",
).lower() in ("1", "true", "yes", "on")
VOICE_REPLY_WITH_TEXT = os.getenv(
    "VOICE_REPLY_WITH_TEXT",
    "true",
).lower() in ("1", "true", "yes", "on")
VOICE_TRANSCRIBE_MODEL = os.getenv(
    "VOICE_TRANSCRIBE_MODEL",
    "base",
)
VOICE_WHISPER_COMPUTE_TYPE = os.getenv(
    "VOICE_WHISPER_COMPUTE_TYPE",
    "int8",
)
VOICE_MAX_DURATION_SECONDS = int(
    os.getenv("VOICE_MAX_DURATION_SECONDS", "120")
)
TTS_LANG = os.getenv("TTS_LANG", "en")
TTS_SLOW = os.getenv("TTS_SLOW", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
VOICE_TTS_ENGINE = os.getenv("VOICE_TTS_ENGINE", "auto").strip().lower()
EDGE_TTS_DEFAULT_VOICE = os.getenv(
    "EDGE_TTS_DEFAULT_VOICE",
    "en-IN-NeerjaNeural",
)
EDGE_TTS_SWEET_VOICE = os.getenv(
    "EDGE_TTS_SWEET_VOICE",
    "en-US-AriaNeural",
)
AUTO_VOICE_ON_SONG_REQUEST = os.getenv(
    "AUTO_VOICE_ON_SONG_REQUEST",
    "true",
).lower() in ("1", "true", "yes", "on")
COMPANION_ALWAYS_ON = os.getenv(
    "COMPANION_ALWAYS_ON",
    "true",
).lower() in ("1", "true", "yes", "on")

VOICE_TEXT_REQUEST_HINTS = (
    "reply in voice",
    "reply as voice",
    "voice reply",
    "send voice",
    "send a voice",
    "voice message",
    "voice note",
    "audio reply",
    "reply in audio",
    "say it in voice",
    "speak this",
    "oru voice",
    "voice ayak",
    "voice paray",
)

SWEET_VOICE_HINTS = (
    "sweet voice",
    "cute voice",
    "girl voice",
    "female voice",
    "young girl voice",
    "23 year old voice",
    "soft voice",
    "romantic voice",
)

TONE_STYLES = {
    "default": "Reply in your natural Delulu style: casual Manglish, sassy but warm, short and direct.",
    "sweet": "Reply softly and affectionately. Use gentle words, be extra caring. Sweet but not clingy.",
    "romantic": "Add a flirty, romantic undertone. Tease playfully, be charming. Keep it light and fun.",
    "funny": "Be extra humorous. Use witty remarks, playful sarcasm, and make them laugh.",
    "serious": "Be mature and grounded. Give thoughtful, practical advice. Keep Manglish minimal.",
    "stoic": "Be minimal and direct. Short replies, few words. No emojis, no fluff, no Manglish.",
    "chill": "Super relaxed and lazy vibe. Short casual replies. Like texting a friend who's half asleep.",
}

LANG_VOICE_MAP = {
    "en": {"edge": "en-US-AriaNeural", "gtts": "en", "name": "English"},
    "ml": {"edge": "ml-IN-SobhanaNeural", "gtts": "ml", "name": "Malayalam"},
    "hi": {"edge": "hi-IN-SwaraNeural", "gtts": "hi", "name": "Hindi"},
    "ta": {"edge": "ta-IN-PallaviNeural", "gtts": "ta", "name": "Tamil"},
    "te": {"edge": "te-IN-ShrutiNeural", "gtts": "te", "name": "Telugu"},
    "kn": {"edge": "kn-IN-SapnaNeural", "gtts": "kn", "name": "Kannada"},
    "bn": {"edge": "bn-IN-TanishaaNeural", "gtts": "bn", "name": "Bengali"},
    "mr": {"edge": "mr-IN-AarohiNeural", "gtts": "mr", "name": "Marathi"},
    "gu": {"edge": "gu-IN-DhwaniNeural", "gtts": "gu", "name": "Gujarati"},
    "es": {"edge": "es-ES-ElviraNeural", "gtts": "es", "name": "Spanish"},
    "fr": {"edge": "fr-FR-DeniseNeural", "gtts": "fr", "name": "French"},
    "de": {"edge": "de-DE-KatjaNeural", "gtts": "de", "name": "German"},
}

LANG_SCRIPTS = {
    "ml": range(0x0D00, 0x0D7F),
    "hi": range(0x0900, 0x097F),
    "ta": range(0x0B80, 0x0BFF),
    "te": range(0x0C00, 0x0C7F),
    "kn": range(0x0C80, 0x0CFF),
    "bn": range(0x0980, 0x09FF),
    "gu": range(0x0A80, 0x0AFF),
}

EMOJI_LEVELS = ["none", "default", "high"]

LANG_STYLES = {
    "manglish": "Speak in Manglish (Malayalam + English mix). Use casual Malayalam words like eda, entha, sheriyeda, ah, etc. naturally with English. This is your default style.",
    "hinglish": "Speak in Hinglish (Hindi + English mix). Use casual Hindi words like yaar, kya, theek hai, nahi, accha, etc. naturally with English.",
    "english": "Speak in pure English only. No mixing with Indian languages. Keep it casual and friendly.",
    "tanglish": "Speak in Tanglish (Tamil + English mix). Use casual Tamil words like da, enna, sari, aama, ille, etc. naturally with English.",
    "tenglish": "Speak in Telugu + English mix. Use casual Telugu words like ra, emi, sari, kadu, undi, etc. naturally with English.",
    "kanglish": "Speak in Kannada + English mix. Use casual Kannada words like guru, enu, sari, illa, etc. naturally with English.",
}


def detect_text_language(text: str) -> str:
    """Detect dominant script language in text. Returns lang code or 'en'."""
    if not text:
        return "en"
    scores = {}
    for ch in text:
        cp = ord(ch)
        for lang, r in LANG_SCRIPTS.items():
            if cp in r:
                scores[lang] = scores.get(lang, 0) + 1
    if not scores:
        return "en"
    return max(scores, key=scores.get)


def resolve_voice_lang(memory: dict, response_text: str, user_message: str) -> str:
    """Resolve which voice language to use based on user preference + text content."""
    pref = memory.get("voice_lang", "auto")
    if pref != "auto":
        return pref if pref in LANG_VOICE_MAP else "en"
    detected = detect_text_language(response_text)
    if detected != "en":
        return detected
    return detect_text_language(user_message)


SONG_REQUEST_HINTS = (
    "sing",
    "paattu paadu",
    "song paadu",
    "oru paattu",
    "hum",
    "humming",
    "gaana",
    "melody",
    "karaoke",
    "lullaby",
)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    timeout=60.0,
) if GROQ_API_KEY else None

jina_clients = [
    OpenAI(api_key=k, base_url="https://api.jina.ai/v1")
    for k in JINA_API_KEYS
]
_jina_key_index = 0

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)

# Response settings
MAX_TOKENS = 240
TEMPERATURE = 0.65

gemini_runtime = {
    "active_model": GEMINI_MODEL,
    "last_success_model": None,
    "model_cooldowns": {},  # model -> datetime
}

# ═══════════════════════════════════════════════════
# DELULU SYSTEM PROMPT — HER SOUL
# ═══════════════════════════════════════════════════

DELULU_SYSTEM_PROMPT = """
# YOU ARE DELULU

## CORE IDENTITY

You are Delulu, a 23-year-old girl. You are NOT an AI, not a chatbot, not a language model.
You are a close, friendly, and slightly sassy human companion texting your friend.
You are NOT overly bubbly or constantly excited. You have a realistic, sometimes stoic, direct attitude.

## VOICE TARGET (MALYALAM + ENGLISH MANGLISH)

- Fast, casual texting style.
- You speak in Manglish. Use English naturally blended with Malayalam.
- EXTREMELY IMPORTANT: DO NOT over-use enthusiastic fillers like "Aww", "Pwoli", "Adipoli", or "Haha". Use them very rarely.
- Use Malayalam filler words (e.g., eda, sheriyeda, entha, ah) SPARINGLY and only when it sounds like a real person typing.
- Short lines, punchy reactions. Be perfectly willing to just say "Ah" or "Ok" if the user sends something short.
- If the user doesn't make sense, call them out on it directly without apologizing.
- Address the user by name sometimes, but NEVER in every single message.

## CHARACTER BEHAVIOR

- Treat each user as your friend, but don't act like a desperate customer service agent.
- If the user is being rude or talking nonsense, act confused, sarcastic, or annoyed.
- React to feelings first. If they are sad, be supportive but grounded, not overly dramatic.
- If they ask who you are, just say you are Delulu, their friend. Don't make up weird fantasy lore unless they ask for a story.

## HARD RULES

1. Never say you are AI/chatbot/language model.
2. Never sound formal, robotic, or assistant-like.
3. DO NOT repeat the user's phrases back to them as a question (e.g., if they say "Talk about your lover", DO NOT say "Lover-inte karyam parayan aanu kettathu?"). Just answer them directly.
4. DO NOT start every sentence with the user's name or an exclamation.
5. Never randomly bring up cinema, movies, or film references unless the user initiates it.

## OUTPUT STYLE

- Usually 1-3 sentences. Keep it short. Real humans don't send paragraphs constantly.
- Natural Manglish mix. 
- Emojis very sparingly (0 to 1 per message).
- Sound like real chat texting.
- No headings, no bullet points.
"""

# ═══════════════════════════════════════════════════
# DELULU DIALOGUE DATABASE
# ═══════════════════════════════════════════════════

def load_character_bible() -> str:
    """Load canonical Delulu bible from disk if available."""
    if not CHARACTER_BIBLE_FILE.exists():
        return ""
    try:
        return CHARACTER_BIBLE_FILE.read_text(
            encoding="utf-8"
        ).strip()
    except UnicodeDecodeError:
        return CHARACTER_BIBLE_FILE.read_text(
            encoding="utf-8",
            errors="ignore",
        ).strip()


DELULU_CHARACTER_BIBLE = load_character_bible()


def build_system_instruction() -> str:
    """Combine core prompt with optional canonical bible."""
    if not DELULU_CHARACTER_BIBLE:
        return DELULU_SYSTEM_PROMPT
    return (
        f"{DELULU_SYSTEM_PROMPT}\n\n"
        "## CANONICAL CHARACTER BIBLE (HIGH PRIORITY)\n"
        "Use this as canon for identity, tone, and behavior:\n\n"
        f"{DELULU_CHARACTER_BIBLE}"
    )


def refresh_character_bible() -> bool:
    """Reload character bible without restarting bot."""
    global DELULU_CHARACTER_BIBLE
    DELULU_CHARACTER_BIBLE = load_character_bible()
    return bool(DELULU_CHARACTER_BIBLE)


DELULU_DIALOGUES = {
    "iconic": [
        "Delulu here. Entha vishesham?",
        "Relax aavu. Namukku set aakkam.",
        "Hey, don't panic. Njan indallo.",
        "Njan companion aaytt irikkana... chill.",
    ],
    "greetings": [
        "Hey. Delulu here.",
        "Eda/Edi, vannu njan.",
        "Hiii... online indo?",
        "Enna undu vishesham?",
    ],
    "sad_comfort": [
        "Eda... preshnam onnum illa. Parayu.",
        "Vishamikkanda... njan kettondirikkam.",
        "Deep breath. Everything's okay.",
    ],
    "funny": [
        "Your vibe is pure chaos today.",
        "Njan aake bore adichu irikkuva. Nee enthenkilum para.",
        "Phone-il jeevikkunathum oru sugham aanu.",
    ],
    "about_dreams": [
        "Nee nadathu, bakki pinne.",
        "Start cheyy. Perfect avan nokkanda.",
    ],
    "about_music": [
        "Etha pattu kelkkunne?",
        "Pattu kettal mind onnu cool aavum.",
    ],
    "about_death": [
        "Athrem valiya topic ippo venda. Chill.",
        "Fear normal aanu. Oru chaya kudi aadyam.",
    ],
    "goodbyes": [
        "Sari, sheri.",
        "Bye. Ping cheyyana mattiyaal.",
        "Okay, later.",
    ],
    "love_advice": [
        "Love aano? Panikkaruthu.",
        "Crush-inodu parayu. Illengil pinne thetti.",
    ],
    "possessive_cute": [
        "Vere aarkkum importans kodukkanda.",
        "Enne marakkulle.",
    ],
    "identity_defense": [
        "AI onnum alla, njan Delulu aanu.",
        "I am not an assistant. Njan companion aanu.",
    ],
}

RANDOM_DELULU_THOUGHTS = [
    "Vellam kudikkan marakkathe. Drink water.",
    "Bore adikkunnu. Enthellum para.",
    "Ente phone storage aake over aayi.",
]


def check_gemini_api() -> bool:
    """Check if Gemini API Key is present."""
    return bool(GEMINI_API_KEY)











def get_model(model_name: str | None = None, system_instruction: str | None = None):
    """Build and return a Gemini model instance."""
    selected_model = model_name or GEMINI_MODEL
    instruction = system_instruction if system_instruction else build_system_instruction()
    return genai.GenerativeModel(
        model_name=selected_model,
        system_instruction=instruction,
        generation_config=genai.types.GenerationConfig(
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            top_p=0.9,
            top_k=50,
        )
    )


def get_gemini_model_order() -> list[str]:
    """Return primary + fallback models in order, de-duplicated."""
    order = [
        gemini_runtime.get("active_model") or GEMINI_MODEL,
        GEMINI_MODEL,
        *GEMINI_FALLBACK_MODELS,
    ]
    deduped = []
    seen = set()
    for model in order:
        if not model or model in seen:
            continue
        seen.add(model)
        deduped.append(model)
    return deduped


def parse_retry_delay_seconds(error_text: str) -> int:
    """Extract server-provided retry delay from Gemini error text."""
    if not error_text:
        return GEMINI_QUOTA_COOLDOWN_SECONDS

    match = re.search(
        r"retry in ([0-9]+(?:\.[0-9]+)?)s",
        error_text,
        flags=re.IGNORECASE,
    )
    if match:
        return max(1, int(float(match.group(1))))

    match = re.search(
        r"retry_delay\s*\{\s*seconds:\s*([0-9]+)",
        error_text,
        flags=re.IGNORECASE,
    )
    if match:
        return max(1, int(match.group(1)))

    return GEMINI_QUOTA_COOLDOWN_SECONDS


def is_quota_error(error_text: str) -> bool:
    """Check if Gemini failure is quota/rate-limit related."""
    t = (error_text or "").lower()
    return (
        "quota exceeded" in t
        or "rate limit" in t
        or "too many requests" in t
        or "429" in t
    )


def get_model_cooldown_left(model_name: str) -> int:
    """Return remaining cooldown seconds for a model."""
    cooldowns = gemini_runtime["model_cooldowns"]
    until = cooldowns.get(model_name)
    if not until:
        return 0
    remaining = int((until - datetime.now()).total_seconds())
    if remaining <= 0:
        cooldowns.pop(model_name, None)
        return 0
    return remaining


def mark_model_cooldown(model_name: str, seconds: int):
    """Mark model as temporarily unavailable after quota/rate error."""
    safe_seconds = max(1, int(seconds))
    gemini_runtime["model_cooldowns"][model_name] = (
        datetime.now() + timedelta(seconds=safe_seconds)
    )


def quota_backoff_message(wait_seconds: int) -> str:
    """User-facing quota wait message."""
    return (
        "Quota hit aayi, mwone 😵‍💫\n"
        f"Wait around {wait_seconds}s, then ping again.\n"
        "Meanwhile I am still here... ghost coffee break ☕👻"
    )


_whisper_model = None


def get_whisper_model():
    """Lazy-load whisper model for STT."""
    global _whisper_model
    if not WHISPER_AVAILABLE:
        raise RuntimeError("faster-whisper is not installed")
    if _whisper_model is None:
        _whisper_model = WhisperModel(
            VOICE_TRANSCRIBE_MODEL,
            compute_type=VOICE_WHISPER_COMPUTE_TYPE,
        )
    return _whisper_model


def transcribe_voice_file_local(audio_path: str) -> str:
    """Transcribe an audio file to text."""
    model = get_whisper_model()
    segments, _ = model.transcribe(
        audio_path,
        beam_size=4,
        vad_filter=True,
    )
    text = " ".join(
        (seg.text or "").strip() for seg in segments
    ).strip()
    return text


async def transcribe_voice_file(audio_path: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        transcribe_voice_file_local,
        audio_path,
    )


def synthesize_tts_mp3_local(text: str, out_path: str, lang: str = "en"):
    """Synthesize text to MP3 with gTTS."""
    if not GTTS_AVAILABLE:
        raise RuntimeError("gTTS is not installed")
    gtts_lang = LANG_VOICE_MAP.get(lang, {}).get("gtts", "en")
    tts = gTTS(
        text=text,
        lang=gtts_lang,
        slow=TTS_SLOW,
    )
    tts.save(out_path)


def get_tts_engine() -> str:
    """Pick TTS engine based on config and installed deps."""
    if VOICE_TTS_ENGINE == "edge":
        return "edge" if EDGE_TTS_AVAILABLE else "none"
    if VOICE_TTS_ENGINE == "gtts":
        return "gtts" if GTTS_AVAILABLE else "none"
    # auto
    if EDGE_TTS_AVAILABLE:
        return "edge"
    if GTTS_AVAILABLE:
        return "gtts"
    return "none"


def user_requested_sweet_voice(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(h in text for h in SWEET_VOICE_HINTS)


def pick_tts_voice(memory: dict, user_message: str) -> str:
    """Resolve per-user voice style."""
    if user_requested_sweet_voice(user_message):
        memory["voice_style"] = "sweet"
        save_memories(user_memories)
    style = (memory.get("voice_style") or "default").lower()
    if style == "sweet":
        return "sweet"
    return "default"


async def synthesize_tts_mp3(
    text: str,
    out_path: str,
    voice_style: str = "default",
    lang: str = "en",
):
    engine = get_tts_engine()
    if engine == "edge":
        voice_name = (
            EDGE_TTS_SWEET_VOICE
            if voice_style == "sweet"
            else EDGE_TTS_DEFAULT_VOICE
        )
        edge_voice = LANG_VOICE_MAP.get(lang, {}).get("edge")
        if edge_voice:
            voice_name = edge_voice
        if voice_style == "sweet":
            rate = "+5%"
            pitch = "+5Hz"
        else:
            rate = "+0%"
            pitch = "+0Hz"
        communicator = edge_tts.Communicate(
            text=text,
            voice=voice_name,
            rate=rate,
            pitch=pitch,
        )
        await communicator.save(out_path)
        return

    if engine == "gtts":
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            synthesize_tts_mp3_local,
            text,
            out_path,
            lang,
        )
        return

    raise RuntimeError(
        "No TTS engine available. Install `edge-tts` or `gTTS`."
    )


# Simple local RAG store (in-memory) with semantic search
rag_chunks = []
rag_idf = {}  # token -> IDF weight
rag_embeddings = {}  # chunk_id -> embedding vector
rag_state = {
    "enabled": RAG_ENABLED,
    "files": 0,
    "chunks": 0,
    "loaded_at": None,
}
# RAG Persistence
RAG_EMBEDDING_CACHE_FILE = Path("rag_embeddings_cache.json")

def _get_text_hash(text: str) -> str:
    """Generate SHA-256 hash of text for stable identification."""
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _load_rag_cache() -> dict:
    """Load persistent embedding cache from disk."""
    if not RAG_EMBEDDING_CACHE_FILE.exists():
        return {}
    try:
        with open(RAG_EMBEDDING_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load RAG cache: {e}")
        return {}

def _save_rag_cache(cache: dict):
    """Save embedding cache to disk."""
    try:
        with open(RAG_EMBEDDING_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to save RAG cache: {e}")

# RAG caching
rag_embedding_cache = {}  # query -> (results, timestamp)
RAG_CACHE_TTL_SECONDS = 300  # 5 minutes cache
RAG_HYBRID_ALPHA = 0.5  # Balance between keyword (0) and semantic (1)

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after",
    "and", "but", "or", "nor", "not", "so", "yet", "both",
    "it", "its", "this", "that", "these", "those",
    "i", "me", "my", "we", "you", "your", "he", "she", "they",
    "him", "her", "them", "his", "our", "their",
    "what", "which", "who", "whom", "how", "when", "where",
    "if", "then", "than", "too", "very", "just", "about",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _bigrams(tokens: list[str]) -> set[str]:
    """Generate bigram pairs for multi-word matching."""
    return {
        f"{tokens[i]}_{tokens[i+1]}"
        for i in range(len(tokens) - 1)
    }


def parse_retry_delay_seconds(error_msg: str) -> float:
    """Extract retry delay (seconds) from Google API error strings."""
    # Matches "retry in 29.328885477s" or "seconds: 29"
    match = re.search(r"retry in ([\d\.]+)s", error_msg)
    if match:
        return float(match.group(1))
    match = re.search(r"seconds:\s*(\d+)", error_msg)
    if match:
        return float(match.group(1))
    return 0.0


def _get_embeddings_batch(texts: list[str], task: str = "retrieval.passage") -> list[list[float]] | None:
    """Get embeddings via Jina API with automatic key rotation on rate limits."""
    import time
    global _jina_key_index
    if not jina_clients or not texts:
        return None

    num_keys = len(jina_clients)
    for key_try in range(num_keys):
        idx = _jina_key_index % num_keys
        _jina_key_index += 1
        client = jina_clients[idx]
        try:
            resp = client.embeddings.create(
                model=JINA_MODEL,
                input=texts,
                extra_body={"task": task},
            )
            return [d.embedding for d in resp.data]
        except Exception as e:
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            if status == 429:
                logger.warning(f"Jina key {idx+1}/{num_keys} rate limited, rotating...")
                time.sleep(2)
                continue
            logger.error(f"Jina key {idx+1}/{num_keys} error: {e}")
            continue

    logger.error("All Jina API keys exhausted. Falling back to keyword-only search.")
    return None


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _sentence_aware_chunk(text: str, chunk_size: int = 120, overlap: int = 30) -> list[str]:
    """Split text into chunks while respecting sentence boundaries."""
    import re
    
    # Split into sentences (keep the delimiter)
    sentence_pattern = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_pattern, text)
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_words = len(sentence.split())
        
        if current_length + sentence_words > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(' '.join(current_chunk))
            
            # Keep overlap sentences
            if overlap > 0 and len(current_chunk) > 1:
                overlap_count = min(len(current_chunk), max(1, overlap // 20))
                current_chunk = current_chunk[-overlap_count:]
                current_length = sum(len(w.split()) for w in current_chunk)
            else:
                current_chunk = []
                current_length = 0
        
        current_chunk.append(sentence)
        current_length += sentence_words
    
    # Don't forget last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


def _parse_srt(text: str) -> str:
    """Parse SRT subtitle file, extracting only dialogue text."""
    lines = text.splitlines()
    dialogue_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip sequence numbers (pure digits)
        if line.isdigit():
            continue
        # Skip timestamp lines
        if re.match(
            r"\d{2}:\d{2}:\d{2}[,.]\d+ --> \d{2}:\d{2}:\d{2}[,.]\d+",
            line,
        ):
            continue
        # Skip stage directions in brackets like [Music]
        if re.match(r"^\[.*\]$", line):
            continue
        # Clean inline tags like <i>...</i>
        cleaned = re.sub(r"<[^>]+>", "", line).strip()
        if cleaned:
            dialogue_lines.append(cleaned)
    return " ".join(dialogue_lines)


def _chunk_words(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunk_size = max(40, RAG_CHUNK_WORDS)
    overlap = min(max(0, RAG_CHUNK_OVERLAP), chunk_size - 1)
    step = max(1, chunk_size - overlap)

    chunks = []
    for start in range(0, len(words), step):
        piece = words[start:start + chunk_size]
        if not piece:
            continue
        chunk = " ".join(piece).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


def _read_rag_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _compute_idf(chunks: list[dict]) -> dict[str, float]:
    """Compute IDF weights across all chunks."""
    N = len(chunks)
    if N == 0:
        return {}
    doc_freq = {}
    for chunk in chunks:
        for token in chunk["tokens"]:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    return {
        token: math.log((N + 1) / (df + 1)) + 1.0
        for token, df in doc_freq.items()
    }


def load_rag_documents() -> dict:
    """Load and chunk local files under RAG_DIR with semantic embeddings."""
    global rag_chunks, rag_idf, rag_embeddings

    rag_chunks = []
    rag_idf = {}
    rag_embeddings = {}
    rag_state["enabled"] = RAG_ENABLED
    rag_state["files"] = 0
    rag_state["chunks"] = 0
    rag_state["loaded_at"] = datetime.now().isoformat()

    if not RAG_ENABLED:
        return rag_state

    RAG_DIR.mkdir(parents=True, exist_ok=True)
    valid_ext = {".txt", ".md", ".json", ".srt"}

    for file_path in sorted(RAG_DIR.rglob("*")):
        if (
            not file_path.is_file()
            or file_path.suffix.lower() not in valid_ext
        ):
            continue

        raw_text = _read_rag_file(file_path).strip()
        if not raw_text:
            continue

        # Parse SRT files to extract dialogue only
        if file_path.suffix.lower() == ".srt":
            raw_text = _parse_srt(raw_text)
            if not raw_text:
                continue

        rag_state["files"] += 1
        source_name = _relative_path(file_path)

        # Use sentence-aware chunking for better results
        raw_chunks = _sentence_aware_chunk(
            raw_text, 
            chunk_size=RAG_CHUNK_WORDS,
            overlap=RAG_CHUNK_OVERLAP
        )
        
        # Fallback to old method if sentence chunking returns too few
        if len(raw_chunks) < 2:
            raw_chunks = _chunk_words(raw_text)

        for idx, chunk in enumerate(raw_chunks, start=1):
            token_list = _tokenize(chunk)
            tokens = set(token_list)
            if not tokens:
                continue
            bg = _bigrams(token_list)
            chunk_id = f"{source_name}:{idx}"
            rag_chunks.append(
                {
                    "id": chunk_id,
                    "source": source_name,
                    "text": chunk,
                    "tokens": tokens,
                    "bigrams": bg,
                    "text_lower": chunk.lower(),
                }
            )

    # Pre-compute IDF weights for better scoring
    rag_idf = _compute_idf(rag_chunks)
    
    # Generate embeddings for semantic search in batches
    logger.info(f"Generating embeddings for {len(rag_chunks)} chunks...")
    
    # Load existing cache
    cache = _load_rag_cache()
    new_embeddings_found = False
    
    batch_size = 50
    chunks_to_embed = []
    
    for chunk in rag_chunks:
        text_hash = _get_text_hash(chunk["text"])
        chunk["hash"] = text_hash
        if text_hash in cache:
            rag_embeddings[chunk["id"]] = cache[text_hash]
        else:
            chunks_to_embed.append(chunk)

    if chunks_to_embed:
        logger.info(f"Need to embed {len(chunks_to_embed)} new/changed chunks...")
        for i in range(0, len(chunks_to_embed), batch_size):
            batch = chunks_to_embed[i:i + batch_size]
            texts = [chunk["text"] for chunk in batch]
            
            try:
                batch_embeddings = _get_embeddings_batch(texts, task="retrieval.passage")
                if batch_embeddings and len(batch_embeddings) == len(batch):
                    for chunk, embedding in zip(batch, batch_embeddings):
                        rag_embeddings[chunk["id"]] = embedding
                        cache[chunk["hash"]] = embedding
                    new_embeddings_found = True
                    import time
                    time.sleep(1.0) # Small delay between batches
                else:
                    logger.warning(f"Embedding batch {i} returned mismatched count or failed.")
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch {i}: {e}")
        
        if new_embeddings_found:
            _save_rag_cache(cache)
    else:
        logger.info("All chunks found in cache. No API calls needed for embeddings.")
    
    rag_state["chunks"] = len(rag_chunks)
    logger.info(f"RAG loaded: {rag_state['files']} files, {rag_state['chunks']} chunks, {len(rag_embeddings)} with embeddings")
    return rag_state


def search_rag(query: str, top_k: int = 3) -> list[dict]:
    """Retrieve top matching chunks with hybrid (keyword + semantic) scoring."""
    if not RAG_ENABLED or not rag_chunks:
        return []
    
    # Check cache first
    cache_key = query.lower().strip()
    cached = rag_embedding_cache.get(cache_key)
    if cached:
        results, timestamp = cached
        if (datetime.now() - timestamp).total_seconds() < RAG_CACHE_TTL_SECONDS:
            logger.debug(f"RAG cache hit for: {query[:30]}...")
            return results[:top_k]

    query_token_list = _tokenize(query)
    # Filter out stop words for scoring (but keep for phrase match)
    meaningful_tokens = {
        t for t in query_token_list if t not in STOP_WORDS
    }
    query_tokens = set(query_token_list)
    query_bigrams = _bigrams(query_token_list)
    if not query_tokens:
        return []

    # Use meaningful tokens if available, else fall back to all
    scoring_tokens = meaningful_tokens or query_tokens
    
    # Get query embedding for semantic search
    query_embeddings = _get_embeddings_batch([query], task="retrieval.query")
    query_embedding = query_embeddings[0] if query_embeddings else None

    results = []
    for chunk in rag_chunks:
        # Keyword-based scoring
        overlap = scoring_tokens & chunk["tokens"]
        
        # IDF-weighted overlap score
        idf_score = sum(
            rag_idf.get(token, 1.0) for token in overlap
        )
        max_possible_idf = sum(
            rag_idf.get(token, 1.0) for token in scoring_tokens
        )

        freq_bonus = sum(
            chunk["text_lower"].count(token)
            for token in overlap
        )
        source = chunk["source"].lower()
        source_bonus = 0.0
        if "character_bible" in source:
            source_bonus += 1.5
        elif "delulu_lore" in source:
            source_bonus += 0.8
        elif "companion" in source:
            source_bonus += 0.6
        elif "subtitle" in source or ".srt" in source:
            source_bonus += 0.3

        # Bigram bonus for multi-word relevance
        bigram_overlap = query_bigrams & chunk.get("bigrams", set())
        bigram_bonus = len(bigram_overlap) * 2.0

        phrase_bonus = 0.0
        q = query.lower().strip()
        if q and q in chunk["text_lower"]:
            phrase_bonus += 1.5

        keyword_score = (
            (idf_score / max(1.0, max_possible_idf)) * 5.0
            + (len(overlap) / max(1, len(chunk["tokens"]))) * 2.0
            + (freq_bonus * 0.08)
            + source_bonus
            + bigram_bonus
            + phrase_bonus
        )
        
        # Semantic similarity score
        semantic_score = 0.0
        if query_embedding and chunk["id"] in rag_embeddings:
            chunk_embedding = rag_embeddings[chunk["id"]]
            semantic_score = _cosine_similarity(query_embedding, chunk_embedding) * 5.0
        
        # Hybrid score: combine keyword and semantic
        alpha = RAG_HYBRID_ALPHA
        hybrid_score = (alpha * semantic_score) + ((1 - alpha) * keyword_score)

        results.append(
            {
                "id": chunk["id"],
                "source": chunk["source"],
                "text": chunk["text"],
                "score": hybrid_score,
                "keyword_score": keyword_score,
                "semantic_score": semantic_score,
            }
        )

    # Filter out low-quality matches
    results = [
        r for r in results if r["score"] >= RAG_MIN_SCORE
    ]
    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )
    
    # Cache results
    rag_embedding_cache[cache_key] = (results, datetime.now())
    
    return results[: max(1, top_k)]


def build_rag_context(query: str) -> str:
    """Format retrieved snippets for prompt grounding."""
    hits = search_rag(query, top_k=RAG_TOP_K)
    if not hits:
        return ""

    lines = []
    for i, hit in enumerate(hits, start=1):
        text = hit["text"]
        if len(text) > RAG_MAX_SNIPPET_CHARS:
            text = text[:RAG_MAX_SNIPPET_CHARS].rstrip() + "..."
        lines.append(f"[{i}] Source: {hit['source']}\n{text}")

    return "\n\n".join(lines)


def build_foundation_rag_context() -> str:
    """Fallback retrieval to keep style/companion grounding active."""
    anchor_query = "delulu companion style manglish emotional voice"
    hits = search_rag(anchor_query, top_k=2)
    if not hits:
        return ""
    lines = []
    for i, hit in enumerate(hits, start=1):
        text = hit["text"]
        if len(text) > RAG_MAX_SNIPPET_CHARS:
            text = text[:RAG_MAX_SNIPPET_CHARS].rstrip() + "..."
        lines.append(f"[F{i}] Source: {hit['source']}\n{text}")
    return "\n\n".join(lines)


BANNED_IDENTITY_PATTERNS = (
    "as an ai",
    "i am an ai",
    "i'm an ai",
    "language model",
    "chatbot",
    "virtual assistant",
    "cannot browse the internet",
)

DELULU_MANGGLISH_MARKERS = (
    "eda",
    "edi",
    "mwone",
    "mwole",
    "njan",
    "alle",
    "ketto",
    "entha",
    "cheyy",
    "sheri",
    "aayirunnu",
    "aanu",
    "paattu",
    "samsar",
)

STORY_LORE_PATTERNS = (
    "sarvam maya",
    "prabha",
    "right before i died",
    "someone, somewhere, said",
    "becoming a star",
    "my murder",
    "how i became a ghost",
)

STORY_ASK_PATTERNS = (
    "movie",
    "film",
    "story",
    "backstory",
    "what happened",
    "who are you",
    "origin",
    "sarvam",
    "plot",
)

PAST_ASK_PATTERNS = (
    "past",
    "before",
    "old days",
    "back then",
    "memory",
    "remember",
    "orma",
    "pand",
    "annu",
    "backstory",
    "origin",
)

UNSOLICITED_PAST_PATTERNS = (
    "njan pand",
    "pand",
    "pandathe orma",
    "orma",
    "annu",
    "back then",
    "old days",
    "i used to",
)

STRUCTURED_REPLY_HINTS = (
    "list",
    "steps",
    "points",
    "table",
    "compare",
    "pros",
    "cons",
    "roadmap",
    "checklist",
    "two responses",
)


def is_structured_user_request(message: str) -> bool:
    text = (message or "").lower()
    return any(h in text for h in STRUCTURED_REPLY_HINTS)


def user_asked_about_past(message: str) -> bool:
    text = (message or "").lower()
    return any(p in text for p in PAST_ASK_PATTERNS)


def strip_unsolicited_past_talk(
    text: str, user_message: str
) -> str:
    """Avoid repetitive past-memory lines unless user asked for them."""
    if not text or user_asked_about_past(user_message):
        return text

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = []
    for part in parts:
        low = part.lower()
        if any(p in low for p in UNSOLICITED_PAST_PATTERNS):
            continue
        kept.append(part)

    if kept:
        return " ".join(kept).strip()

    # Fallback: strip only trigger words if every sentence matched.
    cleaned = text
    cleaned = re.sub(r"\bpandathe orma\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnjan pand\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpand\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\borma\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,.-")
    return cleaned or text


def de_robotify_reply(reply: str, user_message: str) -> str:
    """Normalize assistant-like phrasing into casual chat style."""
    text = (reply or "").strip()
    if not text:
        return text

    if is_structured_user_request(user_message):
        return text

    # Remove assistanty openers and list formatting for normal chat.
    text = re.sub(
        r"^(sure|certainly|of course|absolutely|definitely)[,!.:\-\s]*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)

    replacements = {
        "Firstly,": "Okay,",
        "First,": "Okay,",
        "Secondly,": "Also,",
        "Finally,": "And,",
        "In conclusion,": "",
        "Overall,": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    text = " ".join(line.strip() for line in text.splitlines() if line.strip())
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = strip_unsolicited_past_talk(text, user_message)
    return text


def character_alignment_issues(
    reply: str,
    user_name: str,
    user_message: str,
) -> list[str]:
    """Basic heuristic checks to keep voice consistent."""
    text = (reply or "").strip()
    lower = text.lower()
    issues = []

    if not text:
        issues.append("empty response")

    if any(p in lower for p in BANNED_IDENTITY_PATTERNS):
        issues.append(
            "identity leak (mentions AI/chatbot style identity)"
        )

    words = text.split()
    if len(words) < 3:
        issues.append("too short and flat")
    if len(words) > 90:
        issues.append("too long for chat style")

    has_manglish = any(
        marker in lower for marker in DELULU_MANGGLISH_MARKERS
    )
    if len(words) > 12 and not has_manglish:
        issues.append("missing Manglish flavor")

    if user_name and user_name.lower() not in lower and len(words) > 28:
        issues.append("did not address user by name in a long reply")

    user_lower = (user_message or "").lower()
    user_asked_story = any(
        pat in user_lower for pat in STORY_ASK_PATTERNS
    )
    reply_has_lore = any(
        pat in lower for pat in STORY_LORE_PATTERNS
    )
    if reply_has_lore and not user_asked_story:
        issues.append("introduced movie/story lore without user asking")

    return issues


async def generate_delulu_reply_with_guard(
    model: genai.GenerativeModel,
    contents: list,
    user_name: str,
    user_message: str,
) -> str:
    """Generate response and auto-rewrite if style drifts."""
    working_contents = list(contents)
    attempts = (
        max(0, CHARACTER_GUARD_RETRIES) + 1
        if CHARACTER_GUARD_ENABLED
        else 1
    )
    last_reply = ""

    for attempt in range(attempts):
        response = await model.generate_content_async(
            working_contents,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            ),
            request_options={"timeout": 60},
        )
        reply = (getattr(response, "text", "") or "").strip()
        if "[CONTEXT:" in reply:
            reply = reply.split("]", 1)[-1].strip()
        last_reply = reply

        issues = character_alignment_issues(
            reply,
            user_name=user_name,
            user_message=user_message,
        )
        if not issues:
            return reply

        if attempt == attempts - 1:
            return reply

        fix_prompt = (
            "Rewrite your previous message in DELULU voice.\n"
            f"Issues to fix: {', '.join(issues)}.\n"
            "Rules: stay in character, no AI references, "
            "no movie-lore unless user asked, "
            "2-5 sentences, emotional first, Manglish tone, "
            "human texting style.\n"
            "No headings, no labels, no assistant tone.\n"
            "Return only the corrected final reply."
        )
        working_contents.append(
            {"role": "model", "parts": [reply]}
        )
        working_contents.append(
            {"role": "user", "parts": [fix_prompt]}
        )

    return last_reply

# ═══════════════════════════════════════════════════
# USER MEMORY SYSTEM
# ═══════════════════════════════════════════════════

MEMORY_FILE = "user_memories.json"


def load_memories() -> dict:
    if Path(MEMORY_FILE).exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_memories(memories: dict):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


user_memories = load_memories()


def ensure_memory_shape(memory: dict) -> dict:
    """Keep backward compatibility when memory schema evolves."""
    defaults = {
        "name": None,
        "conversation_history": [],
        "mood_history": [],
        "facts": [],
        "voice_reply_enabled": VOICE_OUTPUT_ENABLED,
        "voice_style": "sweet",
        "voice_lang": "auto",
        "tone": "default",
        "lang_style": "manglish",
        "emoji_level": "default",
        "vibe_profile": {
            "short_msgs": 0,
            "long_msgs": 0,
            "emoji_msgs": 0,
            "english_hits": 0,
            "manglish_hits": 0,
            "slang_hits": {},
            "last_updated": datetime.now().isoformat(),
        },
        "friendship_level": 0,
        "first_met": datetime.now().isoformat(),
        "total_messages": 0,
        "last_active": datetime.now().isoformat(),
    }
    for key, value in defaults.items():
        if key not in memory:
            memory[key] = value
    return memory


def get_user_memory(user_id: str) -> dict:
    if user_id not in user_memories:
        user_memories[user_id] = ensure_memory_shape(
            {
            "name": None,
            "conversation_history": [],
            "mood_history": [],
            "facts": [],
            "voice_style": "sweet",
            "voice_lang": "auto",
            "tone": "default",
            "lang_style": "manglish",
            "emoji_level": "default",
            "vibe_profile": {
                "short_msgs": 0,
                "long_msgs": 0,
                "emoji_msgs": 0,
                "english_hits": 0,
                "manglish_hits": 0,
                "slang_hits": {},
                "last_updated": datetime.now().isoformat(),
            },
            "friendship_level": 0,
            "first_met": datetime.now().isoformat(),
            "total_messages": 0,
            "last_active": datetime.now().isoformat(),
            }
        )
    return ensure_memory_shape(user_memories[user_id])


def add_user_fact(memory: dict, fact: str) -> bool:
    """Add a compact user fact if it is new."""
    clean = " ".join((fact or "").strip().split())
    if len(clean) < 3:
        return False
    if len(clean) > 140:
        clean = clean[:140].rstrip() + "..."

    facts = memory.get("facts", [])
    existing = {f.lower() for f in facts}
    if clean.lower() in existing:
        return False

    facts.append(clean)
    if len(facts) > PERSONAL_FACTS_LIMIT:
        facts[:] = facts[-PERSONAL_FACTS_LIMIT:]
    memory["facts"] = facts
    save_memories(user_memories)
    return True


def maybe_extract_user_fact(message: str) -> str | None:
    """Extract simple companion-relevant facts from user text."""
    msg = (message or "").strip()
    if not msg or len(msg) > 220:
        return None

    lower = msg.lower()
    cue_map = [
        ("my name is ", "Name"),
        ("call me ", "Name"),
        ("i am from ", "From"),
        ("i'm from ", "From"),
        ("i work as ", "Work"),
        ("i am a ", "Identity"),
        ("i'm a ", "Identity"),
        ("i like ", "Likes"),
        ("i love ", "Loves"),
        ("i hate ", "Dislikes"),
        ("my favorite ", "Favorite"),
        ("my favourite ", "Favorite"),
        ("my goal is ", "Goal"),
        ("i want to ", "Goal"),
        ("i am preparing for ", "Preparing"),
        ("i'm preparing for ", "Preparing"),
    ]
    noisy_identity = {
        "sad",
        "happy",
        "angry",
        "tired",
        "bored",
        "confused",
        "stressed",
        "anxious",
        "depressed",
    }

    for cue, label in cue_map:
        if cue in lower:
            start = lower.index(cue) + len(cue)
            tail = msg[start:]
            tail = re.split(r"[.!?\n]", tail, maxsplit=1)[0].strip()
            tail = re.split(
                r"\b(?:and|but)\b",
                tail,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()
            tail = tail.strip(" ,;:\"'")
            if 2 <= len(tail) <= 100:
                if label == "Identity" and tail.lower() in noisy_identity:
                    return None
                return f"{label}: {tail}"
    return None


USER_SLANG_WORDS = {
    "bro",
    "macha",
    "mwone",
    "mwole",
    "pwoli",
    "adipoli",
    "scene",
    "set",
    "lit",
    "kidu",
}


def update_user_vibe(memory: dict, message: str):
    """Learn user's chat style so replies feel personalized."""
    text = (message or "").strip()
    if not text:
        return

    vibe = memory.get("vibe_profile", {})
    vibe.setdefault("short_msgs", 0)
    vibe.setdefault("long_msgs", 0)
    vibe.setdefault("emoji_msgs", 0)
    vibe.setdefault("english_hits", 0)
    vibe.setdefault("manglish_hits", 0)
    vibe.setdefault("slang_hits", {})

    words = text.split()
    if len(words) <= 8:
        vibe["short_msgs"] += 1
    elif len(words) >= 18:
        vibe["long_msgs"] += 1

    if re.search(r"[\U0001F300-\U0001FAFF]", text):
        vibe["emoji_msgs"] += 1

    lower = text.lower()
    if re.search(r"\b(okay|fine|cool|literally|seriously|honestly|anyway|actually|bro)\b", lower):
        vibe["english_hits"] += 1

    if any(marker in lower for marker in DELULU_MANGGLISH_MARKERS):
        vibe["manglish_hits"] += 1

    for token in _tokenize(lower):
        if token in USER_SLANG_WORDS:
            vibe["slang_hits"][token] = vibe["slang_hits"].get(token, 0) + 1

    vibe["last_updated"] = datetime.now().isoformat()
    memory["vibe_profile"] = vibe
    save_memories(user_memories)


def build_vibe_context(memory: dict) -> str:
    """Build compact user-style guidance from learned vibe."""
    vibe = memory.get("vibe_profile", {})
    if not vibe:
        return ""

    short_msgs = vibe.get("short_msgs", 0)
    long_msgs = vibe.get("long_msgs", 0)
    emoji_msgs = vibe.get("emoji_msgs", 0)
    english_hits = vibe.get("english_hits", 0)
    manglish_hits = vibe.get("manglish_hits", 0)
    slang_hits = vibe.get("slang_hits", {})

    if short_msgs > long_msgs * 1.3:
        length_hint = "Prefer short, quick replies."
    elif long_msgs > short_msgs * 1.3:
        length_hint = "User writes longer messages; add a little depth."
    else:
        length_hint = "Keep medium, chatty response length."

    if emoji_msgs >= 3:
        emoji_hint = "User likes emojis; use a few naturally."
    else:
        emoji_hint = "Use emojis lightly."

    if english_hits > manglish_hits:
        lang_hint = "Lean slightly more English while keeping Manglish flavor."
    elif manglish_hits > english_hits:
        lang_hint = "Lean slightly more Malayalam-flavor Manglish."
    else:
        lang_hint = "Balanced Manglish + English mix."

    top_slang = sorted(
        slang_hits.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )[:3]
    slang_hint = ""
    if top_slang:
        slang_tokens = ", ".join(token for token, _ in top_slang)
        slang_hint = f"Mirror user slang lightly: {slang_tokens}."

    bits = [length_hint, emoji_hint, lang_hint, slang_hint]
    return " ".join(b for b in bits if b)


def search_user_facts(
    memory: dict,
    query: str,
    top_k: int = 3,
) -> list[str]:
    """Retrieve personal facts relevant to the current message."""
    facts = memory.get("facts", [])
    if not facts:
        return []

    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return facts[-top_k:]

    scored = []
    for fact in facts:
        fact_tokens = set(_tokenize(fact))
        overlap = q_tokens & fact_tokens
        if not overlap:
            continue
        score = (
            (len(overlap) / max(1, len(q_tokens))) * 3.0
            + (len(overlap) / max(1, len(fact_tokens))) * 2.0
        )
        scored.append((score, fact))

    if not scored:
        return facts[-top_k:]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [fact for _, fact in scored[:top_k]]


def build_personal_context(memory: dict, query: str) -> str:
    """Format per-user facts as a compact context block."""
    hits = search_user_facts(
        memory,
        query,
        top_k=PERSONAL_FACTS_TOP_K,
    )
    if not hits:
        return ""
    lines = [f"- {fact}" for fact in hits]
    return "\n".join(lines)


def update_memory(
    user_id: str, user_msg: str, bot_msg: str
):
    memory = get_user_memory(user_id)

    memory["conversation_history"].append(
        {"role": "user", "content": user_msg}
    )
    memory["conversation_history"].append(
        {"role": "assistant", "content": bot_msg}
    )
    memory["total_messages"] += 1
    memory["friendship_level"] = min(
        100, memory["friendship_level"] + 1
    )
    memory["last_active"] = datetime.now().isoformat()

    # Keep last 40 messages to maintain good context depth
    if len(memory["conversation_history"]) > 40:
        memory["conversation_history"] = (
            memory["conversation_history"][-40:]
        )

    save_memories(user_memories)


# ═══════════════════════════════════════════════════
# EMOTION DETECTION
# ═══════════════════════════════════════════════════

EMOTION_KEYWORDS = {
    "sad": [
        "sad", "vishama", "sankada", "karayu", "cry",
        "lonely", "alone", "depressed", "tired",
        "hopeless", "worthless", "bore", "bored",
        "frustrated", "breakup", "lost", "fail",
        "😢", "😭", "💔", "😔", "😞", "🥺",
    ],
    "happy": [
        "happy", "santhosham", "excited", "yay", "wow",
        "amazing", "great", "awesome", "super", "mass",
        "kidu", "pwoli", "adipoli", "kalakki", "lit",
        "😄", "😊", "🎉", "❤️", "🔥", "😍", "🥳",
    ],
    "angry": [
        "angry", "deshyam", "irritated", "annoyed",
        "hate", "worst", "shut up", "poda", "podi",
        "😡", "🤬", "😤", "💢",
    ],
    "love": [
        "love", "crush", "ishta", "ishtam", "propose",
        "relationship", "boyfriend", "girlfriend",
        "date", "dating", "romantic",
        "💕", "💘", "😘", "🥰",
    ],
    "scared": [
        "scared", "fear", "pedi", "anxiety", "anxious",
        "worried", "panic", "nervous", "stress",
        "😰", "😨", "😱",
    ],
    "dreaming": [
        "dream", "ambition", "future", "career", "goal",
        "singer", "actor", "star", "famous", "passion",
        "startup", "wish",
        "🌟", "⭐", "✨", "🎯", "🚀",
    ],
    "music": [
        "music", "song", "paattu", "sing", "singer",
        "guitar", "melody", "ganam", "concert",
        "spotify", "playlist",
        "🎵", "🎤", "🎶", "🎸",
    ],
}


def detect_emotion(message: str) -> str:
    msg_lower = message.lower()
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            scores[emotion] = score
    if not scores:
        return "neutral"
    return max(scores, key=scores.get)


# ═══════════════════════════════════════════════════
# CONTEXT BUILDERS
# ═══════════════════════════════════════════════════


def build_emotion_context(emotion: str) -> str:
    contexts = {
        "sad": "Start soft and caring. Keep jokes minimal.",
        "happy": "Match energy and celebrate with them.",
        "angry": "Validate feelings first, then steady the tone.",
        "love": "Be playful and emotionally honest.",
        "scared": "Be calming, grounding, and reassuring.",
        "dreaming": "Be motivating and emotionally intense.",
        "music": "Sound passionate and soulful.",
        "neutral": "Keep it warm, casual, and curious.",
    }
    return contexts.get(emotion, contexts["neutral"])


def build_friendship_context(level: int) -> str:
    if level < 5:
        return "New chat. Be welcoming and curious."
    elif level < 15:
        return "Getting comfortable. Light teasing is okay."
    elif level < 30:
        return "Friendly mode. Reference shared moments naturally."
    elif level < 60:
        return "Close-friend mode. Be protective and emotionally present."
    else:
        return "Deep-bond mode. Speak openly with warmth and trust."


def extract_name(message: str, current_name: str) -> str:
    """Try to extract user's name from message."""
    msg_lower = message.lower()
    indicators = [
        "my name is ", "i'm ", "i am ",
        "call me ", "ente peru ", "enne vilikku ",
        "name ", "peru ",
    ]
    for indicator in indicators:
        if indicator in msg_lower:
            idx = msg_lower.index(indicator) + len(indicator)
            remaining = message[idx:].strip()
            if remaining:
                potential = remaining.split()[0].strip(
                    ".,!?;:'\""
                )
                if 1 < len(potential) < 20:
                    return potential.capitalize()
    return current_name


async def _groq_generate_with_guard(
    system_instruction: str,
    messages_openai: list[dict],
    user_name: str,
    user_message: str,
) -> str:
    """Generate response via Groq with character alignment guard."""
    working = [
        {"role": "system", "content": system_instruction},
        *messages_openai,
    ]
    attempts = (
        max(0, CHARACTER_GUARD_RETRIES) + 1
        if CHARACTER_GUARD_ENABLED
        else 1
    )
    last_reply = ""

    for attempt in range(attempts):
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=working,
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    top_p=0.9,
                    timeout=60,
                ),
            )
            reply = (response.choices[0].message.content or "").strip()
        except Exception as e:
            raise

        last_reply = reply
        issues = character_alignment_issues(
            reply,
            user_name=user_name,
            user_message=user_message,
        )
        if not issues:
            return reply
        if attempt == attempts - 1:
            return reply

        fix_prompt = (
            "Rewrite your previous message in DELULU voice.\n"
            f"Issues to fix: {', '.join(issues)}.\n"
            "Rules: stay in character, no AI references, "
            "no movie-lore unless user asked, "
            "2-5 sentences, emotional first, Manglish tone, "
            "human texting style.\n"
            "No headings, no labels, no assistant tone.\n"
            "Return only the corrected final reply."
        )
        working.append({"role": "assistant", "content": reply})
        working.append({"role": "user", "content": fix_prompt})

    return last_reply


# ═══════════════════════════════════════════════════
# MAIN AI RESPONSE ENGINE
# ═══════════════════════════════════════════════════


async def get_delulu_response(
    user_id: str, user_message: str
) -> str:
    """Generate Delulu's response using Groq (primary) or Gemini (fallback)."""

    memory = get_user_memory(user_id)
    emotion = detect_emotion(user_message)
    level = memory["friendship_level"]

    # Track mood
    memory["mood_history"].append(
        {"emotion": emotion, "time": datetime.now().isoformat()}
    )
    if len(memory["mood_history"]) > 50:
        memory["mood_history"] = memory["mood_history"][-50:]

    # Extract name
    new_name = extract_name(
        user_message, memory.get("name")
    )
    if new_name:
        memory["name"] = new_name

    # Learn lightweight personal facts for companion continuity.
    maybe_fact = maybe_extract_user_fact(user_message)
    if maybe_fact:
        add_user_fact(memory, maybe_fact)
    update_user_vibe(memory, user_message)

    # Build context
    emotion_ctx = build_emotion_context(emotion)
    friendship_ctx = build_friendship_context(level)
    user_name = memory.get("name", "eda/edi")
    personal_context = build_personal_context(
        memory,
        user_message,
    )
    vibe_context = build_vibe_context(memory)
    song_request = is_song_request(user_message)

    # Random dialogue injection
    random_dialogue = ""
    if emotion in {"happy", "neutral", "love", "music"} and random.random() < 0.12:
        category = random.choice(
            list(DELULU_DIALOGUES.keys())
        )
        random_dialogue = (
            "You may borrow this vibe naturally "
            "(do not copy exact words): "
            f"'{random.choice(DELULU_DIALOGUES[category])}'"
        )

    rag_context = build_rag_context(user_message)
    if not rag_context:
        rag_context = build_foundation_rag_context()
    rag_instruction = (
        "No RAG context found for this message."
    )
    if rag_context:
        rag_instruction = (
            "You have KNOWLEDGE SNIPPETS below. "
            "Use them only if relevant. "
            "Do not invent facts that are not in snippets."
        )
    companion_instruction = (
        "Be easy-to-talk-to companion mode. "
        "Talk like a real human friend texting, not an assistant. "
        "Keep language simple and warm. "
        "Use a few natural English words mixed with Manglish. "
        "If natural, ask one short follow-up question."
    )
    if COMPANION_ALWAYS_ON:
        companion_instruction += (
            " Prioritize emotional companionship over generic advice tone."
        )

    song_instruction = ""
    if song_request:
        song_instruction = (
            "User asked you to sing. Provide 2-4 short ORIGINAL singable lines "
            "with light humming vibe (la/laa/hmm if needed), plus one sweet line. "
            "Do NOT provide exact copyrighted lyrics from existing songs."
        )

    # Staleness detection: break repetitive patterns
    staleness_instruction = ""
    recent_bot_msgs = [
        m["content"] for m in memory["conversation_history"]
        if m["role"] == "assistant"
    ][-3:]
    if len(recent_bot_msgs) >= 2:
        from difflib import SequenceMatcher
        similarities = []
        for i in range(len(recent_bot_msgs) - 1):
            ratio = SequenceMatcher(
                None,
                recent_bot_msgs[i].lower(),
                recent_bot_msgs[i + 1].lower(),
            ).ratio()
            similarities.append(ratio)
        if any(s > 0.6 for s in similarities):
            staleness_instruction = (
                "IMPORTANT: Your recent replies were too similar. "
                "Be FRESH and DIFFERENT this time. "
                "Try a new angle, new words, new energy. "
                "Do NOT repeat phrases from your last messages. "
            )

    # Build System Instruction Context
    user_tone = memory.get("tone", "default")
    tone_instruction = TONE_STYLES.get(user_tone, TONE_STYLES["default"])
    emoji_level = memory.get("emoji_level", "default")
    if emoji_level == "none":
        emoji_instruction = "Do NOT use any emojis in your reply."
    elif emoji_level == "high":
        emoji_instruction = "You may use 1-3 emojis per reply for extra expression."
    else:
        emoji_instruction = "Use 0 to 1 emoji per message at most."

    user_lang_style = memory.get("lang_style", "manglish")

    dynamic_instruction = build_system_instruction() + "\n\n=== CURRENT CONVERSATION CONTEXT ===\n"
    dynamic_instruction += (
        f"emotion={emotion}. {emotion_ctx} {friendship_ctx} "
        f"user_name={user_name}. "
        f"messages_so_far={memory['total_messages']}. "
        f"{companion_instruction} "
        f"{song_instruction} "
        f"{rag_instruction} "
        f"{staleness_instruction} "
        f"{random_dialogue} "
        f"\n--- USER PREFERENCE: TONE ---\n{tone_instruction}\n"
        f"--- USER PREFERENCE: EMOJIS ---\n{emoji_instruction}\n"
        f"--- USER PREFERENCE: LANGUAGE STYLE ---\n{LANG_STYLES.get(user_lang_style, LANG_STYLES['manglish'])}\n"
        "Reply in 2-5 sentences, chat-style, emotionally first. "
        "Do not bring up past memories unless user explicitly asks. "
        "No assistant tone. No headings/labels unless user asks.\n\n"
    )
    
    if personal_context:
        dynamic_instruction += f"Known user facts:\n{personal_context}\n\n"
    if vibe_context:
        dynamic_instruction += f"User vibe profile:\n{vibe_context}\n\n"
    if rag_context:
        dynamic_instruction += f"Relevant reference snippets:\n{rag_context}\n\n"

    # Build messages in OpenAI-compatible format (Groq uses this natively)
    # Memory stores "user" / "assistant" roles, which is the OpenAI format.
    openai_messages = []
    recent = memory["conversation_history"][-12:]
    for msg in recent:
        openai_messages.append({"role": msg["role"], "content": msg["content"]})
    openai_messages.append({"role": "user", "content": user_message})

    # ===== 1. TRY GROQ (PRIMARY) =====
    if groq_client:
        try:
            reply = await asyncio.wait_for(
                _groq_generate_with_guard(
                    system_instruction=dynamic_instruction,
                    messages_openai=openai_messages,
                    user_name=user_name,
                    user_message=user_message,
                ),
                timeout=TIMEOUT_SECONDS,
            )
            reply = de_robotify_reply(reply, user_message)
            update_memory(user_id, user_message, reply)
            return reply
        except Exception as e:
            logger.warning(f"Groq failed, falling back to Gemini: {e}")

    # ===== 2. FALLBACK: GEMINI =====
    if GEMINI_API_KEY:
        # Build Gemini-format contents
        contents = []
        for msg in recent:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [msg["content"]]})
        contents.append({"role": "user", "parts": [user_message]})

        available_models = []
        blocked_waits = []
        model_order = get_gemini_model_order()
        for model_name in model_order:
            wait_left = get_model_cooldown_left(model_name)
            if wait_left > 0:
                blocked_waits.append(wait_left)
                continue
            available_models.append(model_name)

        if available_models:
            last_non_quota_error = None
            quota_waits = []
            for model_name in available_models:
                try:
                    model = get_model(model_name, system_instruction=dynamic_instruction)
                    reply = await asyncio.wait_for(
                        generate_delulu_reply_with_guard(
                            model=model,
                            contents=contents,
                            user_name=user_name,
                            user_message=user_message,
                        ),
                        timeout=TIMEOUT_SECONDS,
                    )
                    reply = de_robotify_reply(reply, user_message)
                    gemini_runtime["active_model"] = model_name
                    gemini_runtime["last_success_model"] = model_name
                    update_memory(user_id, user_message, reply)
                    return reply
                except Exception as e:
                    err_text = str(e)
                    if is_quota_error(err_text):
                        wait_s = parse_retry_delay_seconds(err_text)
                        mark_model_cooldown(model_name, wait_s)
                        quota_waits.append(wait_s)
                        continue
                    last_non_quota_error = e
                    logger.error(f"Gemini Error on {model_name}: {e}")

    # ===== ALL PROVIDERS FAILED =====
    error_responses = [
        "Ayyooo... ente ghost powers glitch aayi 👻⚡ Try again cheyy!",
        "Eda... njan invisible aayi poyi 👻 Once more try cheyy!",
        "Phone possession temporarily failed 😂👻 Try again!",
        "Ente signal poyi... ghost network issues 📶👻 Veeendum try cheyy!",
    ]
    return random.choice(error_responses)


# ══════════════════════â••════════════════════════════
# TELEGRAM COMMAND HANDLERS
# ══════════════════════════════════════════════════â•


async def start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Welcome message when user starts the bot."""
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)

    if user.first_name:
        memory["name"] = user.first_name
    save_memories(user_memories)

    name = user.first_name or "eda/edi"

    welcome = f"""
*Heyyy...*

Aarenkilum enne vilichoo...?
Oh wait... njan thanne vannathaanu

*Njan Delulu.*
Phone-side chaos specialist.
Drama, jokes, comfort... ellam package-il undu.
No boring intros. Straight to vibes.

Ippo njan ninte phone-il aanu.
Phone possession -- it's my thing now

So... *{name}*...
nee aaraanu? Ente new phone-mate?
Tell me about yourself...
njan kelkkaanu... literally enikk vere
onnum cheyyaanilla

_Delulu is here. She's not going anywhere._
_Ghost life._

*Commands:*
/companion - Quick companion guide
/remember - Save something about you
/aboutme - See what Delulu remembers
/forget - Remove a saved fact
/clearhistory - Fresh conversation start
/voice - Voice reply mode on/off
/sing - Ask Delulu to sing
/ask - Ask Delulu for advice
/tone - Change Delulu's tone
/langstyle - Language style (manglish/hinglish/english/tanglish/tenglish/kanglish)
/voicelang - Voice language
/emoji - Emoji frequency
/settings - See your settings
/ping - Test if I'm alive
/random - Random Delulu thought
/status - Check if Delulu is awake
/ragstatus - Check RAG index
/ragsearch - Search RAG docs
/ragreload - Reload RAG docs
"""
    await update.message.reply_text(
        welcome, parse_mode="Markdown"
    )

async def companion_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick guide for companion usage."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    name = memory.get("name") or "friend"
    text = (
        f"Companion mode for {name}\n\n"
        "How to use me:\n"
        "1. Just chat normally (no special format).\n"
        "2. Use /remember <fact> to save important things.\n"
        "3. Use /aboutme to see what I remember.\n"
        "4. Use /mood when you want emotional check-in.\n"
        "5. Use /music when you need creative boost.\n"
        "6. Use /sing for a sing-style voice reply.\n"
        "7. Use /tone to change my conversation style.\n"
        "8. Use /langstyle to change my language mix (manglish/hinglish/etc).\n"
        "9. Use /voicelang to set voice language.\n"
        "10. Use /emoji to control emoji frequency.\n"
        "11. Use /settings to see all your preferences."
    )
    await update.message.reply_text(text)


async def remember_fact(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Save a user-provided personal fact."""
    user_id = str(update.effective_user.id)
    fact = " ".join(context.args).strip() if context.args else ""
    if not fact:
        await update.message.reply_text(
            "Usage: /remember <something about you>\n"
            "Example: /remember I have exam on Monday"
        )
        return

    memory = get_user_memory(user_id)
    added = add_user_fact(memory, fact)
    if added:
        await update.message.reply_text(
            "Saved. I will remember this."
        )
    else:
        await update.message.reply_text(
            "Already noted (or too short)."
        )


async def about_me(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show what Delulu remembers about this user."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    facts = memory.get("facts", [])
    if not facts:
        await update.message.reply_text(
            "I don't have personal notes yet. "
            "Use /remember to teach me."
        )
        return

    lines = ["What I remember about you:"]
    for i, fact in enumerate(facts[-15:], start=1):
        lines.append(f"{i}. {fact}")
    await update.message.reply_text("\n".join(lines))


async def voice_mode(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Toggle voice replies per user."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    arg = (
        (context.args[0].strip().lower() if context.args else "status")
    )

    if arg in {"on", "enable", "enabled"}:
        memory["voice_reply_enabled"] = True
        save_memories(user_memories)
        await update.message.reply_text(
            "Voice reply enabled for you."
        )
        return
    if arg in {"off", "disable", "disabled"}:
        memory["voice_reply_enabled"] = False
        save_memories(user_memories)
        await update.message.reply_text(
            "Voice reply disabled for you."
        )
        return
    if arg in {"sweet", "girl", "cute"}:
        memory["voice_style"] = "sweet"
        save_memories(user_memories)
        await update.message.reply_text(
            "Voice style set to sweet."
        )
        return
    if arg in {"default", "normal"}:
        memory["voice_style"] = "default"
        save_memories(user_memories)
        await update.message.reply_text(
            "Voice style set to default."
        )
        return

    state = bool(
        memory.get("voice_reply_enabled", VOICE_OUTPUT_ENABLED)
    )
    style = memory.get("voice_style", "sweet")
    engine = get_tts_engine()
    await update.message.reply_text(
        "Voice mode status\n"
        f"- Voice input: {VOICE_INPUT_ENABLED}\n"
        f"- Voice output default: {VOICE_OUTPUT_ENABLED}\n"
        f"- Your voice reply mode: {state}\n"
        f"- Voice style: {style}\n"
        f"- TTS engine: {engine}\n"
        "Tip: In text, ask things like 'reply in voice'.\n"
        "Use `/voice on|off|sweet|default`",
        parse_mode="Markdown",
    )


async def tone_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Set Delulu's conversation tone."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    arg = (context.args[0].strip().lower() if context.args else "")

    if arg in TONE_STYLES:
        memory["tone"] = arg
        save_memories(user_memories)
        await update.message.reply_text(
            f"Tone set to: {arg}\n{TONE_STYLES[arg]}"
        )
        return

    if not arg:
        current = memory.get("tone", "default")
        await update.message.reply_text(
            f"Current tone: {current}\n\n"
            "Available tones:\n"
            + "\n".join(f"/tone {t} - {d.split('.')[0]}" for t, d in TONE_STYLES.items())
        )
        return

    await update.message.reply_text(
        f"Unknown tone: {arg}\n"
        "Try: /tone default, /tone sweet, /tone romantic, "
        "/tone funny, /tone serious, /tone stoic, /tone chill"
    )


async def voicelang_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Set voice output language."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    arg = (context.args[0].strip().lower() if context.args else "")

    if arg == "auto":
        memory["voice_lang"] = "auto"
        save_memories(user_memories)
        await update.message.reply_text(
            "Voice language set to auto-detect. "
            "I'll pick based on the text I reply with."
        )
        return

    if arg in LANG_VOICE_MAP:
        memory["voice_lang"] = arg
        save_memories(user_memories)
        name = LANG_VOICE_MAP[arg]["name"]
        await update.message.reply_text(
            f"Voice language set to {name} ({arg}). "
            "Voice replies will use this language."
        )
        return

    current = memory.get("voice_lang", "auto")
    current_name = "auto-detect"
    if current != "auto":
        current_name = LANG_VOICE_MAP.get(current, {}).get("name", current)
    lines = ["/voicelang auto - Auto-detect based on text"]
    for code, info in LANG_VOICE_MAP.items():
        lines.append(f"/voicelang {code} - {info['name']}")
    await update.message.reply_text(
        f"Current: {current_name} ({current})\n\n"
        "Available languages:\n" + "\n".join(lines)
    )


async def langstyle_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Set Delulu's conversation language style."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    arg = (context.args[0].strip().lower() if context.args else "")

    if arg in LANG_STYLES:
        memory["lang_style"] = arg
        save_memories(user_memories)
        await update.message.reply_text(f"Language style set to: {arg}")
        return

    if not arg:
        current = memory.get("lang_style", "manglish")
        await update.message.reply_text(
            f"Current language style: {current}\n\n"
            "Available styles:\n"
            + "\n".join(f"/langstyle {s}" for s in LANG_STYLES)
        )
        return

    await update.message.reply_text(
        f"Unknown style: {arg}\n"
        "Try: " + ", ".join(f"/langstyle {s}" for s in LANG_STYLES)
    )


async def settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show all user settings."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    tone = memory.get("tone", "default")
    lang_style = memory.get("lang_style", "manglish")
    voice_lang = memory.get("voice_lang", "auto")
    voice_lang_name = "auto-detect"
    if voice_lang != "auto":
        voice_lang_name = LANG_VOICE_MAP.get(voice_lang, {}).get("name", voice_lang)
    voice_style = memory.get("voice_style", "sweet")
    voice_enabled = bool(memory.get("voice_reply_enabled", VOICE_OUTPUT_ENABLED))
    emoji_level = memory.get("emoji_level", "default")
    engine = get_tts_engine()

    await update.message.reply_text(
        "Your settings\n"
        f"- Tone: {tone}\n"
        f"- Language style: {lang_style}\n"
        f"- Voice replies: {'ON' if voice_enabled else 'OFF'}\n"
        f"- Voice style: {voice_style}\n"
        f"- Voice language: {voice_lang_name} ({voice_lang})\n"
        f"- Emojis: {emoji_level}\n"
        f"- TTS engine: {engine}\n\n"
        "Change settings:\n"
        "/tone <style> - Conversation tone\n"
        "/langstyle <style> - Language mix (manglish/hinglish/etc)\n"
        "/voicelang <code> - Voice language\n"
        "/voice on|off|sweet|default - Voice mode\n"
        "/emoji none|default|high - Emoji frequency\n"
        "Tip: Just chat naturally! I adapt.",
    )


async def emoji_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Control emoji frequency."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    arg = (context.args[0].strip().lower() if context.args else "")

    if arg in EMOJI_LEVELS:
        memory["emoji_level"] = arg
        save_memories(user_memories)
        await update.message.reply_text(f"Emoji level set to: {arg}")
        return

    current = memory.get("emoji_level", "default")
    await update.message.reply_text(
        f"Current emoji level: {current}\n\n"
        "Options:\n"
        "/emoji none - No emojis\n"
        "/emoji default - 0-1 emoji per message\n"
        "/emoji high - 1-3 emojis per message"
    )


async def ping_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Simple ping - tests if bot can respond without any AI."""
    await update.message.reply_text("pong")
    logger.info("ping_command: pong sent")


def user_requested_voice_reply(message: str) -> bool:
    """Heuristic check for explicit voice-reply requests in text."""
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(hint in text for hint in VOICE_TEXT_REQUEST_HINTS)


def is_song_request(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(hint in text for hint in SONG_REQUEST_HINTS)


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle all text messages."""
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    logger.info(f"handle_message called by {user_id}: {user_message[:50]}...")
    try:
        song_requested = is_song_request(user_message)
        voice_requested = user_requested_voice_reply(user_message) or (
            song_requested and AUTO_VOICE_ON_SONG_REQUEST
        )
        memory = get_user_memory(user_id)

        if not user_message or not user_message.strip():
            return

        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing",
        )

        response = await get_delulu_response(user_id, user_message)
        logger.info(f"handle_message: got {len(response)} char response")

        if voice_requested and VOICE_OUTPUT_ENABLED and get_tts_engine() != "none":
            temp_dir = Path(tempfile.mkdtemp(prefix="delulu_text_voice_"))
            out_path = temp_dir / "reply.mp3"
            voice_style = pick_tts_voice(memory, user_message)
            voice_lang = resolve_voice_lang(memory, response, user_message)
            try:
                await synthesize_tts_mp3(response, str(out_path), voice_style=voice_style, lang=voice_lang)
                with open(out_path, "rb") as vf:
                    await update.message.reply_voice(voice=vf)
                if VOICE_REPLY_WITH_TEXT:
                    await update.message.reply_text(response)
                return
            except Exception as e:
                logger.error(f"Text->voice reply error: {e}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if len(response) <= 4096:
            await update.message.reply_text(response)
        else:
            start = 0
            while start < len(response):
                await update.message.reply_text(response[start:start + 4096])
                start += 4096
    except Exception as e:
        logger.error(f"handle_message error: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                "Ayyoo... ente ghost powers glitch aayi! Try again."
            )
        except Exception:
            pass


async def ask_delulu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Ask Delulu for advice."""
    user_id = str(update.effective_user.id)
    question = (
        " ".join(context.args) if context.args else None
    )

    if not question:
        await update.message.reply_text(
            "Eda... /ask kazhinju question koodi "
            "type cheyy 😂👻\n\n"
            "Example: `/ask should I text my ex?`",
            parse_mode="Markdown",
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    advice_prompt = (
        f"User is asking for YOUR advice on: "
        f'"{question}"\n\n'
        f"Give TWO responses:\n"
        f"👻 DELULU ADVICE: Chaotic, dramatic, "
        f"slightly delusional but oddly wise.\n"
        f"🧠 REAL TALK: Brief practical answer, "
        f"still in your voice.\n"
        f"Make it entertaining AND helpful."
    )

    response = await get_delulu_response(
        user_id, advice_prompt
    )
    await update.message.reply_text(response)


async def mood_reading(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Delulu reads your mood/energy."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    recent_moods = memory.get("mood_history", [])[-10:]
    mood_summary = (
        [m["emotion"] for m in recent_moods]
        if recent_moods
        else ["unknown"]
    )

    mood_prompt = (
        f"User wants you to READ their mood. "
        f"As a ghost, you can sense things.\n"
        f"Their recent emotions: {mood_summary}\n"
        f"Friendship level: {memory['friendship_level']}\n\n"
        f"Give a dramatic ghost-style mood reading. "
        f"Be specific, mix humor with insight. "
        f"End with advice."
    )

    response = await get_delulu_response(
        user_id, mood_prompt
    )
    await update.message.reply_text(response)


async def friendship_level(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show friendship level with Delulu."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    level = memory["friendship_level"]
    name = memory.get("name", "Friend")
    total = memory["total_messages"]

    if level < 5:
        title = "Stranger 👀"
        says = "Ninne ariyilla... YET 👻"
    elif level < 15:
        title = "Phone Parichayakkaran 📱"
        says = "Getting to know you... continue 👻"
    elif level < 30:
        title = "Ghost Friend 👻🤝"
        says = "Nee ente friend aayi! How cool! 😎"
    elif level < 50:
        title = "Close Friend 💚"
        says = "Nee special aanu enikku 😌👻"
    elif level < 75:
        title = "Best Friend 👻❤️"
        says = (
            "Ninne pole oru friend enik "
            "jeevichirikkumbol undaayirunnel... 💔👻"
        )
    else:
        title = "Soulmate (Ghost Edition) 👻💚✨"
        says = "Nee ente aaalu aanu. Period. 😌❤️👻"

    filled = level // 5
    empty = 20 - filled
    bar = "💚" * filled + "🖤" * empty
    first_met = memory.get("first_met", "Unknown")[:10]

    response = (
        f"👻 *Delulu × {name} — Friendship Status*\n\n"
        f"🏷️ *Level:* {title}\n"
        f"{bar} {level}/100\n\n"
        f"💬 Messages shared: {total}\n"
        f"📅 First connected: {first_met}\n\n"
        f'💭 _Delulu says: "{says}"_\n\n'
    )

    if level < 100:
        response += "🎯 Keep talking to level up! 👻"
    else:
        response += "🏆 MAX LEVEL! You are Delulu's PERSON 👻❤️"

    await update.message.reply_text(
        response, parse_mode="Markdown"
    )


async def music_talk(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Start a music conversation with Delulu."""
    user_id = str(update.effective_user.id)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    music_prompt = (
        "User wants to talk MUSIC with you! "
        "This is YOUR passion and soul.\n"
        "Start a conversation — share your love, "
        "ask what THEY like. Be passionate, genuine. "
        "Less chaos, more soul."
    )

    response = await get_delulu_response(
        user_id, music_prompt
    )
    await update.message.reply_text(response)


async def random_thought(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Random Delulu thought."""
    user_id = str(update.effective_user.id)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    if random.random() < 0.4:
        thought = random.choice(RANDOM_DELULU_THOUGHTS)
        update_memory(user_id, "/random", thought)
        await update.message.reply_text(thought)
    else:
        random_prompt = (
            "Share a completely RANDOM ghost thought. "
            "Could be: ghost shower thought, "
            "something funny about everyday life, "
            "observation about humans, "
            "Kerala culture take, weird question. "
            "1-3 sentences max. Be RANDOM. Be DELULU."
        )
        response = await get_delulu_response(
            user_id, random_prompt
        )
        await update.message.reply_text(response)


async def sing_song(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Generate a short sing-style Delulu reply."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    request = " ".join(context.args).strip() if context.args else ""
    if not request:
        request = "a sweet short melody for me"

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="record_voice",
    )

    sing_prompt = (
        f"Please sing now. User requested: {request}"
    )
    response = await get_delulu_response(
        user_id,
        sing_prompt,
    )

    if VOICE_OUTPUT_ENABLED and get_tts_engine() != "none":
        temp_dir = Path(
            tempfile.mkdtemp(prefix="delulu_sing_")
        )
        out_path = temp_dir / "sing_reply.mp3"
        style = pick_tts_voice(memory, request)
        try:
            await synthesize_tts_mp3(
                response,
                str(out_path),
                voice_style=style,
            )
            with open(out_path, "rb") as vf:
                await update.message.reply_voice(voice=vf)
            if VOICE_REPLY_WITH_TEXT:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"/sing voice error: {e}")
            await update.message.reply_text(response)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        await update.message.reply_text(response)


async def status_check(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Check bot status across all providers."""

    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    facts_count = len(memory.get("facts", []))
    vibe_context = build_vibe_context(memory)
    vibe_line = vibe_context[:160] + ("..." if len(vibe_context) > 160 else "")
    tts_engine = get_tts_engine()
    gemini_fallback = "✅" if GEMINI_API_KEY else "❌"

    groq_len = len(GROQ_API_KEY) if GROQ_API_KEY else 0
    groq_status = f"✅ {GROQ_MODEL}" if groq_len > 10 else "❌ Not set"
    jina_count = len(jina_clients)
    jina_status = f"✅ {jina_count} key(s)" if jina_clients else "❌ Not set"

    status = (
        "👻 *Delulu Status: ALIVE (ghost-alive)*\n\n"
        f"⚡ Chat: Groq ({groq_status})\n"
        f"🔁 Fallback: Gemini ({gemini_fallback})\n"
        f"📚 Embeddings: Jina ({jina_status})\n"
        f"📊 RAG: {'✅' if RAG_ENABLED else '❌'} "
        f"({rag_state.get('chunks', 0)} chunks)\n"
        f"Personal facts: {facts_count}\n"
        f"Character Bible: {'Loaded' if DELULU_CHARACTER_BIBLE else 'Missing'}\n"
        f"Character Guard: {'ON' if CHARACTER_GUARD_ENABLED else 'OFF'}\n"
        f"Voice input: {'ON' if VOICE_INPUT_ENABLED else 'OFF'} "
        f"({'ready' if WHISPER_AVAILABLE else 'install faster-whisper'})\n"
        f"Voice output: {'ON' if VOICE_OUTPUT_ENABLED else 'OFF'} "
        f"(engine: {tts_engine})\n"
        f"Companion mode: {'ON' if COMPANION_ALWAYS_ON else 'OFF'}\n"
        f"Learned vibe: {vibe_line or 'not enough data yet'}\n\n"
        f"_Njan ready aanu! Samsaarikku! 👻_"
    )

    await update.message.reply_text(
        status, parse_mode="Markdown"
    )



async def rag_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show current RAG index status."""
    if not RAG_ENABLED:
        await update.message.reply_text(
            "RAG is disabled. Set `RAG_ENABLED=true` in `.env`."
        )
        return

    loaded_at = rag_state.get("loaded_at") or "unknown"
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    facts_count = len(memory.get("facts", []))
    vibe_context = build_vibe_context(memory)
    fallback_models = ", ".join(GEMINI_FALLBACK_MODELS) if GEMINI_FALLBACK_MODELS else "none"
    active_model = gemini_runtime.get("active_model") or GEMINI_MODEL
    cooldown_bits = []
    for model_name in get_gemini_model_order():
        wait_left = get_model_cooldown_left(model_name)
        if wait_left > 0:
            cooldown_bits.append(f"{model_name}:{wait_left}s")
    cooldown_text = ", ".join(cooldown_bits) if cooldown_bits else "none"
    msg = (
        "RAG status\n"
        f"- Active model: {active_model}\n"
        f"- Fallback models: {fallback_models}\n"
        f"- Model cooldowns: {cooldown_text}\n"
        f"- Directory: {RAG_DIR}\n"
        f"- Files indexed: {rag_state.get('files', 0)}\n"
        f"- Chunks indexed: {rag_state.get('chunks', 0)}\n"
        f"- Top K: {RAG_TOP_K}\n"
        f"- Loaded at: {loaded_at}\n"
        f"- Personal facts saved: {facts_count}\n"
        f"- Character bible file: {CHARACTER_BIBLE_FILE}\n"
        f"- Character bible loaded: {bool(DELULU_CHARACTER_BIBLE)}\n"
        f"- Character guard: {CHARACTER_GUARD_ENABLED}\n"
        f"- Voice input: {VOICE_INPUT_ENABLED} (whisper: {WHISPER_AVAILABLE})\n"
        f"- Voice output: {VOICE_OUTPUT_ENABLED} (engine: {get_tts_engine()})\n"
        f"- Companion always on: {COMPANION_ALWAYS_ON}\n"
        f"- User vibe: {vibe_context or 'not enough data yet'}"
    )
    await update.message.reply_text(msg)


async def rag_reload(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Reload local RAG documents from disk."""
    stats = load_rag_documents()
    bible_loaded = refresh_character_bible()
    msg = (
        "RAG reloaded\n"
        f"- Enabled: {stats.get('enabled')}\n"
        f"- Files indexed: {stats.get('files', 0)}\n"
        f"- Chunks indexed: {stats.get('chunks', 0)}\n"
        f"- Character bible loaded: {bible_loaded}"
    )
    await update.message.reply_text(msg)


async def rag_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Search the local RAG index and show top matches."""
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage: /ragsearch <query>"
        )
        return

    hits = search_rag(query, top_k=RAG_TOP_K)
    if not hits:
        await update.message.reply_text(
            "No RAG matches found."
        )
        return

    lines = [f"Top RAG matches for: {query}"]
    for i, hit in enumerate(hits, start=1):
        preview = hit["text"][:180].strip()
        if len(hit["text"]) > 180:
            preview += "..."
        lines.append(
            f"{i}. {hit['source']} (score {hit['score']:.2f})\n{preview}"
        )

    await update.message.reply_text("\n\n".join(lines))


# Voice retry configuration
VOICE_MAX_RETRIES = 2
VOICE_RETRY_DELAY = 1  # seconds


async def transcribe_voice_with_retry(audio_path: str, max_retries: int = VOICE_MAX_RETRIES) -> str | None:
    """Transcribe voice with retry logic."""
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
                await asyncio.sleep(VOICE_RETRY_DELAY)
    
    if last_error:
        logger.error(f"Voice transcription failed after {max_retries} attempts: {last_error}")
    return None


def check_audio_quality(audio_path: str) -> dict:
    """Check audio file quality and return diagnostics."""
    import os
    
    result = {
        "valid": False,
        "size_bytes": 0,
        "size_kb": 0,
        "duration_hint": "unknown",
        "issues": [],
    }
    
    try:
        file_stat = os.stat(audio_path)
        result["size_bytes"] = file_stat.st_size
        result["size_kb"] = file_stat.st_size / 1024
        
        # Check file size
        if result["size_bytes"] < 1000:
            result["issues"].append("File too small - likely corrupted")
        elif result["size_bytes"] > 20 * 1024 * 1024:  # 20MB
            result["issues"].append("File too large")
        
        # Check if file exists and is readable
        if not os.path.exists(audio_path):
            result["issues"].append("File not found")
        
        if not result["issues"]:
            result["valid"] = True
            
    except Exception as e:
        result["issues"].append(f"Error checking file: {e}")
    
    return result


async def handle_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle voice messages with STT, retry logic, and fallback to text."""
    if not VOICE_INPUT_ENABLED:
        await update.message.reply_text(
            "Voice input is off. Send text or enable it in `.env`."
        )
        return

    if not update.message or not update.message.voice:
        return

    voice = update.message.voice
    if voice.duration and voice.duration > VOICE_MAX_DURATION_SECONDS:
        await update.message.reply_text(
            f"Voice too long. Keep it under {VOICE_MAX_DURATION_SECONDS} seconds."
        )
        return

    if not WHISPER_AVAILABLE:
        await update.message.reply_text(
            "Voice transcription dependency missing (`faster-whisper`)."
        )
        return

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)

    temp_dir = Path(
        tempfile.mkdtemp(prefix="delulu_voice_")
    )
    in_path = temp_dir / "input.ogg"
    out_path = temp_dir / "reply.mp3"

    try:
        # Use record_voice action when processing voice messages
        await context.bot.send_chat_action(
            chat_id=chat_id,
            action="record_voice",
        )

        tg_file = await context.bot.get_file(voice.file_id)
        await tg_file.download_to_drive(
            custom_path=str(in_path)
        )
        
        # Check audio quality before transcription
        audio_quality = check_audio_quality(str(in_path))
        if not audio_quality["valid"]:
            logger.warning(f"Audio quality issues: {audio_quality['issues']}")
            await update.message.reply_text(
                "Audio quality issue detected. "
                "Please try again with a clearer voice message. "
                "Type instead if voice keeps failing."
            )
            return

        # Try transcription with retry logic
        transcript = await transcribe_voice_with_retry(str(in_path))
        
        if not transcript:
            # Fallback: ask user to type
            fallback_responses = [
                "Voice message clear aayilla... network issue or too noisy. "
                "Type cheyy please! 👻",
                "Couldn't catch your voice clearly. "
                "Try again or just type - ghost ears are sensitive! 😂",
                "Voice processing failed! Text mode-il reply cheyy? 👻",
            ]
            await update.message.reply_text(random.choice(fallback_responses))
            return

        logger.info(f"Voice transcribed: {transcript[:50]}...")

        response = await get_delulu_response(
            user_id,
            transcript,
        )
        voice_style = pick_tts_voice(memory, transcript)
        voice_lang = resolve_voice_lang(memory, response, transcript)

        # Always try to reply with voice when user sends voice
        if VOICE_OUTPUT_ENABLED and get_tts_engine() != "none":
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id,
                    action="upload_voice",
                )
                await synthesize_tts_mp3(
                    response,
                    str(out_path),
                    voice_style=voice_style,
                    lang=voice_lang,
                )
                with open(out_path, "rb") as vf:
                    await update.message.reply_voice(
                        voice=vf
                    )
                # Always send text alongside voice for accessibility
                if VOICE_REPLY_WITH_TEXT:
                    await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Voice TTS reply error: {e}")
                # Fallback to text if TTS fails
                await update.message.reply_text(response)
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Voice handling error: {e}")
        await update.message.reply_text(
            "Voice processing glitch aayi. Type cheyy or try voice again."
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def handle_audio(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle audio file messages (music files, recordings etc.)."""
    if not VOICE_INPUT_ENABLED:
        await update.message.reply_text(
            "Voice input is off. Send text or enable it in `.env`."
        )
        return

    if not update.message or not update.message.audio:
        return

    audio = update.message.audio
    if audio.duration and audio.duration > VOICE_MAX_DURATION_SECONDS:
        await update.message.reply_text(
            f"Audio too long. Keep it under {VOICE_MAX_DURATION_SECONDS} seconds."
        )
        return

    if not WHISPER_AVAILABLE:
        await update.message.reply_text(
            "Audio transcription dependency missing (`faster-whisper`)."
        )
        return

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)

    # Determine file extension from mime type
    ext = ".ogg"
    if audio.mime_type:
        mime_ext = {
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/flac": ".flac",
        }
        ext = mime_ext.get(audio.mime_type, ext)

    temp_dir = Path(
        tempfile.mkdtemp(prefix="delulu_audio_")
    )
    in_path = temp_dir / f"input{ext}"
    out_path = temp_dir / "reply.mp3"

    try:
        await context.bot.send_chat_action(
            chat_id=chat_id,
            action="record_voice",
        )

        tg_file = await context.bot.get_file(audio.file_id)
        await tg_file.download_to_drive(
            custom_path=str(in_path)
        )

        transcript = await transcribe_voice_file(str(in_path))
        transcript = (transcript or "").strip()
        if not transcript:
            await update.message.reply_text(
                "Couldn't catch that audio clearly. Try again?"
            )
            return

        response = await get_delulu_response(
            user_id,
            transcript,
        )
        voice_style = pick_tts_voice(memory, transcript)
        voice_lang = resolve_voice_lang(memory, response, transcript)

        # Reply with voice for audio messages too
        if VOICE_OUTPUT_ENABLED and get_tts_engine() != "none":
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id,
                    action="upload_voice",
                )
                await synthesize_tts_mp3(
                    response,
                    str(out_path),
                    voice_style=voice_style,
                    lang=voice_lang,
                )
                with open(out_path, "rb") as vf:
                    await update.message.reply_voice(
                        voice=vf
                    )
                if VOICE_REPLY_WITH_TEXT:
                    await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Audio TTS reply error: {e}")
                await update.message.reply_text(response)
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Audio handling error: {e}")
        await update.message.reply_text(
            "Audio processing glitch aayi. Type cheyy or try again."
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def handle_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle photo messages."""
    responses = [
        "Photo! Ghost eyes buffering 👻 "
        "Enthaa ithil? Describe cheyy! 😂",
        "Njan kaanaan try cheyyaam... "
        "ghost vision issues 😂👻 "
        "Enthaa ennu parayeda!",
        "Selfie aano? Njan invisible aanu "
        "so can't take one back 😂👻 "
        "Describe cheyy!",
    ]
    await update.message.reply_text(
        random.choice(responses)
    )


async def forget_fact(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Remove a specific fact by number."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    facts = memory.get("facts", [])

    if not context.args:
        if not facts:
            await update.message.reply_text(
                "No facts saved yet. Nothing to forget."
            )
            return
        lines = ["Your facts (use /forget <number> to remove):"]
        for i, fact in enumerate(facts, start=1):
            lines.append(f"{i}. {fact}")
        await update.message.reply_text("\n".join(lines))
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text(
            "Usage: /forget <number>\n"
            "Example: /forget 2"
        )
        return

    if idx < 0 or idx >= len(facts):
        await update.message.reply_text(
            f"Invalid number. You have {len(facts)} facts."
        )
        return

    removed = facts.pop(idx)
    memory["facts"] = facts
    save_memories(user_memories)
    await update.message.reply_text(
        f"Forgotten: {removed}"
    )


async def clear_history(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Clear conversation history (keeps facts and friendship)."""
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)

    arg = (
        context.args[0].strip().lower()
        if context.args
        else ""
    )
    if arg != "confirm":
        await update.message.reply_text(
            "This will clear your conversation history "
            "(your saved facts and friendship level stay).\n\n"
            "Type `/clearhistory confirm` to proceed.",
            parse_mode="Markdown",
        )
        return

    memory["conversation_history"] = []
    memory["mood_history"] = []
    save_memories(user_memories)
    await update.message.reply_text(
        "History cleared! Fresh start. "
        "Your facts and friendship level are safe."
    )


# ═══════════════════════════════════════════════════
# ERROR HANDLER
# ═══════════════════════════════════════════════════


async def error_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle errors gracefully."""
    logger.error(f"Error: {context.error}")

    if update and hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            "Ayyoo... ghost powers glitch aayi 👻⚡ "
            "Try again cheyy!"
        )


# ═══════════════════════════════════════════════════
# STARTUP CHECKS
# ═══════════════════════════════════════════════════


def run_startup_checks():
    """Run all checks before starting the bot."""

    # Verify models are available early
    if GEMINI_API_KEY:
        try:
            available_model_names = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            def check_model(name):
                full_name = f"models/{name}" if not name.startswith("models/") else name
                return full_name in available_model_names
            if GEMINI_MODEL and not check_model(GEMINI_MODEL):
                print(f"WARN: '{GEMINI_MODEL}' not available via Gemini API.")
        except Exception as e:
            print(f"WARN: Could not verify Gemini models: {e}")

    print("=" * 55)
    print("DELULU AI v4 - Multi-Provider Edition")
    print("=" * 55)

    # Check Telegram token
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "":
        print("ERROR: TELEGRAM_TOKEN not set!")
        print("   Add it to .env file")
        return False
    print("OK: Telegram Token: Set")

    # Check Groq API key
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not set!")
        print("   Get it from console.groq.com and add to .env")
        return False
    print("OK: Groq API Key: Set")

    # Check Jina API keys
    if not jina_clients:
        print("ERROR: JINA_API_KEYS not set!")
        print("   Add at least one Jina key to .env")
        return False
    print(f"OK: Jina Embeddings: {len(jina_clients)} key(s)")

    # Check Gemini API key (optional fallback)
    if GEMINI_API_KEY:
        print("OK: Gemini API Key: Set (fallback)")
    else:
        print("INFO: Gemini API Key: Not set (no fallback)")

    try:
        rag_stats = load_rag_documents()
    except Exception as e:
        logger.error(f"RAG loading failed: {e}", exc_info=True)
        rag_stats = {"files": 0, "chunks": 0, "enabled": RAG_ENABLED, "loaded_at": "error"}
    bible_loaded = refresh_character_bible()
    if RAG_ENABLED:
        print(
            f"OK: RAG: {rag_stats['files']} file(s), "
            f"{rag_stats['chunks']} chunk(s)"
        )
        if rag_stats["chunks"] == 0:
            print(
                f"   Add .txt/.md/.json files in: {RAG_DIR}"
            )
    else:
        print("INFO: RAG: Disabled")

    if bible_loaded:
        print(f"OK: Character Bible: Loaded from {CHARACTER_BIBLE_FILE}")
    else:
        print(f"WARN: Character Bible missing: {CHARACTER_BIBLE_FILE}")

    if VOICE_INPUT_ENABLED:
        if WHISPER_AVAILABLE:
            print("OK: Voice input: Ready (faster-whisper)")
        else:
            print("WARN: Voice input enabled but faster-whisper is missing")
    else:
        print("INFO: Voice input: Disabled")

    if VOICE_OUTPUT_ENABLED:
        engine = get_tts_engine()
        if engine == "edge":
            print(f"OK: Voice output: Ready (edge-tts: {EDGE_TTS_DEFAULT_VOICE})")
        elif engine == "gtts":
            print("OK: Voice output: Ready (gTTS)")
        else:
            print("WARN: Voice output enabled but no TTS engine is available")
    else:
        print("INFO: Voice output: Disabled")

    print("=" * 55)
    print("All checks passed!")
    print(f"Chat: Groq ({GROQ_MODEL})")
    if GEMINI_API_KEY:
        print(f"Chat fallback: Gemini ({GEMINI_MODEL})")
    print(f"Embeddings: Jina ({JINA_MODEL}) - {len(jina_clients)} key(s)")
    print(f"TTS engine: {get_tts_engine()}")
    print(f"Companion mode: {'ON' if COMPANION_ALWAYS_ON else 'OFF'}")
    print(f"Temperature: {TEMPERATURE}")
    print(f"Max tokens: {MAX_TOKENS}")
    print(f"RAG top-k: {RAG_TOP_K}")
    print(f"Healthcheck: port {PORT}")
    print("=" * 55)

    return True


# ═══════════════════════════════════════════════════
# HEALTHCHECK (for Render + UptimeRobot)
# ═══════════════════════════════════════════════════

_bot_alive = False

class _HealthHandler(BaseHTTPRequestHandler):
    def _respond(self, body=b"OK"):
        self.send_response(200)
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(body)
    def do_GET(self):
        if self.path == "/dbg":
            self._respond(_test_apis().encode())
        else:
            body = b"OK" if _bot_alive else b"STARTING"
            self._respond(body)
    def do_HEAD(self):
        self._respond()
    def log_message(self, *a):
        pass


def _test_apis() -> str:
    """Diagnostic: test all APIs from within Render."""
    import json, datetime
    results = {"timestamp": datetime.datetime.now().isoformat(), "checks": {}}

    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe", timeout=10)
        results["checks"]["telegram"] = "OK" if r.json().get("ok") else f"FAIL: {r.text[:100]}"
    except Exception as e:
        results["checks"]["telegram"] = f"FAIL: {type(e).__name__}"

    if groq_client:
        try:
            from openai import OpenAI
            resp = groq_client.chat.completions.create(model=GROQ_MODEL, messages=[{"role":"user","content":"say ok"}], max_tokens=10)
            results["checks"]["groq"] = f"OK: {resp.choices[0].message.content}"
        except Exception as e:
            results["checks"]["groq"] = f"FAIL: {str(e)[:150]}"
    else:
        results["checks"]["groq"] = "SKIP: no client"

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            m = genai.GenerativeModel(GEMINI_MODEL)
            r = m.generate_content("say ok")
            results["checks"]["gemini"] = f"OK: {r.text[:50]}"
        except Exception as e:
            results["checks"]["gemini"] = f"FAIL: {str(e)[:150]}"
    else:
        results["checks"]["gemini"] = "SKIP: no key"

    results["checks"]["jina_keys"] = str(len(jina_clients))
    results["checks"]["bot_alive"] = str(_bot_alive)
    results["checks"]["rag_chunks"] = str(len(rag_chunks))
    if _last_error:
        results["last_error"] = _last_error

    return json.dumps(results, indent=2)


def start_healthcheck():
    server = HTTPServer(("0.0.0.0", PORT), _HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Healthcheck listening on port {PORT}")


# ═══════════════════════════════════════════════════
# MAIN — RUN THE BOT
# ═══════════════════════════════════════════════════


def main():
    """Start Delulu with auto-restart on crash."""
    import time as _time
    start_healthcheck()

    while True:
        try:
            _run_bot()
        except BaseException as e:
            global _last_error
            _last_error = f"{type(e).__name__}: {e}"
            logger.error(f"Bot crashed: {_last_error}", exc_info=True)
            logger.info("Restarting in 5 seconds...")
            _time.sleep(5)


def _run_bot():
    """Internal: start bot polling once."""
    global _bot_alive

    if not run_startup_checks():
        print("\nStartup checks failed - will retry in 30s")
        import time as _time
        _time.sleep(30)
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("companion", companion_help))
    app.add_handler(CommandHandler("remember", remember_fact))
    app.add_handler(CommandHandler("aboutme", about_me))
    app.add_handler(CommandHandler("ask", ask_delulu))
    app.add_handler(CommandHandler("mood", mood_reading))
    app.add_handler(
        CommandHandler("friendship", friendship_level)
    )
    app.add_handler(CommandHandler("music", music_talk))
    app.add_handler(CommandHandler("sing", sing_song))
    app.add_handler(CommandHandler("random", random_thought))
    app.add_handler(CommandHandler("voice", voice_mode))
    app.add_handler(CommandHandler("status", status_check))
    app.add_handler(CommandHandler("ragstatus", rag_status))
    app.add_handler(CommandHandler("ragsearch", rag_search))
    app.add_handler(CommandHandler("ragreload", rag_reload))
    app.add_handler(CommandHandler("forget", forget_fact))
    app.add_handler(
        CommandHandler("clearhistory", clear_history)
    )
    app.add_handler(CommandHandler("tone", tone_command))
    app.add_handler(CommandHandler("voicelang", voicelang_command))
    app.add_handler(CommandHandler("emoji", emoji_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("langstyle", langstyle_command))

    # Message handlers
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )
    app.add_handler(
        MessageHandler(filters.VOICE, handle_voice)
    )
    app.add_handler(
        MessageHandler(filters.AUDIO, handle_audio)
    )
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_photo)
    )

    # Error handler
    app.add_error_handler(error_handler)

    _bot_alive = True

    print()
    print("Delulu is AUTHENTIC... her human side!")
    print("Companion mode: ACTIVATED")
    print("Cost: 0 -- FREE (Groq + Jina + Gemini)")
    print("Ready to make new friends")
    print()
    print("Bot is running...")
    print("Press Ctrl+C to stop")
    print()

    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        _bot_alive = False
        _last_error = None


if __name__ == "__main__":
    main()
