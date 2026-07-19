import os
import logging
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("delulu")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
GEMINI_FALLBACK_MODELS: list[str] = []
JINA_API_KEYS_RAW = os.getenv("JINA_API_KEYS", "")
JINA_MODEL = os.getenv("JINA_MODEL", "jina-embeddings-v3")

PORT = int(os.getenv("PORT", "10000"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))
MAX_TOKENS = 300
TEMPERATURE = 0.8

RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
RAG_DIR = os.getenv("RAG_DIR", "rag_data")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_CHUNK_WORDS = int(os.getenv("RAG_CHUNK_WORDS", "120"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "30"))
RAG_MAX_SNIPPET_CHARS = int(os.getenv("RAG_MAX_SNIPPET_CHARS", "600"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "1.5"))
CHARACTER_BIBLE_FILE = os.getenv("CHARACTER_BIBLE_FILE", "rag_data/delulu_character_bible.md")
CHARACTER_GUARD_ENABLED = os.getenv("CHARACTER_GUARD_ENABLED", "true").lower() == "true"
CHARACTER_GUARD_RETRIES = 0

PERSONAL_FACTS_LIMIT = int(os.getenv("PERSONAL_FACTS_LIMIT", "40"))
PERSONAL_FACTS_TOP_K = int(os.getenv("PERSONAL_FACTS_TOP_K", "4"))

VOICE_INPUT_ENABLED = os.getenv("VOICE_INPUT_ENABLED", "true").lower() == "true"
VOICE_OUTPUT_ENABLED = os.getenv("VOICE_OUTPUT_ENABLED", "true").lower() == "true"
VOICE_REPLY_WITH_TEXT = os.getenv("VOICE_REPLY_WITH_TEXT", "true").lower() == "true"
VOICE_TRANSCRIBE_MODEL = os.getenv("VOICE_TRANSCRIBE_MODEL", "base")
VOICE_WHISPER_COMPUTE_TYPE = os.getenv("VOICE_WHISPER_COMPUTE_TYPE", "int8")
VOICE_MAX_DURATION_SECONDS = int(os.getenv("VOICE_MAX_DURATION_SECONDS", "120"))
TTS_LANG = os.getenv("TTS_LANG", "en")
TTS_SLOW = os.getenv("TTS_SLOW", "false").lower() == "true"
VOICE_TTS_ENGINE = os.getenv("VOICE_TTS_ENGINE", "auto")
EDGE_TTS_DEFAULT_VOICE = os.getenv("EDGE_TTS_DEFAULT_VOICE", "en-IN-NeerjaNeural")
EDGE_TTS_SWEET_VOICE = os.getenv("EDGE_TTS_SWEET_VOICE", "en-US-AriaNeural")
AUTO_VOICE_ON_SONG_REQUEST = os.getenv("AUTO_VOICE_ON_SONG_REQUEST", "true").lower() == "true"
COMPANION_ALWAYS_ON = os.getenv("COMPANION_ALWAYS_ON", "true").lower() == "true"
WHISPER_AVAILABLE = True

GEMINI_QUOTA_COOLDOWN_SECONDS = 30
GEMINI_TOTAL_COOLDOWN_SECONDS = 120

SWEET_VOICE_HINTS = (
    "sweet voice", "sweet", "soft voice", "softly", "romantic",
    "sweetly", "gentle", "lovingly", "cute voice", "cutely",
)

BANNED_IDENTITY_PATTERNS = (
    "as an ai", "as a language model", "i am an ai",
    "i am a language model", "i am just an ai",
    "i am a bot", "as a bot", "as an assistant",
    "i don't have personal", "i do not have personal",
    "as an ai assistant", "i'm an ai",
)

_bot_alive = False
_application: Any = None
_loop: Any = None
_last_error: str | None = None

MEMORY_FILE = "user_memories.json"
BASE_DIR = Path(__file__).parent.parent.absolute()

try:
    from gtts import gTTS  # noqa: F401
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import edge_tts  # noqa: F401
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
