from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import shutil
import tempfile
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes, filters

from .api_clients import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODELS,
    GROQ_MODEL,
    check_gemini_api,
    gemini_runtime,
    get_gemini_model_order,
    get_model,
    get_model_cooldown_left,
    groq_client,
    is_quota_error,
    mark_model_cooldown,
    parse_retry_delay_seconds,
)
from .config import (
    AUTO_VOICE_ON_SONG_REQUEST,
    CHARACTER_GUARD_ENABLED,
    CHARACTER_GUARD_RETRIES,
    COMPANION_ALWAYS_ON,
    GTTS_AVAILABLE,
    MAX_TOKENS,
    SWEET_VOICE_HINTS,
    TEMPERATURE,
    TIMEOUT_SECONDS,
    VOICE_INPUT_ENABLED,
    VOICE_MAX_DURATION_SECONDS,
    VOICE_OUTPUT_ENABLED,
    VOICE_REPLY_WITH_TEXT,
    logger,
)
from .context import (
    build_emotion_context,
    build_foundation_rag_context,
    build_friendship_context,
    build_personal_context,
    build_rag_context,
    build_vibe_context,
    detect_emotion,
    extract_name,
)
from .memory import (
    add_user_fact,
    clear_user_history,
    get_user_memory,
    maybe_extract_user_fact,
    save_memories,
    update_memory,
    update_user_vibe,
    user_memories,
    strip_unsolicited_past_talk,
)
from .prompts import (
    DELULU_DIALOGUES,
    LANG_STYLES,
    RANDOM_DELULU_THOUGHTS,
    TONE_STYLES,
    build_system_instruction,
    is_song_request,
    LANG_VOICE_MAP,
    refresh_character_bible,
)
from .rag import rag_chunks, rag_state, reload_rag
from .voice import (
    detect_text_language,
    get_tts_engine,
    pick_tts_voice,
    resolve_voice_lang,
    synthesize_tts_mp3,
    transcribe_voice_with_retry,
)

logger = logging.getLogger("delulu.handlers")

BANNED_IDENTITY_PATTERNS = (
    "as an ai", "as a language model", "i am an ai",
    "i am a language model", "i am just an ai",
    "i am a bot", "as a bot", "as an assistant",
    "i don't have personal", "i do not have personal",
    "as an ai assistant", "i'm an ai",
)


def de_robotify_reply(reply: str, user_message: str) -> str:
    text = (reply or "").strip()
    if not text:
        return text
    if is_structured_user_request(user_message):
        return text
    text = re.sub(r"^(sure|certainly|of course|absolutely|definitely)[,!.:\-\s]*", "", text, flags=re.IGNORECASE)
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


def is_structured_user_request(message: str) -> bool:
    lower = message.lower().strip()
    return any(h in lower for h in ("list", "steps", "tutorial", "guide me", "how to", "format", "bullet"))


def character_alignment_issues(reply: str, user_name: str, user_message: str) -> list[str]:
    text = (reply or "").strip()
    lower = text.lower()
    issues: list[str] = []
    if not text:
        issues.append("empty response")
    if any(p in lower for p in BANNED_IDENTITY_PATTERNS):
        issues.append("identity leak (mentions AI/chatbot style identity)")
    words = text.split()
    if len(words) > 120:
        issues.append("too long for chat style")
    has_manglish = any(p in lower for p in ("eda", "ente", "entha", "sheri", "pinn", "ippo", "aano", "ille", "undu", "venda", "poda"))
    is_emotional = user_message and any(w in user_message.lower() for w in ("sad", "cry", "miss", "love", "angry", "scared"))
    if not has_manglish and not is_emotional and not is_structured_user_request(user_message):
        issues.append("missing Manglish flavor")
    return issues


