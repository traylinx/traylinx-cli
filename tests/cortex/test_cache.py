"""Tests for performance modules."""

import pytest
import time
from traylinx.cortex.intent.cache import IntentCache, get_intent_cache
from traylinx.cortex.types import Intent, IntentType


class TestIntentCache:
    """Tests for intent caching."""

    @pytest.fixture
    def cache(self):
        return IntentCache(max_size=10, ttl_seconds=1.0)

    def test_set_and_get(self, cache):
        """Can set and retrieve cached intent."""
        intent = Intent(type=IntentType.CLI_COMMAND, command="run", confidence=0.9)
        cache.set("start my agent", intent)

        result = cache.get("start my agent")
        assert result is not None
        assert result.command == "run"

    def test_normalization(self, cache):
        """Similar inputs should hit same cache entry."""
        intent = Intent(type=IntentType.CLI_COMMAND, command="run", confidence=0.9)
        cache.set("Start My Agent", intent)

        # Different case should hit
        result = cache.get("start my agent")
        assert result is not None

    def test_ttl_expiration(self, cache):
        """Cache entries expire after TTL."""
        intent = Intent(type=IntentType.CLI_COMMAND, command="run", confidence=0.9)
        cache.set("test", intent)

        # Wait for TTL
        time.sleep(1.1)

        result = cache.get("test")
        assert result is None

    def test_lru_eviction(self):
        """Oldest entry evicted when full."""
        cache = IntentCache(max_size=3, ttl_seconds=60.0)
        
        for i in range(4):
            intent = Intent(type=IntentType.CLI_COMMAND, command=f"cmd{i}", confidence=0.9)
            cache.set(f"input{i}", intent)

        # First entry should be evicted
        assert cache.get("input0") is None
        # Latest entries should exist
        assert cache.get("input3") is not None

    def test_stats(self, cache):
        """Stats track hits and misses."""
        intent = Intent(type=IntentType.CLI_COMMAND, command="run", confidence=0.9)
        cache.set("test", intent)

        cache.get("test")  # hit
        cache.get("missing")  # miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_clear(self, cache):
        """Clear removes all entries."""
        intent = Intent(type=IntentType.CLI_COMMAND, command="run", confidence=0.9)
        cache.set("test", intent)
        cache.clear()

        assert cache.get("test") is None
        assert cache.stats()["size"] == 0


class TestGlobalCache:
    """Tests for global cache singleton."""

    def test_singleton(self):
        """get_intent_cache returns same instance."""
        cache1 = get_intent_cache()
        cache2 = get_intent_cache()
        assert cache1 is cache2
