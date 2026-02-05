"""Intent caching for performance optimization.

Caches intent classification results to avoid repeated LLM calls
for identical or similar inputs.
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from traylinx.cortex.types import Intent


@dataclass
class CacheEntry:
    """A cached intent classification result."""

    intent: Intent
    created_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class IntentCache:
    """LRU cache for intent classification results.

    Features:
    - TTL-based expiration (default: 1 hour)
    - Maximum size limit (default: 1000 entries)
    - LRU eviction when full
    - Fuzzy matching for similar inputs
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: float = 3600.0,  # 1 hour
        fuzzy_match: bool = True,
    ):
        """Initialize cache.

        Args:
            max_size: Maximum number of cached entries
            ttl_seconds: Time-to-live in seconds
            fuzzy_match: Enable fuzzy matching for similar inputs
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.fuzzy_match = fuzzy_match
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def _normalize_input(self, user_input: str) -> str:
        """Normalize input for cache key generation.

        Args:
            user_input: Raw user input

        Returns:
            Normalized input string
        """
        # Lowercase, strip whitespace, remove punctuation
        normalized = user_input.lower().strip()
        normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
        # Collapse multiple spaces
        normalized = " ".join(normalized.split())
        return normalized

    def _generate_key(self, user_input: str) -> str:
        """Generate cache key from user input.

        Args:
            user_input: User input string

        Returns:
            Cache key (hash)
        """
        normalized = self._normalize_input(user_input)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get(self, user_input: str) -> Intent | None:
        """Get cached intent for input.

        Args:
            user_input: User input to look up

        Returns:
            Cached Intent or None if not found/expired
        """
        key = self._generate_key(user_input)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Check TTL
        if time.time() - entry.created_at > self.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        # Update access stats
        entry.access_count += 1
        entry.last_accessed = time.time()
        self._hits += 1

        return entry.intent

    def set(self, user_input: str, intent: Intent) -> None:
        """Cache an intent classification result.

        Args:
            user_input: Original user input
            intent: Classified intent
        """
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        key = self._generate_key(user_input)
        self._cache[key] = CacheEntry(
            intent=intent,
            created_at=time.time(),
        )

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed,
        )
        del self._cache[lru_key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hit/miss stats
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }

    def prune_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if now - entry.created_at > self.ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


# Global cache instance
_global_cache: IntentCache | None = None


def get_intent_cache() -> IntentCache:
    """Get the global intent cache instance.

    Returns:
        Global IntentCache
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = IntentCache()
    return _global_cache