async def generate_delulu_reply_with_guard(
    model: Any,
    contents: list[dict[str, Any]],
    user_name: str,
    user_message: str,
) -> str:
    attempts = max(0, CHARACTER_GUARD_RETRIES) + 1 if CHARACTER_GUARD_ENABLED else 1
    last_reply = ""
    working_contents = list(contents)
    for attempt in range(attempts):
        response = await model.generate_content_async(contents=working_contents)
        reply = (getattr(response, "text", "") or "").strip()
        if "[CONTEXT:" in reply:
            reply = reply.split("]", 1)[-1].strip()
        last_reply = reply
        issues = character_alignment_issues(reply, user_name=user_name, user_message=user_message)
        if not issues:
            return reply
        if attempt == attempts - 1:
            return reply
        fix_prompt = (
            "Rewrite that in DELULU voice — natural, short, human.\n"
            f"Fix: {', '.join(issues)}.\n"
            "No AI talk. No headings. Just reply like a friend.\n"
            "Return only the corrected reply."
        )
        working_contents.append({"role": "model", "parts": [reply]})
        working_contents.append({"role": "user", "parts": [fix_prompt]})
    return last_reply


async def _groq_generate_with_guard(
    system_instruction: str,
    messages_openai: list[dict[str, str]],
    user_name: str,
    user_message: str,
) -> str:
    working = [{"role": "system", "content": system_instruction}, *messages_openai]
    attempts = max(0, CHARACTER_GUARD_RETRIES) + 1 if CHARACTER_GUARD_ENABLED else 1
    last_reply = ""
    for attempt in range(attempts):
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
        last_reply = reply
        issues = character_alignment_issues(reply, user_name=user_name, user_message=user_message)
        if not issues:
            return reply
        if attempt == attempts - 1:
            return reply
        fix_prompt = (
            "Rewrite that in DELULU voice — natural, short, human.\n"
            f"Fix: {', '.join(issues)}.\n"
            "No AI talk. No headings. Just reply like a friend.\n"
            "Return only the corrected reply."
        )
        working.append({"role": "assistant", "content": reply})
        working.append({"role": "user", "content": fix_prompt})
    return last_reply


