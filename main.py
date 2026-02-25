"""
Guardrail Cloud Service — Main Entry Point
==========================================

Architecture
------------

  POST /api/chat
      Calls Azure LLM, stores both turns in MongoDB in the background.
      The RealtimeMonitor Change Stream scans the user message asynchronously.

  POST /api/test-chat
      Inserts ONLY the user message into MongoDB (no LLM call).
      Use this to inject test payloads for the monitor to scan.

  GET  /api/monitor/stream   — SSE: real-time scan events
  GET  /api/conversations/*  — all conversation reads → MongoDB ONLY
  GET  /api/security-logs/*  — all validation details → local JSON ONLY
  POST /api/scan             — ad-hoc scan (nothing persisted)
  POST /api/batch/*          — bulk-process unprocessed MongoDB docs

Rules
-----
1.  Security scanning ONLY happens inside RealtimeMonitor (or /api/scan).
2.  /api/test-chat NEVER calls the scanner — it only writes to MongoDB.
3.  Conversation data is ALWAYS fetched via MongoDB.
4.  Security-log data is ALWAYS read from local security_logs/*.json.
"""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_CONFIG, ALLOWED_ORIGINS, AZURE_API_KEY, LOG_LEVEL
from datetime_utils import now
from models import HealthResponse, StatsResponse
from mongodb_storage import connect_mongodb, close_mongodb, get_mongodb
from config import MONGODB_CONVERSATIONS_COLLECTION, AVAILABLE_MODELS
from security_scanner import ConcurrentSecurityScanner, shutdown_scanner
from realtime_monitor import get_monitor, shutdown_monitor
from mongodb_storage import mark_conversation_processed

# Static frontend
from static_routes import router as static_router, mount_static

# Route modules
from routes.chat          import router as chat_router
from routes.conversations import router as conversations_router
from routes.security_logs import router as security_logs_router
from routes.monitor       import router as monitor_router
from routes.scan          import router as scan_router
from routes.admin         import router as admin_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Suppress noisy Presidio internal logs that fire on every analyze() call:
#   INFO:presidio-analyzer:Fetching all recognizers for language en
#   WARNING:presidio-analyzer:Entity CUSTOM doesn't have the corresponding recognizer in language : en
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(**API_CONFIG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(static_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(security_logs_router)
app.include_router(monitor_router)
app.include_router(scan_router)
app.include_router(admin_router)

# Legacy aliases (keep old URLs working while frontend migrates)
from routes.security_logs import get_all_security_logs, get_bot_security_log
from fastapi import Query
from typing import Optional

@app.get("/api/security", tags=["Security Logs (legacy)"], include_in_schema=False)
async def _legacy_security(
    bot_id: Optional[str] = Query(None),
    skip:   int           = Query(0, ge=0),
    limit:  int           = Query(100, ge=1, le=1000),
):
    return await get_all_security_logs(bot_id=bot_id, skip=skip, limit=limit)

@app.get("/api/security/{bot_id}", tags=["Security Logs (legacy)"], include_in_schema=False)
async def _legacy_security_bot(bot_id: str):
    return await get_bot_security_log(bot_id=bot_id)


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------

_scanner = ConcurrentSecurityScanner()

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    return HealthResponse(
        status="connected",
        service="Guardrail Cloud Service",
        timestamp=now(),
        scanners_active=len(_scanner.scanners) + 1,
    )


@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    return StatsResponse(
        service="Guardrail Cloud Service",
        version="2.0.0",
        scanners={
            "prompt_injection": {
                "name":            "Prompt Injection Scanner",
                "threshold":       0.8,
                "description":     "Detects prompt injection and jailbreak attempts",
                "concurrent_safe": True,
            },
            "toxicity": {
                "name":            "Toxicity Scanner",
                "threshold":       0.5,
                "description":     "Detects toxic and harmful content",
                "concurrent_safe": True,
            },
            "pii": {
                "name":            "PII Detection & Anonymization",
                "threshold":       0.5,
                "description":     "Detects and anonymizes personal information",
                "concurrent_safe": True,
            },
            "secrets": {
                "name":            "Secrets Scanner",
                "threshold":       0.0,
                "description":     "Detects API keys, passwords, and tokens",
                "concurrent_safe": True,
            },
        },
        models_available=AVAILABLE_MODELS,
    )


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

mount_static(app)


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 70)
    logger.info("🚀  Guardrail Cloud Service — starting up")
    logger.info("=" * 70)

    logger.info("🔌  Connecting to MongoDB …")
    if connect_mongodb():
        logger.info("✅  MongoDB connected")
    else:
        logger.warning("⚠️   MongoDB unavailable — chat and conversation endpoints will fail")

    monitor = get_monitor()
    asyncio.create_task(monitor.run_forever())
    logger.info("📡  Real-time monitor background task launched")
    logger.info("✅  Security scanners: Prompt Injection | Toxicity | PII | Secrets")

    # =========================================================================
    # 🔥 WARMUP: Pre-compile ONNX graphs + warm CPU caches for all scanners.
    #
    # Without this, the very first real request triggers JIT compilation of
    # every ONNX model and a cold CPU cache read of hundreds of MBs of weights,
    # adding 3-5s to that first request.
    #
    # With this warmup, all graphs are compiled during startup so every
    # subsequent request (including the very first real one) runs at ~1s.
    # =========================================================================
    await _scanner.warmup()

    logger.info("=" * 70)

    if not AZURE_API_KEY:
        logger.warning("⚠️   AZURE_API_KEY not set — LLM calls will fail")


@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scanner()
    shutdown_monitor()
    close_mongodb()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)

