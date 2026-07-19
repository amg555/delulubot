from __future__ import annotations

import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from .config import MEMORY_FILE, PERSONAL_FACTS_LIMIT, PERSONAL_FACTS_TOP_K, logger

user_memories: dict[str, Any] = {}


def load_memories() -> dict[str, Any]:
    global user_memories
    if not os.path.exists(MEMORY_FILE):
        user_memories = {}
        return user_memories
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            user_memories = data
        else:
            user_memories = {}
    except Exception as e:
        logger.warning(f"Failed to load memories: {e}")
        user_memories = {}
    return user_memories


def save_memories(memories: dict[str, Any]) -> None:
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save memories: {e}")


def get_user_memory(user_id: str) -> dict[str, Any]:
    if user_id not in user_memories:
        user_memories[user_id] = {
            "name": None,
            "conversation_history": [],
            "total_messages": 0,
            "friendship_level": 1,
            "mood_history": [],
            "user_facts": [],
            "voice_style": "default",
            "voice_enabled": False,
            "tone": "default",
            "lang_style": "manglish",
            "voice_lang": "auto",
            "emoji_level": "default",
        }
    return user_memories[user_id]


def update_memory(user_id: str, user_message: str, bot_reply: str) -> None:
    memory = get_user_memory(user_id)
    memory["conversation_history"].append({"role": "user", "content": user_message})
    memory["conversation_history"].append({"role": "assistant", "content": bot_reply})
    if len(memory["conversation_history"]) > 50:
        memory["conversation_history"] = memory["conversation_history"][-50:]
    memory["total_messages"] = memory.get("total_messages", 0) + 1
    if memory["total_messages"] % 5 == 0:
        memory["friendship_level"] = min(100, memory.get("friendship_level", 1) + 1)
    save_memories(user_memories)


def maybe_extract_user_fact(message: str) -> str | None:
    lower = message.lower().strip()
    patterns = [
        r"(?:i\s+(?:am|'m)\s+|ente\s+peru\s+|enne\s+vilikku\s+|call\s+me\s+)(.{2,30})$",
        r"(?:i\s+(?:like|love|enjoy|hate|dislike)\s+(.{2,50}))",
        r"(?:i\s+(?:work|study|live|stay)\s+(?:at|in|as)\s+(.{2,50}))",
        r"(?:my\s+(?:name|job|work|school|college|place|hometown|dream|goal)\s+(?:is|:)\s+(.{2,50}))",
        r"(?:ente\s+(?:joli|place|school|college|dream|goal)\s+(.{2,50}))",
        r"(?:njan\s+(.{3,60}))",
    ]
    for pat in patterns:
        match = re.search(pat, lower)
        if match and match.group(1):
            fact = match.group(1).strip().rstrip(".,!?")
            if len(fact) > 3:
                return fact
    return None


def add_user_fact(memory: dict[str, Any], fact: str) -> None:
    facts = memory.get("user_facts", [])
    for existing in facts:
        if SequenceMatcher(None, fact.lower(), existing.lower()).ratio() > 0.8:
            return
    facts.append(fact)
    if len(facts) > PERSONAL_FACTS_LIMIT:
        facts.pop(0)
    memory["user_facts"] = facts


def clear_user_history(user_id: str) -> None:
    memory = get_user_memory(user_id)
    memory["conversation_history"] = []
    memory["total_messages"] = 0
    memory["friendship_level"] = 1
    memory["mood_history"] = []
    save_memories(user_memories)


def update_user_vibe(memory: dict[str, Any], message: str) -> None:
    word_count = len(message.split())
    memory["avg_message_length"] = (
        0.7 * memory.get("avg_message_length", word_count) + 0.3 * word_count
    )


def extract_name(message: str, current_name: str | None) -> str | None:
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
                name = remaining.split()[0].strip(".,!?;:")
                if name and len(name) < 30 and not any(c in name for c in "0123456789"):
                    return name
    return None


def strip_unsolicited_past_talk(text: str, user_message: str) -> str:
    lines = text.split("\n")
    kept: list[str] = []
    for line in lines:
        lower = line.lower().strip()
        if any(p in lower for p in ["remember when you said", "earlier you mentioned"]):
            if user_message and user_message.lower() not in lower:
                continue
        kept.append(line)
    return "\n".join(kept)


load_memories()