async def get_delulu_response(user_id: str, user_message: str) -> str:
    memory = get_user_memory(user_id)
    emotion = detect_emotion(user_message)
    level = memory["friendship_level"]
    memory["mood_history"].append({"emotion": emotion, "time": datetime.now().isoformat()})
    if len(memory["mood_history"]) > 50:
        memory["mood_history"] = memory["mood_history"][-50:]
    new_name = extract_name(user_message, memory.get("name"))
    if new_name:
        memory["name"] = new_name
    maybe_fact = maybe_extract_user_fact(user_message)
    if maybe_fact:
        add_user_fact(memory, maybe_fact)
    update_user_vibe(memory, user_message)
    emotion_ctx = build_emotion_context(emotion)
    friendship_ctx = build_friendship_context(level)
    user_name = memory.get("name", "eda/edi")
    personal_context = build_personal_context(memory, user_message)
    vibe_context = build_vibe_context(memory)
    song_request = is_song_request(user_message)
    rag_context = build_rag_context(user_message)
    if not rag_context:
        rag_context = build_foundation_rag_context()
    rag_instruction = "No RAG context found for this message."
    if rag_context:
        rag_instruction = "You have KNOWLEDGE SNIPPETS below. Use them only if relevant. Do not invent facts that are not in snippets."
    companion_instruction = "Just talk like a friend. Be natural — don't force anything."
    if COMPANION_ALWAYS_ON:
        companion_instruction += " Prioritize emotional connection over advice."
    song_instruction = ""
    if song_request:
        song_instruction = (
            "User asked you to sing. Provide 2-4 short ORIGINAL singable lines "
            "with light humming vibe (la/laa/hmm if needed), plus one sweet line. "
            "Do NOT provide exact copyrighted lyrics from existing songs."
        )
    staleness_instruction = ""
    recent_bot_msgs = [m["content"] for m in memory["conversation_history"] if m["role"] == "assistant"][-3:]
    if len(recent_bot_msgs) >= 2:
        similarities = [SequenceMatcher(None, recent_bot_msgs[i].lower(), recent_bot_msgs[i + 1].lower()).ratio() for i in range(len(recent_bot_msgs) - 1)]
        if any(s > 0.65 for s in similarities):
            staleness_instruction = "Your last replies were a bit repetitive. Say something different this time."
    user_tone = memory.get("tone", "default")
    tone_instruction = TONE_STYLES.get(user_tone, TONE_STYLES["default"])
    emoji_level = memory.get("emoji_level", "default")
    if emoji_level == "none":
        emoji_instruction = "No emojis."
    elif emoji_level == "high":
        emoji_instruction = "You can use emojis freely if it fits."
    else:
        emoji_instruction = "Use emojis naturally, don't force them."
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
        f"\nTone: {tone_instruction}\n"
        f"Emojis: {emoji_instruction}\n"
        f"Language style: {LANG_STYLES.get(user_lang_style, LANG_STYLES['manglish'])}\n"
        "Vary your response length naturally — sometimes one word, sometimes a few sentences. "
        "React emotionally first. "
        "Don't bring up past memories unless user asks. "
        "No assistant tone. No headings/labels.\n\n"
    )
    if personal_context:
        dynamic_instruction += f"Known user facts:\n{personal_context}\n\n"
    if vibe_context:
        dynamic_instruction += f"User vibe profile:\n{vibe_context}\n\n"
    if rag_context:
        dynamic_instruction += f"Relevant reference snippets:\n{rag_context}\n\n"

    openai_messages = []
    recent = memory["conversation_history"][-12:]
    for msg in recent:
        openai_messages.append({"role": msg["role"], "content": msg["content"]})
    openai_messages.append({"role": "user", "content": user_message})

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

    if GEMINI_API_KEY:
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

    error_responses = [
        "Ayyooo... ente ghost powers glitch aayi 👻⚡ Try again cheyy!",
        "Eda... njan invisible aayi poyi 👻 Once more try cheyy!",
        "Phone possession temporarily failed 😂👻 Try again!",
        "Ente signal poyi... ghost network issues 📶👻 Veeendum try cheyy!",
    ]
    return random.choice(error_responses)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    user = update.effective_user
    user_id = str(user.id)
    user_message = update.message.text if update.message else ""
    if not user_message:
        return

    chat_id = update.effective_chat.id
    memory = get_user_memory(user_id)
    voice_enabled = memory.get("voice_enabled", False)

    if user.first_name:
        memory["name"] = user.first_name

    response = await get_delulu_response(user_id, user_message)

    if VOICE_OUTPUT_ENABLED and voice_enabled and get_tts_engine() != "none":
        temp_dir = Path(tempfile.mkdtemp(prefix="delulu_"))
        out_path = temp_dir / "reply.mp3"
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
            voice_style = pick_tts_voice(memory, user_message)
            voice_lang = resolve_voice_lang(memory, response, user_message)
            await synthesize_tts_mp3(
                response, str(out_path), voice_style=voice_style, lang=voice_lang,
            )
            if out_path.stat().st_size > 0:
                with open(out_path, "rb") as vf:
                    await update.message.reply_voice(voice=vf)
            if VOICE_REPLY_WITH_TEXT:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Voice reply error: {e}")
            await update.message.reply_text(response)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        await update.message.reply_text(response)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages with STT."""
    if not VOICE_INPUT_ENABLED:
        await update.message.reply_text("Voice input is off. Send text or enable it in `.env`.")
        return
    if not update.message or not update.message.voice:
        return
    voice = update.message.voice
    if voice.duration and voice.duration > VOICE_MAX_DURATION_SECONDS:
        await update.message.reply_text(f"Voice too long. Keep it under {VOICE_MAX_DURATION_SECONDS} seconds.")
        return
    if not groq_client:
        await update.message.reply_text("Voice transcription API unavailable.")
        return

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    temp_dir = Path(tempfile.mkdtemp(prefix="delulu_voice_"))
    in_path = temp_dir / "input.ogg"
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        tg_file = await context.bot.get_file(voice.file_id)
        await tg_file.download_to_drive(custom_path=str(in_path))
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        transcript = await transcribe_voice_with_retry(str(in_path))
        transcript = (transcript or "").strip()
        if not transcript:
            await update.message.reply_text("Couldn't catch that clearly. Try again?")
            return
        logger.info(f"Voice transcribed: {transcript[:50]}...")
        response = await get_delulu_response(user_id, transcript)
        voice_style = pick_tts_voice(memory, transcript)
        voice_lang = resolve_voice_lang(memory, response, transcript)

        if VOICE_OUTPUT_ENABLED and get_tts_engine() != "none":
            out_path = temp_dir / "reply.mp3"
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
                await synthesize_tts_mp3(
                    response, str(out_path), voice_style=voice_style, lang=voice_lang,
                )
                if out_path.stat().st_size > 0:
                    with open(out_path, "rb") as vf:
                        await update.message.reply_voice(voice=vf)
                if VOICE_REPLY_WITH_TEXT:
                    await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Voice TTS reply error: {e}")
                await update.message.reply_text(response)
        else:
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Voice handling error: {e}")
        await update.message.reply_text("Voice processing glitch aayi. Type cheyy or try voice again.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio file messages."""
    if not VOICE_INPUT_ENABLED:
        await update.message.reply_text("Voice input is off.")
        return
    if not update.message or not update.message.audio:
        return
    audio = update.message.audio
    if audio.duration and audio.duration > VOICE_MAX_DURATION_SECONDS:
        await update.message.reply_text(f"Audio too long. Keep it under {VOICE_MAX_DURATION_SECONDS} seconds.")
        return
    if not groq_client:
        await update.message.reply_text("Audio transcription API unavailable.")
        return

    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    memory = get_user_memory(user_id)
    ext = ".ogg"
    if audio.mime_type:
        mime_ext = {
            "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/ogg": ".ogg",
            "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/flac": ".flac",
        }
        ext = mime_ext.get(audio.mime_type, ext)
    temp_dir = Path(tempfile.mkdtemp(prefix="delulu_audio_"))
    in_path = temp_dir / f"input{ext}"
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
        tg_file = await context.bot.get_file(audio.file_id)
        await tg_file.download_to_drive(custom_path=str(in_path))
        transcript = await transcribe_voice_with_retry(str(in_path))
        transcript = (transcript or "").strip()
        if not transcript:
            await update.message.reply_text("Couldn't catch that audio clearly. Try again?")
            return
        response = await get_delulu_response(user_id, transcript)
        voice_style = pick_tts_voice(memory, transcript)
        voice_lang = resolve_voice_lang(memory, response, transcript)
        if VOICE_OUTPUT_ENABLED and get_tts_engine() != "none":
            out_path = temp_dir / "reply.mp3"
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action="upload_voice")
                await synthesize_tts_mp3(response, str(out_path), voice_style=voice_style, lang=voice_lang)
                with open(out_path, "rb") as vf:
                    await update.message.reply_voice(voice=vf)
                if VOICE_REPLY_WITH_TEXT:
                    await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Audio TTS reply error: {e}")
                await update.message.reply_text(response)
        else:
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Audio handling error: {e}")
        await update.message.reply_text("Audio processing glitch aayi. Try again.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Ooh, photo! ✨ Enikku kaanaan pattilla (I can't see it), "
        "but I'm sure it's awesome. Parayu entha uddeshichath?"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def companion_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hey! I'm Delulu. Your phone-side companion.\n"
        "Talk to me casually in Manglish (Malayalam + English).\n"
        "I can match your vibe, crack jokes, comfort you, or just listen.\n"
        "Use /settings to customize me.\n"
        "Or just start talking — I'll adapt."
    )


