from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import google.generativeai as genai
from openai import OpenAI

from .config import (
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MODEL,
    GEMINI_QUOTA_COOLDOWN_SECONDS,
    GEMINI_TOTAL_COOLDOWN_SECONDS,
    GROQ_API_KEY,
    GROQ_MODEL,
    JINA_API_KEYS_RAW,
    JINA_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    _last_error,
    logger,
)
from .prompts import build_system_instruction

groq_client: OpenAI | None = None
jina_clients: list[dict[str, Any]] = []
_jina_key_index = 0

_jina_key_balance_cache: dict[str, bool] = {}
_jina_last_check: float = 0
_JINA_CHECK_INTERVAL = 300.0

gemini_cooldowns: dict[str, float] = {}
gemini_runtime: dict[str, Any] = {
    "active_model": None,
    "last_success_model": None,
}


def _init_groq() -> OpenAI | None:
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — Groq disabled")
        return None
    try:
        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            timeout=60,
        )
        logger.info("Groq client initialized")
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client: {e}")
        return None


def _init_jina_clients() -> list[dict[str, Any]]:
    clients: list[dict[str, Any]] = []
    keys = [k.strip() for k in JINA_API_KEYS_RAW.split(",") if k.strip()]
    for key in keys:
        clients.append({"key": key, "used": False, "failed": False})
    logger.info(f"Jina clients: {len(clients)} keys loaded")
    return clients


def _init_gemini() -> None:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini configured")


groq_client = _init_groq()
jina_clients = _init_jina_clients()
_init_gemini()


def check_gemini_api() -> bool:
    return bool(GEMINI_API_KEY)


def get_model(model_name: str | None = None, system_instruction: str | None = None):
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
        ),
    )


def get_gemini_model_order() -> list[str]:
    order = [
        gemini_runtime.get("active_model") or GEMINI_MODEL,
        GEMINI_MODEL,
        *GEMINI_FALLBACK_MODELS,
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for model in order:
        if not model or model in seen:
            continue
        seen.add(model)
        deduped.append(model)
    return deduped


def parse_retry_delay_seconds(error_text: str) -> int:
    import re
    if not error_text:
        return GEMINI_QUOTA_COOLDOWN_SECONDS
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", error_text, re.IGNORECASE)
    if match:
        return max(1, int(float(match.group(1))))
    match = re.search(r"retry_delay\s*\{\s*seconds:\s*([0-9]+)", error_text, re.IGNORECASE)
    if match:
        return max(1, int(match.group(1)))
    return GEMINI_QUOTA_COOLDOWN_SECONDS


def is_quota_error(error_text: str) -> bool:
    t = (error_text or "").lower()
    return "quota exceeded" in t or "rate limit" in t or "too many requests" in t or "429" in t


def mark_model_cooldown(model_name: str, seconds: int) -> None:
    gemini_cooldowns[model_name] = time.time() + seconds


def get_model_cooldown_left(model_name: str) -> float:
    expiry = gemini_cooldowns.get(model_name, 0)
    remaining = expiry - time.time()
    return max(0, remaining)


def get_next_jina_client() -> dict[str, Any] | None:
    global _jina_key_index
    if not jina_clients:
        return None
    start = _jina_key_index
    for _ in range(len(jina_clients)):
        client = jina_clients[_jina_key_index]
        _jina_key_index = (_jina_key_index + 1) % len(jina_clients)
        if not client.get("failed"):
            return client
        if _jina_key_index == start:
            break
    return None


def _test_apis() -> str:
    now = __import__("datetime").datetime.now()
    results: dict[str, Any] = {"timestamp": now.isoformat(), "checks": {}}
    import requests
    try:
        from .config import TELEGRAM_TOKEN
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe", timeout=10)
        results["checks"]["telegram"] = "OK" if r.json().get("ok") else f"FAIL: {r.text[:100]}"
    except Exception as e:
        results["checks"]["telegram"] = f"FAIL: {type(e).__name__}"
    if groq_client:
        try:
            resp = groq_client.chat.completions.create(model=GROQ_MODEL, messages=[{"role": "user", "content": "say ok"}], max_tokens=10)
            results["checks"]["groq"] = f"OK: {resp.choices[0].message.content}"
        except Exception as e:
            results["checks"]["groq"] = f"FAIL: {str(e)[:150]}"
    else:
        results["checks"]["groq"] = "SKIP: no client"
    if GEMINI_API_KEY:
        try:
            m = genai.GenerativeModel(GEMINI_MODEL)
            r = m.generate_content("say ok")
            results["checks"]["gemini"] = f"OK: {r.text[:50]}"
        except Exception as e:
            results["checks"]["gemini"] = f"FAIL: {str(e)[:150]}"
    else:
        results["checks"]["gemini"] = "SKIP: no key"
    results["checks"]["jina_keys"] = str(len(jina_clients))
    results["checks"]["bot_alive"] = str(True)
    from .config import _last_error as le
    if le:
        results["last_error"] = le
    return json.dumps(results, indent=2)
