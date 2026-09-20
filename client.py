"""OpenRouter Decisions API client with bounded in-process caching."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from .config import API_URL, CACHE_TTL_SECONDS, MAX_CACHE_ENTRIES, MODEL, TIMEOUT_SECONDS

NEGATIVE_CACHE_TTL_SECONDS = 5.0


class NegativeCacheError(RuntimeError):
    """A recent provider failure is being suppressed to avoid a retry storm."""


class DecisionClient:
    """Small, injectable client for Jev decisions."""

    def __init__(self, post: Callable[..., Any] = httpx.post) -> None:
        self._post = post
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._negative_cache: dict[str, float] = {}
        self._lock = threading.Lock()

    def decide(self, cache_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]
            negative_until = self._negative_cache.get(cache_key, 0.0)
            if negative_until > now:
                raise NegativeCacheError("Jev provider failure is temporarily cached")
        try:
            response = self._post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                    "HTTP-Referer": "https://hermes-agent.nousresearch.com",
                    "X-OpenRouter-Title": "Hermes Jev Gate",
                },
                json={"model": MODEL, **payload},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("answers"), dict):
                raise ValueError("Jev response did not contain an answers object")
            answers = body["answers"]
        except Exception:
            with self._lock:
                self._negative_cache[cache_key] = time.monotonic() + NEGATIVE_CACHE_TTL_SECONDS
            raise
        with self._lock:
            self._negative_cache.pop(cache_key, None)
            if len(self._cache) >= MAX_CACHE_ENTRIES:
                oldest = min(self._cache, key=lambda key: self._cache[key][0])
                self._cache.pop(oldest, None)
            self._cache[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, answers)
        return answers


CLIENT = DecisionClient()


def reset_cache() -> None:
    with CLIENT._lock:
        CLIENT._cache.clear()
        CLIENT._negative_cache.clear()


__all__ = ["CLIENT", "DecisionClient", "NegativeCacheError", "reset_cache"]