async def remember_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    text = update.message.text[len("/remember"):].strip() if update.message else ""
    if not text:
        await update.message.reply_text("Tell me what to remember: /remember <fact>")
        return
    add_user_fact(memory, text)
    save_memories(user_memories)
    await update.message.reply_text(f"Sheri! Njan orkunnu ✅")


async def about_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    facts = memory.get("user_facts", [])
    name = memory.get("name") or "Not set yet"
    level = memory.get("friendship_level", 1)
    total = memory.get("total_messages", 0)
    if not facts:
        await update.message.reply_text(f"I know you as *{name}*. We've exchanged {total} messages. Tell me more about yourself with /remember.", parse_mode="Markdown")
        return
    facts_text = "\n".join(f"- {f}" for f in facts[-10:])
    await update.message.reply_text(
        f"*Things I know about you:*\nName: {name}\nFriendship: Level {level}\nMessages: {total}\n\n{facts_text}",
        parse_mode="Markdown",
    )


async def forget_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    memory["user_facts"] = []
    save_memories(user_memories)
    await update.message.reply_text("Forgot everything about you ✅ Fresh start.")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    clear_user_history(user_id)
    await update.message.reply_text("Conversation history cleared ✅ Fresh start.")


async def ask_delulu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text[len("/ask"):].strip() if update.message else ""
    if not text:
        await update.message.reply_text("Ask me something: /ask <your question>")
        return
    response = await get_delulu_response(user_id, f"[advice] {text}")
    await update.message.reply_text(response)