# ---------------------------------------------------------------------------
# Cache management endpoints
# ---------------------------------------------------------------------------

@app.get("/api/cache/stats", tags=["Cache"])
async def cache_stats():
    """Redis scan-cache statistics (key count, TTL, version)."""
    from redis_cache import get_stats
    return {"success": True, **(await get_stats()), "timestamp": now()}


@app.post("/api/cache/flush", tags=["Cache"])
async def cache_flush():
    """
    Evict all cached scan results.
    Use after updating scanner thresholds or models so stale results
    are not served.
    """
    from redis_cache import flush_all
    ok = await flush_all()
    return {
        "success": ok,
        "message": "All scan cache entries evicted." if ok else "Nothing to flush (Redis not connected).",
        "timestamp": now(),
    }


@app.delete("/api/cache/entry", tags=["Cache"])
async def cache_invalidate_entry(prompt: str):
    """
    Evict the cached result for a single prompt.
    Useful after a false-negative is reported.
    """
    from redis_cache import invalidate
    evicted = await invalidate(prompt)
    return {
        "success": True,
        "evicted": evicted,
        "message": "Entry evicted." if evicted else "Key not found in cache.",
        "timestamp": now(),
    }


@app.get("/api/cache/diagnose", tags=["Cache"])
async def cache_diagnose():
    """
    🔍 Full Redis cache diagnostic — open this in your browser.
    Checks: package installed, REDIS_URL set, ping, read/write, key count.
    """
    import os
    report = {
        "timestamp": now(),
        "checks": {},
        "verdict": None,
        "fix": None,
    }

    # ── 1. Package installed? ──────────────────────────────────────────────
    try:
        import redis.asyncio as aioredis
        report["checks"]["package_installed"] = {
            "ok": True,
            "detail": "redis package found"
        }
    except ImportError:
        report["checks"]["package_installed"] = {
            "ok": False,
            "detail": "redis package NOT installed"
        }
        report["verdict"] = "FAILED"
        report["fix"] = "Run:  pip install redis  then restart the server"
        return report

    # ── 2. REDIS_URL set? ─────────────────────────────────────────────────
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        report["checks"]["redis_url"] = {
            "ok": False,
            "detail": "REDIS_URL environment variable is not set"
        }
        report["verdict"] = "FAILED"
        report["fix"] = "Add  REDIS_URL=redis://localhost:6379  to your .env file and restart"
        return report

    report["checks"]["redis_url"] = {
        "ok": True,
        "detail": f"REDIS_URL is set → {redis_url.split('@')[-1]}"   # hide password
    }

    # ── 3. Can we connect + ping? ─────────────────────────────────────────
    try:
        client = aioredis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        pong = await client.ping()
        report["checks"]["ping"] = {"ok": True, "detail": f"PONG received: {pong}"}
    except Exception as e:
        report["checks"]["ping"] = {"ok": False, "detail": str(e)}
        report["verdict"] = "FAILED"
        report["fix"] = "Redis is unreachable. Make sure Redis server is running."
        return report

    # ── 4. Read / write test ──────────────────────────────────────────────
    try:
        await client.set("guardrail:_diag_test", "ok", ex=30)
        val = await client.get("guardrail:_diag_test")
        await client.delete("guardrail:_diag_test")
        report["checks"]["read_write"] = {
            "ok": val in ("ok", b"ok"),  # redis may return str or bytes
            "detail": "SET + GET + DEL all succeeded"
        }
    except Exception as e:
        report["checks"]["read_write"] = {"ok": False, "detail": str(e)}
        report["verdict"] = "FAILED"
        report["fix"] = "Redis connected but read/write failed — check permissions."
        return report

    # ── 5. How many cached scan keys exist right now? ─────────────────────
    try:
        prefix = os.getenv("REDIS_CACHE_PREFIX", "guardrail:scan:")
        count = 0
        async for _ in client.scan_iter(match=f"{prefix}*", count=100):
            count += 1
        report["checks"]["cached_scan_keys"] = {
            "ok": True,
            "detail": f"{count} scan result(s) currently cached"
        }
    except Exception as e:
        report["checks"]["cached_scan_keys"] = {"ok": False, "detail": str(e)}

    # ── 6. Simulate a real cache round-trip with "bitch" ──────────────────
    try:
        from redis_cache import get_cached_result, cache_result
        from models import SecurityScanResult
        from datetime_utils import now as _now

        test_prompt = "bitch"

        # Check if it's already cached from a real scan
        cached = await get_cached_result(test_prompt)
        if cached:
            report["checks"]["live_cache_hit"] = {
                "ok": True,
                "detail": f"'bitch' is already cached → risk={cached.risk_level}, safe={cached.is_safe}"
            }
        else:
            # Write a dummy entry, read it back, then delete
            dummy = SecurityScanResult(
                is_safe=False,
                detections={"toxicity": {"detected": True, "risk_score": 0.95}},
                risk_level="CRITICAL",
                message="test",
                timestamp=_now(),
                scan_duration=0.001,
            )
            await cache_result(test_prompt, dummy)
            readback = await get_cached_result(test_prompt)
            await client.delete(f"{prefix}{__import__('hashlib').sha256('bitch'.encode()).hexdigest()}")

            report["checks"]["live_cache_hit"] = {
                "ok": readback is not None,
                "detail": (
                    "Round-trip write→read succeeded — cache is working correctly"
                    if readback else "Write succeeded but read returned None — unexpected"
                )
            }
    except Exception as e:
        report["checks"]["live_cache_hit"] = {"ok": False, "detail": str(e)}

    await client.aclose()

    # ── Final verdict ─────────────────────────────────────────────────────
    all_ok = all(v["ok"] for v in report["checks"].values())
    report["verdict"] = "✅ CACHE IS WORKING" if all_ok else "⚠️ PARTIAL — see checks above"
    if all_ok:
        report["fix"] = None
        report["note"] = (
            "Every repeated prompt will now return from cache in ~5ms "
            "instead of running the full 1-2s scan pipeline."
        )

    return report