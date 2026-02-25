"""
Redis Scan Cache
----------------
Caches SecurityScanResult objects so identical (or near-identical) prompts
skip the expensive ONNX inference pipeline entirely.

Design goals
------------
✅ Zero impact on correctness   — Redis down = fall through to real scan
✅ Zero changes to callers      — ConcurrentSecurityScanner.scan_prompt()
                                  is the only integration point
✅ Collision-resistant keys     — SHA-256 of normalised prompt text
✅ Configurable TTL             — default 1 h, override via REDIS_CACHE_TTL_SECONDS
✅ Hit/miss metrics logged      — grep for "[cache]" to monitor effectiveness

Environment variables (all optional — Redis is disabled if REDIS_URL is unset)
-------------------------------------------------------------------------------
REDIS_URL               redis://localhost:6379   Full Redis connection URL
REDIS_CACHE_TTL_SECONDS 3600                     How long a cached result lives
REDIS_CACHE_PREFIX      guardrail:scan:          Namespace for all cache keys

Integration
-----------
In security_scanner.py, inside scan_prompt() / scan_prompt_parallel():

    from redis_cache import get_cached_result, cache_result

    # Before scanning
    cached = await get_cached_result(prompt)
    if cached:
        return cached

    # ... run full scan ...

    # After scanning
    await cache_result(prompt, scan_result)
    return scan_result
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read once at import time)
# ---------------------------------------------------------------------------
REDIS_URL         = os.getenv("REDIS_URL", "")                      # e.g. redis://localhost:6379
CACHE_TTL         = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "3600"))  # 1 hour default
CACHE_PREFIX      = os.getenv("REDIS_CACHE_PREFIX", "guardrail:scan:")

# ---------------------------------------------------------------------------
# Lazy Redis client (created on first use, None if Redis unavailable)
# ---------------------------------------------------------------------------
_redis_client = None
_redis_checked = False   # Only attempt connection once


def _get_client():
    """
    Return a connected redis.asyncio client, or None if Redis is unavailable.
    Connection is attempted once; subsequent calls return the cached client.
    """
    global _redis_client, _redis_checked

    if _redis_checked:
        return _redis_client

    _redis_checked = True

    if not REDIS_URL:
        logger.info("[cache] REDIS_URL not set — scan caching disabled")
        return None

    try:
        import redis.asyncio as aioredis  # redis>=4.2.0
        _redis_client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,   # all values come back as str
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        logger.info(f"[cache] Redis client created → {REDIS_URL}")
    except ImportError:
        logger.warning(
            "[cache] 'redis' package not installed. "
            "Run: pip install redis  — scan caching disabled."
        )
    except Exception as exc:
        logger.warning(f"[cache] Could not create Redis client: {exc}")

    return _redis_client


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------
_WHITESPACE_RE = re.compile(r"\s+")


def _make_cache_key(prompt: str) -> str:
    """
    Build a deterministic, collision-resistant cache key from a prompt.

    Normalisation steps (order matters):
      1. Strip leading/trailing whitespace
      2. Collapse all interior whitespace runs to a single space
      3. Lower-case  (so "Hello" and "hello" share one cache entry)
      4. SHA-256     (fixed-length, safe for Redis key-length limits)

    The prefix keeps guardrail keys separate from any other Redis data.
    """
    normalised = _WHITESPACE_RE.sub(" ", prompt.strip()).lower()
    digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return f"{CACHE_PREFIX}{digest}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_cached_result(prompt: str):
    """
    Look up a previously cached scan result for *prompt*.

    Returns
    -------
    SecurityScanResult  if a valid cache entry exists
    None                if cache miss, Redis down, or any error
    """
    client = _get_client()
    if client is None:
        return None

    key = _make_cache_key(prompt)

    try:
        raw = await client.get(key)
        if raw is None:
            logger.debug(f"[cache] MISS  key={key[-12:]}")
            return None

        import time
        t0 = time.time()
        data = json.loads(raw)

        # Import here to avoid circular imports at module load time
        from models import SecurityScanResult

        # Stamp actual cache retrieval time so the dashboard shows
        # real latency (~5ms) instead of the original scan duration.
        retrieval_time = round(time.time() - t0, 4)
        data["scan_duration"] = retrieval_time
        data["from_cache"]    = True   # useful for debugging / metrics

        result = SecurityScanResult(**data)

        logger.info(
            f"[cache] HIT ✅  key=…{key[-12:]}  "
            f"risk={result.risk_level}  safe={result.is_safe}  "
            f"retrieval={retrieval_time*1000:.1f}ms"
        )
        return result

    except Exception as exc:
        # Never let a cache failure block a real scan
        logger.warning(f"[cache] get error (falling through to scan): {exc}")
        return None


async def cache_result(prompt: str, result) -> bool:
    """
    Store a scan result in Redis with the configured TTL.

    Parameters
    ----------
    prompt  Original (un-normalised) prompt text
    result  SecurityScanResult instance to cache

    Returns True on success, False on any failure (non-fatal).
    """
    client = _get_client()
    if client is None:
        return False

    key = _make_cache_key(prompt)

    try:
        payload = json.dumps(result.dict())
        await client.setex(key, CACHE_TTL, payload)
        logger.debug(
            f"[cache] SET   key=…{key[-12:]}  "
            f"ttl={CACHE_TTL}s  risk={result.risk_level}"
        )
        return True

    except Exception as exc:
        logger.warning(f"[cache] set error (non-fatal): {exc}")
        return False


async def invalidate(prompt: str) -> bool:
    """
    Manually evict a cached result (e.g. after a false-negative report).
    Returns True if the key existed and was deleted.
    """
    client = _get_client()
    if client is None:
        return False

    key = _make_cache_key(prompt)
    try:
        deleted = await client.delete(key)
        if deleted:
            logger.info(f"[cache] EVICTED key=…{key[-12:]}")
        return bool(deleted)
    except Exception as exc:
        logger.warning(f"[cache] invalidate error: {exc}")
        return False


async def flush_all() -> bool:
    """
    Delete ALL guardrail scan cache entries (uses SCAN + DEL, not FLUSHDB).
    Safe to call in production — only touches keys with our prefix.
    """
    client = _get_client()
    if client is None:
        return False

    deleted = 0
    try:
        async for key in client.scan_iter(match=f"{CACHE_PREFIX}*", count=100):
            await client.delete(key)
            deleted += 1
        logger.info(f"[cache] Flushed {deleted} scan cache entries")
        return True
    except Exception as exc:
        logger.warning(f"[cache] flush error: {exc}")
        return False


async def get_stats() -> dict:
    """
    Return cache statistics useful for the /health or /api/stats endpoint.
    Always returns a dict — never raises.
    """
    client = _get_client()
    if client is None:
        return {"enabled": False, "reason": "Redis not configured"}

    try:
        # Count keys with our prefix
        count = 0
        async for _ in client.scan_iter(match=f"{CACHE_PREFIX}*", count=100):
            count += 1

        info = await client.info("server")

        return {
            "enabled":       True,
            "redis_url":     REDIS_URL.split("@")[-1],  # hide credentials
            "cached_scans":  count,
            "ttl_seconds":   CACHE_TTL,
            "prefix":        CACHE_PREFIX,
            "redis_version": info.get("redis_version", "unknown"),
        }
    except Exception as exc:
        return {"enabled": True, "error": str(exc)}