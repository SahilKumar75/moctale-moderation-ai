"""Caching layer for Moctale Moderation AI."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis

log = logging.getLogger(__name__)


class ModerationCache:
    """Redis-backed cache with graceful degradation.
    
    If Redis is unavailable, it degrades to a no-op cache safely.
    """

    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 3600) -> None:
        self.ttl = ttl_seconds
        self.redis: redis.Redis | None = None
        if redis_url:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                # Ping to check connection
                self.redis.ping()
                log.info("Redis cache initialized.", extra={"redis_url": redis_url})
            except Exception as e:
                log.warning("Failed to connect to Redis. Caching disabled.", extra={"error": str(e)})
                self.redis = None
        else:
            log.info("No Redis URL provided. Caching disabled.")

    def _hash_key(self, text: str, context_type: str) -> str:
        """Generate a deterministic cache key."""
        payload = f"{text}:{context_type}".encode()
        return f"moctale:cache:{hashlib.sha256(payload).hexdigest()}"

    def get(self, text: str, context_type: str) -> dict[str, Any] | None:
        """Retrieve a cached moderation result."""
        if not self.redis:
            return None
        key = self._hash_key(text, context_type)
        try:
            val = self.redis.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            log.warning("Redis GET failed", extra={"error": str(e)})
        return None

    def set(self, text: str, context_type: str, result_dict: dict[str, Any]) -> None:
        """Store a moderation result in cache."""
        if not self.redis:
            return
        key = self._hash_key(text, context_type)
        try:
            self.redis.setex(key, self.ttl, json.dumps(result_dict))
        except Exception as e:
            log.warning("Redis SET failed", extra={"error": str(e)})
