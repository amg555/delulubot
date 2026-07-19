from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from .api_clients import get_next_jina_client, jina_clients
from .config import (
    RAG_CHUNK_OVERLAP,
    RAG_CHUNK_WORDS,
    RAG_DIR,
    RAG_ENABLED,
    RAG_MAX_SNIPPET_CHARS,
    RAG_MIN_SCORE,
    RAG_TOP_K,
    JINA_MODEL,
    BASE_DIR,
    logger,
)
from .memory import user_memories

rag_chunks: list[dict[str, Any]] = []
rag_idf: dict[str, float] = {}
rag_embeddings: dict[str, list[float]] = {}
rag_state: dict[str, Any] = {
    "enabled": RAG_ENABLED,
    "files": 0,
    "chunks": 0,
    "loaded_at": None,
}

RAG_EMBEDDING_CACHE_FILE = Path("rag_embeddings_cache.json")
_TOKEN_PATTERN = re.compile(r"\w+")


def _get_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_rag_cache() -> dict[str, Any]:
    if not RAG_EMBEDDING_CACHE_FILE.exists():
        return {}
    try:
        with open(RAG_EMBEDDING_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load RAG cache: {e}")
        return {}


def _save_rag_cache(cache: dict[str, Any]) -> None:
    try:
        with open(RAG_EMBEDDING_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save RAG cache: {e}")


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    chunk_size = RAG_CHUNK_WORDS
    overlap = RAG_CHUNK_OVERLAP
    step = max(1, chunk_size - overlap)
    for i in range(0, max(1, len(words)), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _load_rag_documents() -> list[str]:
    if not RAG_ENABLED:
        return []
    rag_path = Path(RAG_DIR)
    if not rag_path.exists() or not rag_path.is_dir():
        logger.warning(f"RAG directory not found: {RAG_DIR}")
        return []
    docs: list[str] = []
    for fpath in sorted(rag_path.rglob("*")):
        if fpath.is_file() and fpath.suffix.lower() in {".txt", ".md", ".json", ".yml", ".yaml"}:
            try:
                docs.append(fpath.read_text(encoding="utf-8"))
            except Exception:
                try:
                    docs.append(fpath.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    pass
    logger.info(f"Loaded {len(docs)} RAG documents")
    return docs


def load_chunks() -> list[dict[str, Any]]:
    global rag_chunks, rag_state, rag_embeddings
    if not RAG_ENABLED:
        rag_state["enabled"] = False
        return []
    docs = _load_rag_documents()
    all_chunks: list[dict[str, Any]] = []
    for doc in docs:
        for chunk_text in _chunk_text(doc):
            if chunk_text.strip():
                all_chunks.append({"text": chunk_text})
    if not all_chunks:
        logger.warning("No RAG chunks loaded — empty document pool")
        rag_state["chunks"] = 0
        rag_chunks = []
        return []

    cache = _load_rag_cache()
    texts = [c["text"] for c in all_chunks]
    new_texts = [t for t in texts if _get_text_hash(t) not in cache]
    if new_texts and jina_clients:
        _compute_embeddings(new_texts, cache)
        _save_rag_cache(cache)

    rag_embeddings = {}
    for c in all_chunks:
        h = _get_text_hash(c["text"])
        if h in cache:
            rag_embeddings[h] = cache[h]

    rag_chunks = all_chunks
    rag_state["files"] = len(docs)
    rag_state["chunks"] = len(all_chunks)
    from datetime import datetime
    rag_state["loaded_at"] = datetime.now().isoformat()
    _build_idf(rag_chunks)
    logger.info(f"RAG ready: {len(rag_chunks)} chunks from {len(docs)} files")
    return rag_chunks


def _compute_embeddings(texts: list[str], cache: dict[str, Any]) -> None:
    from .api_clients import _jina_key_balance_cache, _jina_last_check, _JINA_CHECK_INTERVAL

    for text in texts:
        text_hash = _get_text_hash(text)
        if text_hash in cache:
            continue
        client = get_next_jina_client()
        if not client:
            logger.warning("All Jina API keys exhausted for embedding — skipping")
            break
        try:
            key = client["key"]
            resp = _jina_request(key, text)
            if resp:
                cache[text_hash] = resp
        except Exception as e:
            logger.warning(f"Jina embed error: {e}")
            client["failed"] = True


def _jina_request(api_key: str, text: str) -> list[float] | None:
    import requests

    resp = requests.post(
        "https://api.jina.ai/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"input": [text], "model": JINA_MODEL},
        timeout=15,
    )
    if resp.status_code == 429:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    emb = data.get("data", [{}])[0].get("embedding")
    return emb


def _get_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    results: list[list[float] | None] = []
    cache = _load_rag_cache()
    uncached: list[int] = []
    for i, text in enumerate(texts):
        h = _get_text_hash(text)
        if h in cache:
            results.append(cache[h])
        else:
            results.append(None)
            uncached.append(i)
    if not uncached:
        return results
    client = get_next_jina_client()
    if client:
        try:
            batch_texts = [texts[i] for i in uncached]
            key = client["key"]
            import requests
            resp = requests.post(
                "https://api.jina.ai/v1/embeddings",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"input": batch_texts, "model": JINA_MODEL},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    idx = item.get("index")
                    if idx is not None and idx < len(uncached):
                        actual_i = uncached[idx]
                        emb = item.get("embedding")
                        results[actual_i] = emb
                        h = _get_text_hash(texts[actual_i])
                        cache[h] = emb
                _save_rag_cache(cache)
        except Exception as e:
            logger.warning(f"Jina batch embedding failed: {e}")
    return results


def _build_idf(chunks: list[dict[str, Any]]) -> None:
    n = len(chunks)
    if n == 0:
        rag_idf.clear()
        return
    df: dict[str, int] = {}
    for c in chunks:
        tokens = set(_TOKEN_PATTERN.findall(c["text"].lower()))
        for token in tokens:
            df[token] = df.get(token, 0) + 1
    rag_idf.clear()
    for token, count in df.items():
        rag_idf[token] = max(0.1, (n / max(1, count)) ** 0.5)


def build_rag_context(message: str) -> str:
    if not RAG_ENABLED or not rag_chunks:
        return ""
    if not jina_clients:
        return ""
    results = search_rag(message)
    if not results:
        return ""
    snippets = []
    seen: set[str] = set()
    for r in results:
        text = r["text"][:RAG_MAX_SNIPPET_CHARS]
        if text not in seen:
            seen.add(text)
            snippets.append(text)
            if len(snippets) >= RAG_TOP_K:
                break
    if not snippets:
        return ""
    separator = "\n---\n"
    return separator.join(snippets)


def build_foundation_rag_context() -> str:
    if not rag_chunks:
        return ""
    taken: list[str] = []
    seen: set[str] = set()
    for c in rag_chunks[:RAG_TOP_K]:
        t = c["text"][:RAG_MAX_SNIPPET_CHARS]
        if t not in seen:
            seen.add(t)
            taken.append(t)
    return "\n---\n".join(taken)


def search_rag(query: str) -> list[dict[str, Any]]:
    if not RAG_ENABLED or not rag_chunks:
        return []
    if rag_embeddings and jina_clients:
        return _semantic_search(query)
    return _keyword_search(query)


def _semantic_search(query: str) -> list[dict[str, Any]]:
    if not jina_clients or not rag_embeddings:
        return _keyword_search(query)
    query_vec = _get_embeddings_batch([query])
    if not query_vec or not query_vec[0]:
        return _keyword_search(query)
    import numpy as np
    qv = np.array(query_vec[0])
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in rag_chunks:
        h = _get_text_hash(chunk["text"])
        cv = rag_embeddings.get(h)
        if cv is not None:
            cv_arr = np.array(cv)
            denom = (np.linalg.norm(qv) * np.linalg.norm(cv_arr))
            score = float(np.dot(qv, cv_arr) / denom) if denom > 0 else 0
            if score >= RAG_MIN_SCORE:
                scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, chunk in scored[:RAG_TOP_K]:
        results.append({"text": chunk["text"], "score": round(score, 4)})
    if not results:
        return _keyword_search(query)
    return results


def _keyword_search(query: str) -> list[dict[str, Any]]:
    tokens = _TOKEN_PATTERN.findall(query.lower())
    if not tokens:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in rag_chunks:
        text_lower = chunk["text"].lower()
        score = 0
        for token in tokens:
            if token in text_lower:
                w = rag_idf.get(token, 1)
                score += w * text_lower.count(token)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"text": c["text"], "score": round(s, 2)} for s, c in scored[:RAG_TOP_K]]


def reload_rag() -> list[dict[str, Any]]:
    return load_chunks()