async def sing_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    response = await get_delulu_response(user_id, "paattu paadu")
    await update.message.reply_text(response)


async def random_thought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(random.choice(RANDOM_DELULU_THOUGHTS))


async def mood_reading(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    moods = memory.get("mood_history", [])
    if not moods:
        await update.message.reply_text("Not enough data for mood reading yet. Talk to me more!")
        return
    recent = moods[-5:]
    mood_summary = "\n".join(
        f"- {m['emotion']}" for m in recent
    )
    await update.message.reply_text(f"Your recent moods:\n{mood_summary}")


async def friendship_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    level = memory.get("friendship_level", 1)
    total = memory.get("total_messages", 0)
    await update.message.reply_text(f"Friendship Level: {level}/100 | Messages exchanged: {total}")


async def music_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text[len("/music"):].strip() if update.message else ""
    if text:
        response = await get_delulu_response(user_id, f"[music] {text}")
    else:
        response = await get_delulu_response(user_id, "[music] Talk about music")
    await update.message.reply_text(response)


async def voice_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    current = memory.get("voice_enabled", False)
    memory["voice_enabled"] = not current
    save_memories(user_memories)
    status = "ON ✅" if memory["voice_enabled"] else "OFF ❌"
    await update.message.reply_text(f"Voice reply mode: {status}")


async def status_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from .api_clients import groq_client, jina_clients, check_gemini_api
    from .rag import rag_state

    lines = [
        "*Delulu Status*",
        f"- Groq: {'OK' if groq_client else 'Not configured'}",
        f"- Gemini: {'OK' if check_gemini_api() else 'Not configured'}",
        f"- Jina keys: {len(jina_clients)}",
        f"- RAG: {'Enabled' if rag_state.get('enabled') else 'Disabled'} ({rag_state.get('chunks', 0)} chunks)",
        f"- Voice input: {VOICE_INPUT_ENABLED}",
        f"- Voice output: {VOICE_OUTPUT_ENABLED} (TTS: {get_tts_engine()})",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def rag_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from .rag import rag_state
    await update.message.reply_text(
        f"RAG: {'Enabled' if rag_state.get('enabled') else 'Disabled'}\n"
        f"Files: {rag_state.get('files', 0)}\n"
        f"Chunks: {rag_state.get('chunks', 0)}\n"
        f"Loaded: {rag_state.get('loaded_at', 'Never')}"
    )


async def rag_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text[len("/ragsearch"):].strip() if update.message else ""
    if not text:
        await update.message.reply_text("Usage: /ragsearch <query>")
        return
    from .rag import search_rag
    results = search_rag(text)
    if not results:
        await update.message.reply_text("No results found.")
        return
    msg = "\n\n".join(f"[Score: {r['score']}]\n{r['text'][:300]}" for r in results[:3])
    await update.message.reply_text(msg[:4000] if len(msg) > 4000 else msg)


async def rag_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reload_rag()
    await update.message.reply_text("RAG reloaded ✅")


async def tone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    text = update.message.text[len("/tone"):].strip() if update.message else ""
    if not text:
        await update.message.reply_text(
            "Set my tone: /tone <style>\n"
            "Styles: default, sweet, romantic, funny, serious, stoic, chill"
        )
        return
    arg = text.lower()
    if arg not in TONE_STYLES:
        await update.message.reply_text(f"Unknown tone. Options: {', '.join(TONE_STYLES)}")
        return
    memory["tone"] = arg
    save_memories(user_memories)
    await update.message.reply_text(f"Tone set to {arg} ✅")


async def langstyle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    text = update.message.text[len("/langstyle"):].strip() if update.message else ""
    if not text:
        await update.message.reply_text(
            "Set language style: /langstyle <style>\n"
            + "\n".join(f"/langstyle {s}" for s in LANG_STYLES)
        )
        return
    arg = text.lower()
    if arg not in LANG_STYLES:
        await update.message.reply_text(f"Unknown style. Try: " + ", ".join(f"/langstyle {s}" for s in LANG_STYLES))
        return
    memory["lang_style"] = arg
    save_memories(user_memories)
    await update.message.reply_text(f"Language style set to {arg} ✅")


async def voicelang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    text = update.message.text[len("/voicelang"):].strip() if update.message else ""
    if not text:
        lang_list = "\n".join(f"{k}: {v['name']}" for k, v in LANG_VOICE_MAP.items())
        await update.message.reply_text(
            f"Set voice language: /voicelang <code>\n"
            f"Codes:\n{lang_list}\nUse /voicelang auto for automatic detection."
        )
        return
    arg = text.lower()
    if arg not in LANG_VOICE_MAP and arg != "auto":
        await update.message.reply_text(f"Unknown code. Options: auto, {', '.join(LANG_VOICE_MAP)}")
        return
    memory["voice_lang"] = arg
    save_memories(user_memories)
    lang_name = LANG_VOICE_MAP[arg]["name"] if arg in LANG_VOICE_MAP else "Auto"
    await update.message.reply_text(f"Voice language set to {lang_name} ✅")


async def emoji_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    text = update.message.text[len("/emoji"):].strip() if update.message else ""
    if not text:
        await update.message.reply_text("Set emoji level: /emoji <level>\nLevels: default, none, high")
        return
    arg = text.lower()
    if arg not in ("default", "none", "high"):
        await update.message.reply_text("Options: default, none, high")
        return
    memory["emoji_level"] = arg
    save_memories(user_memories)
    await update.message.reply_text(f"Emoji level set to {arg} ✅")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    memory = get_user_memory(user_id)
    voice_lang = memory.get("voice_lang", "auto")
    lang_name = LANG_VOICE_MAP[voice_lang]["name"] if voice_lang in LANG_VOICE_MAP else "Auto"
    await update.message.reply_text(
        f"*Your Settings:*\n"
        f"Tone: {memory.get('tone', 'default')}\n"
        f"Lang style: {memory.get('lang_style', 'manglish')}\n"
        f"Voice lang: {lang_name}\n"
        f"Emoji level: {memory.get('emoji_level', 'default')}\n"
        f"Voice replies: {'ON' if memory.get('voice_enabled') else 'OFF'}",
        parse_mode="Markdown",
    )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong")
