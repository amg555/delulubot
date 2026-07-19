from __future__ import annotations

import asyncio
import os
import sys

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import (
    TELEGRAM_TOKEN,
    TIMEOUT_SECONDS,
    VOICE_INPUT_ENABLED,
    VOICE_OUTPUT_ENABLED,
    VOICE_TRANSCRIBE_MODEL,
    VOICE_WHISPER_COMPUTE_TYPE,
    CHARACTER_BIBLE_FILE,
    GTTS_AVAILABLE,
    _bot_alive,
    _application,
    _loop,
    _last_error,
    logger,
)
from .api_clients import groq_client, jina_clients, check_gemini_api
from .handlers import (
    start,
    companion_help,
    remember_fact,
    about_me,
    forget_fact,
    clear_history,
    ask_delulu,
    sing_song,
    random_thought,
    mood_reading,
    friendship_level,
    music_talk,
    voice_mode,
    status_check,
    rag_status,
    rag_search,
    rag_reload,
    tone_command,
    langstyle_command,
    voicelang_command,
    emoji_command,
    settings_command,
    ping_command,
    handle_message,
    handle_voice,
    handle_audio,
    handle_photo,
    error_handler,
)
from .prompts import refresh_character_bible, DELULU_CHARACTER_BIBLE
from .rag import rag_state, reload_rag
from .voice import get_tts_engine
from .webhook_server import start_webhook_server


def run_startup_checks() -> bool:
    print("=" * 50)
    print("DELULU BOT STARTUP")
    print("=" * 50)

    if not TELEGRAM_TOKEN:
        print("FATAL: TELEGRAM_TOKEN not set")
        return False

    print(f"OK: TELEGRAM_TOKEN: {'set' if TELEGRAM_TOKEN else 'Not set'}")
    print(f"OK: GROQ_API_KEY: {'set' if os.getenv('GROQ_API_KEY') else 'Not set'}")
    print(f"OK: GEMINI_API_KEY: {'set' if os.getenv('GEMINI_API_KEY') else 'Not set'}")

    print(f"OK: Groq client: {'Ready' if groq_client else 'Not configured'}")
    print(f"OK: Gemini: {'Ready' if check_gemini_api() else 'Not configured'}")
    print(f"OK: Jina clients: {len(jina_clients)} keys loaded")

    bible_loaded = bool(DELULU_CHARACTER_BIBLE)
    if bible_loaded:
        print(f"OK: Character Bible: Loaded from {CHARACTER_BIBLE_FILE}")
    else:
        print(f"WARN: Character Bible missing: {CHARACTER_BIBLE_FILE}")

    if VOICE_INPUT_ENABLED:
        if groq_client:
            print("OK: Voice input: Ready (Groq Whisper API)")
        else:
            print("WARN: Voice input enabled but Groq client not available")
    else:
        print("INFO: Voice input: Disabled")

    if VOICE_OUTPUT_ENABLED:
        engine = get_tts_engine()
        if engine != "none":
            print(f"OK: Voice output: Ready ({engine}-tts)")
        else:
            print("WARN: Voice output enabled but no TTS engine available")
    else:
        print("INFO: Voice output: Disabled")

    if rag_state.get("chunks", 0) > 0:
        print(f"OK: RAG: {rag_state['chunks']} chunks loaded")
    else:
        print("WARN: RAG: No chunks loaded")

    print("=" * 50)
    return True


def _run_bot_webhook():
    """Start bot in webhook mode."""
    global _bot_alive, _application, _loop

    if not run_startup_checks():
        print("\nStartup checks failed - will retry in 30s")
        import time as _time
        _time.sleep(30)
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    _application = app

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("companion", companion_help))
    app.add_handler(CommandHandler("remember", remember_fact))
    app.add_handler(CommandHandler("aboutme", about_me))
    app.add_handler(CommandHandler("ask", ask_delulu))
    app.add_handler(CommandHandler("mood", mood_reading))
    app.add_handler(CommandHandler("friendship", friendship_level))
    app.add_handler(CommandHandler("music", music_talk))
    app.add_handler(CommandHandler("sing", sing_song))
    app.add_handler(CommandHandler("random", random_thought))
    app.add_handler(CommandHandler("voice", voice_mode))
    app.add_handler(CommandHandler("status", status_check))
    app.add_handler(CommandHandler("ragstatus", rag_status))
    app.add_handler(CommandHandler("ragsearch", rag_search))
    app.add_handler(CommandHandler("ragreload", rag_reload))
    app.add_handler(CommandHandler("forget", forget_fact))
    app.add_handler(CommandHandler("clearhistory", clear_history))
    app.add_handler(CommandHandler("tone", tone_command))
    app.add_handler(CommandHandler("voicelang", voicelang_command))
    app.add_handler(CommandHandler("emoji", emoji_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("langstyle", langstyle_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)

    hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")

    async def run():
        global _loop
        _loop = asyncio.get_event_loop()
        await app.initialize()
        await app.start()

        if hostname:
            wh_url = f"https://{hostname}/{TELEGRAM_TOKEN}"
            try:
                import requests as _req
                r = _req.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                    json={"url": wh_url, "drop_pending_updates": True},
                    timeout=15,
                )
                logger.info(f"Webhook set: {r.json()}")
            except Exception as e:
                logger.warning(f"Webhook setup failed: {e}")

        global _bot_alive
        _bot_alive = True

        print()
        print("Delulu is AUTHENTIC... her human side!")
        print("Companion mode: ACTIVATED")
        print("Webhook mode")
        print("Bot is running...")
        print()

        while True:
            await asyncio.sleep(3600)

    try:
        asyncio.run(run())
    finally:
        _bot_alive = False
        _last_error = None


def main():
    """Start Delulu in webhook mode with auto-restart on crash."""
    import time as _time

    start_webhook_server()

    while True:
        try:
            _run_bot_webhook()
        except BaseException as e:
            global _last_error
            _last_error = f"{type(e).__name__}: {e}"
            logger.error(f"Bot crashed: {_last_error}", exc_info=True)
            logger.info("Restarting in 5 seconds...")
            _time.sleep(5)


if __name__ == "__main__":
    main()
