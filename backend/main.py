"""
Guardrail Cloud Service — Main API
====================================

Architecture (read this before touching endpoints)
----------------------------------------------------

  ┌──────────────────────────────────────────────────────────────────────┐
  │  /api/test-chat  (POST)                                              │
  │   → inserts raw message into MongoDB (no scan here)                  │
  │   → monitor Change-Stream picks it up and scans it asynchronously    │
  │   → result arrives on the SSE stream (/api/monitor/stream)           │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  RealtimeMonitor (background task)                                   │
  │   → watches MongoDB conversations collection via Change Stream       │
  │   → scans every NEW user message with ConcurrentSecurityScanner      │
  │   → writes result to  security_logs/{botId}.json  (LOCAL only)      │
  │   → broadcasts scan events to all SSE subscribers                    │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  /api/conversations/*  ← ALL conversation reads → MongoDB ONLY       │
  │  /api/monitor/stream   ← real-time scan events   → SSE              │
  │  /api/security-logs/*  ← ALL validation details  → LOCAL JSON only  │
  └──────────────────────────────────────────────────────────────────────┘

Rules enforced here
--------------------
1.  Validation / security scanning ONLY happens inside RealtimeMonitor.
2.  /api/test-chat NEVER calls the scanner directly — it only writes to MongoDB.
3.  Conversation data is ALWAYS fetched via fetch_conversations() from MongoDB.
4.  Security-log/validation data is ALWAYS read from local security_logs/*.json.
5.  The frontend MUST NOT mix these two sources.
"""

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import logging
import time
import asyncio
import json
import uuid

from config import (
    API_CONFIG,
    ALLOWED_ORIGINS,
    AVAILABLE_MODELS,
    LOG_LEVEL,
    OPENROUTER_API_KEY,
    SECURITY_STORAGE_DIR,
)
try:
    from config import MONGODB_CONVERSATIONS_COLLECTION
except ImportError:
    MONGODB_CONVERSATIONS_COLLECTION = "messages"

from models import (
    ScanRequest, SecurityScanResult,
    HealthResponse, StatsResponse,
)
from mongodb_storage import (
    connect_mongodb,
    close_mongodb,
    get_mongodb,
    fetch_conversations,        # ← THE common helper
    save_conversation,
    insert_test_message,
    get_unprocessed_conversations,
    mark_conversation_processed,
    get_processing_stats,
    build_conversation,
)
from security_scanner import ConcurrentSecurityScanner, shutdown_scanner
from llm_client import call_openrouter
from datetime_utils import now
from realtime_monitor import get_monitor, shutdown_monitor
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

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

# Scan-only detector (for /api/scan endpoint; NOT used by test-chat)
detector = ConcurrentSecurityScanner()


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request body for /api/chat  (the main user-facing chat endpoint).
    """
    prompt:  str = Field(..., min_length=1, max_length=10_000)
    bot_id:  str = Field(..., description="Bot / session ID")
    model:   str = Field(default="openai/gpt-4o-mini")

    @validator("prompt")
    def strip_prompt(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("prompt cannot be blank")
        return v


class TestChatRequest(BaseModel):
    """
    Request body for /api/test-chat.
    The prompt is stored in MongoDB AS-IS; the monitor handles scanning.
    """
    prompt:  str = Field(..., min_length=1, max_length=10_000)
    bot_id:  str = Field(..., description="Bot / session ID")
    model:   str = Field(default="openai/gpt-4o-mini")

    @validator("prompt")
    def strip_prompt(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("prompt cannot be blank")
        return v


# ============================================================================
# HEALTH
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    return HealthResponse(
        status="connected",
        service="Guardrail Cloud Service",
        timestamp=now(),
        scanners_active=len(detector.scanners) + 1,
    )


# ============================================================================
#  MAIN CHAT ENDPOINT  /api/chat
#
#  Flow (zero blocking for the user):
#    1. Call LLM immediately → return response to frontend
#    2. asyncio.create_task() fires background coroutine that stores:
#         • user message doc  → MongoDB  (monitor scans it via Change Stream)
#         • bot response doc  → MongoDB  (stored separately, role = "bot")
#
#  The user never waits for storage or scanning.
# ============================================================================

async def _store_conversation_background(
    bot_id: str,
    thread_id: str,
    conversation_id: str,
    user_message_id: str,
    bot_message_id: str,
    user_id: str,
    prompt: str,
    llm_response: str,
    model: str,
    ts: str,
) -> None:
    """
    Fire-and-forget coroutine that persists one user turn to MongoDB.

    Stores TWO documents:
      1. User message  — picked up by the monitor's Change Stream for scanning
      2. Bot response  — stored for conversation history (role = "bot", not scanned)
    """
    db = get_mongodb()
    if db is None:
        logger.warning("[_store_background] MongoDB not connected — skipping storage")
        return

    collection = db[MONGODB_CONVERSATIONS_COLLECTION]

    # ── 1. User message document ─────────────────────────────────────────────
    user_doc = {
        "messageId":      user_message_id,
        "botId":          bot_id,
        "threadId":       thread_id,
        "conversationId": conversation_id,
        "userId":         user_id,
        "from": {
            "role": "user",
            "id":   user_id,
        },
        "activity": {
            "role":      "user",
            "text":      prompt,
            "timestamp": ts,
        },
        "processed": False,
        "source":    "chat",
        "createdAt": ts,
        "updatedAt": ts,
    }

    # ── 2. Bot response document ──────────────────────────────────────────────
    bot_doc = {
        "messageId":      bot_message_id,
        "botId":          bot_id,
        "threadId":       thread_id,
        "conversationId": conversation_id,
        "userId":         user_id,
        "from": {
            "role": "bot",
            "id":   bot_id,
        },
        "activity": {
            "role":      "bot",
            "text":      llm_response,
            "timestamp": now(),
        },
        "model":     model,
        "processed": True,          # bot messages are never scanned
        "source":    "chat",
        "createdAt": now(),
        "updatedAt": now(),
    }

    try:
        collection.insert_many([user_doc, bot_doc], ordered=False)
        logger.debug(f"[_store_background] Stored user={user_message_id} bot={bot_message_id}")
    except Exception as exc:
        # Surface per-document errors from BulkWriteError so you can see which doc failed
        from pymongo.errors import BulkWriteError
        if isinstance(exc, BulkWriteError):
            for we in exc.details.get("writeErrors", []):
                failed_id = we.get("op", {}).get("messageId", "?")
                code = we.get("code", "?")
                msg  = we.get("errmsg", "?")
                logger.error(
                    f"[_store_background] Insert rejected for messageId={failed_id} "
                    f"(code={code}): {msg}"
                )
        else:
            logger.error(f"[_store_background] Storage failed: {exc}")


@app.post("/api/chat", tags=["Chat"])
async def chat(request: ChatRequest):
    """
    💬 MAIN CHAT ENDPOINT — smooth, non-blocking.

    Returns the LLM response immediately.
    Storage + security scanning happen in the background via the monitor.
    """
    try:
        ts_ms           = int(time.time() * 1000)
        user_message_id = f"msg_user_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:6]}"
        bot_message_id  = f"msg_bot_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:6]}"
        conversation_id = f"conv_{request.bot_id}_{ts_ms}"
        thread_id = (
            f"thread_{request.bot_id.split('_')[1]}"
            if "_" in request.bot_id
            else f"thread_{request.bot_id}"
        )
        user_id = (
            f"user_{request.bot_id.split('_')[1]}"
            if "_" in request.bot_id
            else f"user_{request.bot_id}"
        )
        ts = now()

        # ── Call LLM immediately ───────────────────────────────────────────────
        llm_response_raw = await call_openrouter(request.prompt, request.model)
        assistant_message = (
            llm_response_raw
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        # ── Fire-and-forget background storage ────────────────────────────────
        asyncio.create_task(
            _store_conversation_background(
                bot_id          = request.bot_id,
                thread_id       = thread_id,
                conversation_id = conversation_id,
                user_message_id = user_message_id,
                bot_message_id  = bot_message_id,
                user_id         = user_id,
                prompt          = request.prompt,
                llm_response    = assistant_message,
                model           = request.model,
                ts              = ts,
            )
        )

        logger.info(
            f"[chat] bot={request.bot_id!r} responded, "
            f"storing in background (user={user_message_id})"
        )

        return {
            "success":          True,
            "response":         assistant_message,
            "message_id":       user_message_id,
            "conversation_id":  conversation_id,
            "model":            request.model,
            "usage":            llm_response_raw.get("usage", {}),
            "timestamp":        ts,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[chat] Error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {exc}",
        )


# ============================================================================
#  TEST CHAT ENDPOINT
#  Writes the message to MongoDB.  The RealtimeMonitor does the actual scan.
# ============================================================================

@app.post("/api/test-chat", tags=["Test Chat"])
async def test_chat(request: TestChatRequest):
    """
    ✉️  TEST CHAT — stores message in MongoDB, validation happens via monitor.

    Flow
    ----
    1.  Generate unique IDs for this message.
    2.  Insert the raw document into the MongoDB conversations collection.
    3.  Return immediately — the monitor's Change Stream will pick up the new
        document, scan it, and push the result over SSE.

    The response contains the message_id so the frontend can correlate the
    incoming SSE event with this request.
    """
    try:
        # Generate stable IDs
        ts_ms         = int(time.time() * 1000)
        message_id    = f"msg_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:8]}"
        conversation_id = f"conv_{request.bot_id}_{ts_ms}"
        thread_id     = (
            f"thread_{request.bot_id.split('_')[1]}"
            if "_" in request.bot_id
            else f"thread_{request.bot_id}"
        )
        user_id = (
            f"user_{request.bot_id.split('_')[1]}"
            if "_" in request.bot_id
            else f"user_{request.bot_id}"
        )

        ok = insert_test_message(
            bot_id          = request.bot_id,
            thread_id       = thread_id,
            conversation_id = conversation_id,
            message_id      = message_id,
            text            = request.prompt,
            user_id         = user_id,
        )

        if not ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to store message in MongoDB — check DB connection",
            )

        logger.info(
            f"[test-chat] Stored msg {message_id} for bot {request.bot_id!r} "
            f"— waiting for monitor to scan"
        )

        return {
            "success":         True,
            "message":         "Message stored. Validation is processing via the real-time monitor.",
            "message_id":      message_id,
            "conversation_id": conversation_id,
            "thread_id":       thread_id,
            "bot_id":          request.bot_id,
            "hint":            "Subscribe to /api/monitor/stream to receive the scan result.",
            "timestamp":       now(),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[test-chat] Unexpected error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {exc}",
        )


# ============================================================================
#  REAL-TIME MONITOR — SSE STREAM
#  Pushes scan events as the monitor processes MongoDB documents.
# ============================================================================

@app.get("/api/monitor/stream", tags=["Real-Time Monitor"])
async def stream_monitor():
    """
    📡 SSE endpoint — subscribe to receive real-time validation events.

    Frontend usage
    --------------
    const es = new EventSource('/api/monitor/stream');
    es.addEventListener('processed', (e) => {
        const data = JSON.parse(e.data);
        // data.message_id, data.is_blocked, data.has_pii, etc.
    });
    es.addEventListener('stats',     (e) => { ... });
    es.addEventListener('error',     (e) => { ... });
    """
    monitor = get_monitor()
    return StreamingResponse(
        monitor.sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/monitor/status", tags=["Real-Time Monitor"])
async def get_monitor_status():
    """Current monitor statistics."""
    monitor = get_monitor()
    return {
        "running":         monitor.running,
        "processed_count": monitor.processed_count,
        "skipped_count":   monitor.skipped_count,
        "error_count":     monitor.error_count,
        "subscribers":     len(monitor._sse_queues),
        "timestamp":       now(),
    }


@app.post("/api/monitor/stop", tags=["Real-Time Monitor"])
async def stop_monitor():
    """Stop the real-time monitor (admin use)."""
    monitor = get_monitor()
    monitor.stop()
    return {
        "success":         True,
        "message":         "Monitor stopped",
        "processed_count": monitor.processed_count,
        "error_count":     monitor.error_count,
        "timestamp":       now(),
    }


@app.get("/api/admin/diagnose", tags=["Admin"])
async def diagnose_unprocessed():
    """
    🔍 Show exactly why unprocessed docs are being skipped.
    Run this when backfill shows 0/N scanned.
    """
    db = get_mongodb()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")

    col = db[MONGODB_CONVERSATIONS_COLLECTION]
    docs = list(col.find({"processed": {"$ne": True}}).limit(20))

    results = []
    monitor = get_monitor()
    for doc in docs:
        report = monitor.diagnose_document(doc)
        # Keep only the fields useful for diagnosis
        results.append({
            "messageId":      doc.get("messageId"),
            "botId":          doc.get("botId"),
            "threadId":       doc.get("threadId"),
            "conversationId": doc.get("conversationId"),
            "from_role":      doc.get("from", {}).get("role"),
            "processed":      doc.get("processed"),
            "text_preview":   (doc.get("activity", {}).get("text") or "")[:60],
            "verdict":        report.get("verdict"),
            "checks":         report.get("checks"),
        })

    return {
        "total_unprocessed": len(docs),
        "results": results,
        "timestamp": now(),
    }


async def fix_indexes():
    """
    🔧 Drop and recreate all MongoDB indexes cleanly.
    Run this once if you see IndexKeySpecsConflict errors on startup.
    """
    db = get_mongodb()
    if db is None:
        raise HTTPException(status_code=503, detail="MongoDB not connected")

    col = db[MONGODB_CONVERSATIONS_COLLECTION]
    dropped = []
    errors  = []

    # Drop every index except the immutable _id index
    try:
        existing = [idx["name"] for idx in col.list_indexes() if idx["name"] != "_id_"]
        for name in existing:
            try:
                col.drop_index(name)
                dropped.append(name)
                logger.info(f"[fix-indexes] Dropped: {name}")
            except Exception as e:
                errors.append({"index": name, "error": str(e)})
                logger.warning(f"[fix-indexes] Could not drop {name}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not list indexes: {e}")

    # Recreate the correct set
    from pymongo import ASCENDING, DESCENDING
    created = []
    specs = [
        ("conversationId", {}),
        ("messageId",      {"unique": True, "sparse": True}),
        ("botId",          {}),
        ("threadId",       {}),
        ([("createdAt", DESCENDING)], {}),
        ("processed",      {}),
    ]
    for keys, kwargs in specs:
        try:
            col.create_index(keys, **kwargs)
            created.append(str(keys))
        except Exception as e:
            errors.append({"index": str(keys), "error": str(e)})
            logger.warning(f"[fix-indexes] Could not create {keys}: {e}")

    return {
        "success": len(errors) == 0,
        "dropped": dropped,
        "created": created,
        "errors":  errors,
        "message": "Indexes fixed. Restart the server to apply the backfill." if not errors else "Some errors occurred — see 'errors' field.",
        "timestamp": now(),
    }


# ============================================================================
#  CONVERSATION ENDPOINTS  ← ALL DATA FROM MONGODB ONLY
# ============================================================================

@app.get("/api/conversations", tags=["Conversations"])
async def list_conversations(
    bot_id:      Optional[str] = Query(None, description="Filter by bot ID"),
    thread_id:   Optional[str] = Query(None, description="Filter by thread ID"),
    role:        Optional[str] = Query(None, description="Filter by from.role (e.g. 'user')"),
    unprocessed: bool           = Query(False, description="Only return unprocessed messages"),
    skip:        int            = Query(0, ge=0),
    limit:       int            = Query(50, ge=1, le=500),
):
    """
    📦 Fetch conversations from MongoDB.

    All filtering / pagination is done server-side via fetch_conversations().
    """
    result = fetch_conversations(
        bot_id           = bot_id,
        thread_id        = thread_id,
        role             = role,
        only_unprocessed = unprocessed,
        skip             = skip,
        limit            = limit,
    )
    return {"success": True, **result}


@app.get("/api/conversations/{conversation_id}", tags=["Conversations"])
async def get_conversation(conversation_id: str):
    """
    Fetch a single conversation document from MongoDB by its conversationId.
    """
    result = fetch_conversations(conversation_id=conversation_id, limit=1)
    docs = result.get("conversations", [])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )
    return {"success": True, "conversation": docs[0], "timestamp": now()}


@app.get("/api/conversations/bot/{bot_id}", tags=["Conversations"])
async def get_bot_conversations(
    bot_id:    str,
    thread_id: Optional[str] = Query(None),
    skip:      int            = Query(0, ge=0),
    limit:     int            = Query(50, ge=1, le=500),
):
    """
    Fetch all conversations for a specific bot from MongoDB.
    Optionally filter by thread_id.
    """
    result = fetch_conversations(
        bot_id    = bot_id,
        thread_id = thread_id,
        skip      = skip,
        limit     = limit,
    )
    return {"success": True, "bot_id": bot_id, **result}


@app.get("/api/conversations/thread/{thread_id}", tags=["Conversations"])
async def get_thread_conversations(
    thread_id: str,
    skip:  int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Fetch all messages belonging to a thread from MongoDB.
    """
    result = fetch_conversations(thread_id=thread_id, skip=skip, limit=limit)
    return {"success": True, "thread_id": thread_id, **result}


@app.get("/api/conversations/message/{message_id}", tags=["Conversations"])
async def get_message(message_id: str):
    """
    Fetch a single message document from MongoDB by messageId.
    """
    result = fetch_conversations(message_id=message_id, limit=1)
    docs = result.get("conversations", [])
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message '{message_id}' not found",
        )
    return {"success": True, "message": docs[0], "timestamp": now()}


# ============================================================================
#  SECURITY LOG ENDPOINTS  ← ALL DATA FROM LOCAL JSON FILES ONLY
# ============================================================================

@app.get("/api/security-logs", tags=["Security Logs"])
async def get_all_security_logs(
    bot_id: Optional[str] = Query(None),
    skip:   int           = Query(0, ge=0),
    limit:  int           = Query(100, ge=1, le=1000),
):
    """
    📂 Read all security logs from local ``security_logs/`` folder.

    Each file = one bot's aggregated scan results.  The frontend should call
    this endpoint (not MongoDB) for all validation / threat details.
    """
    logs = []

    SECURITY_STORAGE_DIR.mkdir(exist_ok=True)
    for log_file in sorted(SECURITY_STORAGE_DIR.glob("*.json")):
        if log_file.name.startswith("."):          # skip .resume_token.json
            continue
        try:
            with open(log_file) as f:
                data = json.load(f)
            if bot_id and data.get("bot_id") != bot_id:
                continue
            logs.append(data)
        except Exception as exc:
            logger.warning(f"Could not read {log_file}: {exc}")

    total         = len(logs)
    paginated     = logs[skip: skip + limit]
    total_prompts = sum(lg.get("total_prompts",       0) for lg in logs)
    total_blocked = sum(lg.get("blocked_prompts",     0) for lg in logs)
    total_pii     = sum(lg.get("pii_detections",      0) for lg in logs)
    total_jb      = sum(lg.get("jailbreak_attempts",  0) for lg in logs)
    total_tox     = sum(lg.get("toxicity_detections", 0) for lg in logs)
    total_sec     = sum(lg.get("secrets_detections",  0) for lg in logs)

    return {
        "success":  True,
        "sessions": paginated,
        "total":    total,
        "skip":     skip,
        "limit":    limit,
        "stats": {
            "totalConversations": total,
            "totalPrompts":   total_prompts,
            "totalBlocked":   total_blocked,
            "totalPII":       total_pii,
            "totalJailbreaks": total_jb,
            "totalToxicity":  total_tox,
            "totalSecrets":   total_sec,
        },
        "timestamp": now(),
    }


@app.get("/api/security-logs/local", tags=["Security Logs"])
async def get_local_security_logs_alias(
    bot_id: Optional[str] = Query(None),
    skip:   int           = Query(0, ge=0),
    limit:  int           = Query(100, ge=1, le=1000),
):
    """Alias for /api/security-logs — kept for backward compatibility."""
    return await get_all_security_logs(bot_id=bot_id, skip=skip, limit=limit)


@app.get("/api/security-logs/stats/summary", tags=["Security Logs"])
async def get_security_stats_summary(bot_id: Optional[str] = Query(None)):
    """Aggregate statistics across all local security-log files."""
    totals = {
        "total_bots": 0,
        "total_prompts": 0,
        "total_blocked": 0,
        "total_pii": 0,
        "total_secrets": 0,
        "total_jailbreaks": 0,
        "total_toxicity": 0,
    }

    for log_file in SECURITY_STORAGE_DIR.glob("*.json"):
        if log_file.name.startswith("."):
            continue
        try:
            with open(log_file) as f:
                data = json.load(f)
            if bot_id and data.get("bot_id") != bot_id:
                continue
            totals["total_bots"]       += 1
            totals["total_prompts"]    += data.get("total_prompts",       0)
            totals["total_blocked"]    += data.get("blocked_prompts",     0)
            totals["total_pii"]        += data.get("pii_detections",      0)
            totals["total_secrets"]    += data.get("secrets_detections",  0)
            totals["total_jailbreaks"] += data.get("jailbreak_attempts",  0)
            totals["total_toxicity"]   += data.get("toxicity_detections", 0)
        except Exception as exc:
            logger.warning(f"Could not read {log_file}: {exc}")

    return {**totals, "timestamp": now()}


@app.get("/api/security-logs/{bot_id}", tags=["Security Logs"])
async def get_bot_security_log(bot_id: str):
    """Read the security log for a specific bot from local JSON."""
    log_path = SECURITY_STORAGE_DIR / f"{bot_id}.json"
    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for bot_id: {bot_id}",
        )
    with open(log_path) as f:
        data = json.load(f)
    return {"success": True, "log": data, "timestamp": now()}


@app.get("/api/security-logs/{bot_id}/summary", tags=["Security Logs"])
async def get_bot_security_summary(bot_id: str):
    """Statistics summary for one bot from local JSON."""
    log_path = SECURITY_STORAGE_DIR / f"{bot_id}.json"
    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for bot_id: {bot_id}",
        )
    with open(log_path) as f:
        data = json.load(f)
    return {
        "bot_id":     data.get("bot_id"),
        "created_at": data.get("created_at"),
        "last_updated": data.get("last_updated"),
        "statistics": {
            "total_prompts":       data.get("total_prompts",       0),
            "blocked_prompts":     data.get("blocked_prompts",     0),
            "pii_detections":      data.get("pii_detections",      0),
            "jailbreak_attempts":  data.get("jailbreak_attempts",  0),
            "toxicity_detections": data.get("toxicity_detections", 0),
            "secrets_detections":  data.get("secrets_detections",  0),
            "total_events":        len(data.get("security_events", [])),
        },
    }


@app.get("/api/security-logs/{bot_id}/pii", tags=["Security Logs"])
async def get_bot_pii_events(bot_id: str):
    """Return only PII-flagged events for a bot from local JSON."""
    log_path = SECURITY_STORAGE_DIR / f"{bot_id}.json"
    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for bot_id: {bot_id}",
        )
    with open(log_path) as f:
        data = json.load(f)
    pii_events = [
        ev for ev in data.get("security_events", [])
        if ev.get("detections", {}).get("pii", {}).get("detected", False)
    ]
    return {
        "bot_id":              bot_id,
        "pii_detection_count": len(pii_events),
        "pii_events":          pii_events,
    }


@app.delete("/api/security-logs/{bot_id}", tags=["Security Logs"])
async def delete_bot_security_log(bot_id: str):
    """Delete the local security log for a bot."""
    log_path = SECURITY_STORAGE_DIR / f"{bot_id}.json"
    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for bot_id: {bot_id}",
        )
    log_path.unlink()
    return {"success": True, "message": f"Deleted security log for {bot_id}", "timestamp": now()}


@app.get("/api/security-logs/search/prompts", tags=["Security Logs"])
async def search_prompts(
    query:  str            = Query(..., min_length=3),
    bot_id: Optional[str] = Query(None),
    limit:  int            = Query(100, ge=1, le=500),
):
    """Full-text search over local security-log event prompts."""
    results = []
    q = query.lower()

    for log_file in SECURITY_STORAGE_DIR.glob("*.json"):
        if log_file.name.startswith(".") or len(results) >= limit:
            break
        try:
            with open(log_file) as f:
                data = json.load(f)
            if bot_id and data.get("bot_id") != bot_id:
                continue
            for ev in data.get("security_events", []):
                if q in ev.get("prompt", "").lower() or q in (ev.get("anonymized_prompt") or "").lower():
                    results.append(ev)
                    if len(results) >= limit:
                        break
        except Exception as exc:
            logger.warning(f"Could not read {log_file}: {exc}")

    return {
        "results":       results[:limit],
        "total_matches": len(results),
        "query":         query,
        "timestamp":     now(),
    }


@app.get("/api/security-logs/threats/top", tags=["Security Logs"])
async def get_top_threatening_bots(
    limit:  int            = Query(10, ge=1, le=100),
    bot_id: Optional[str] = Query(None),
):
    """Return bots with the most threat events (from local JSON)."""
    threats = []

    for log_file in SECURITY_STORAGE_DIR.glob("*.json"):
        if log_file.name.startswith("."):
            continue
        try:
            with open(log_file) as f:
                data = json.load(f)
            if bot_id and data.get("bot_id") != bot_id:
                continue
            pii  = data.get("pii_detections",      0)
            jb   = data.get("jailbreak_attempts",  0)
            tox  = data.get("toxicity_detections", 0)
            sec  = data.get("secrets_detections",  0)
            total = pii + jb + tox + sec
            if total > 0:
                threats.append({
                    "bot_id":              data.get("bot_id"),
                    "pii_detections":      pii,
                    "jailbreak_attempts":  jb,
                    "toxicity_detections": tox,
                    "secrets_detections":  sec,
                    "total_threats":       total,
                })
        except Exception as exc:
            logger.warning(f"Could not read {log_file}: {exc}")

    threats.sort(key=lambda x: x["total_threats"], reverse=True)
    return {"results": threats[:limit], "timestamp": now()}


# ============================================================================
#  LEGACY ALIASES  — keep old URLs working while dashboard migrates
# ============================================================================

@app.get("/api/security", tags=["Security Logs"])
async def legacy_security_alias(
    bot_id: Optional[str] = Query(None),
    skip:   int           = Query(0, ge=0),
    limit:  int           = Query(100, ge=1, le=1000),
):
    """Alias for /api/security-logs — kept for backward compatibility."""
    return await get_all_security_logs(bot_id=bot_id, skip=skip, limit=limit)


@app.get("/api/security/{bot_id}", tags=["Security Logs"])
async def legacy_security_bot_alias(bot_id: str):
    """Alias for /api/security-logs/{bot_id} — kept for backward compatibility."""
    return await get_bot_security_log(bot_id=bot_id)


# ============================================================================
#  SCAN-ONLY ENDPOINT  (direct scan — does NOT write to MongoDB or local JSON)
# ============================================================================

@app.post("/api/scan", response_model=SecurityScanResult, tags=["Security"])
async def scan_only(request: ScanRequest):
    """
    Scan a single prompt with all security checks and return results inline.
    Nothing is persisted — useful for ad-hoc testing.
    """
    try:
        loop = asyncio.get_event_loop()
        scan_results = await loop.run_in_executor(
            None, detector.scan_prompt_parallel, request.prompt, "scan-only"
        )
        return scan_results
    except Exception as exc:
        logger.error(f"Scan error: {exc}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}")


# ============================================================================
#  BATCH PROCESSING ENDPOINTS
#  Fetches unprocessed docs from MongoDB, scans, saves to local JSON.
# ============================================================================

@app.post("/api/batch/process-next", tags=["Batch Processing"])
async def process_next_conversation():
    """
    Process the next unprocessed conversation from MongoDB.
    Scans it and stores the result in security_logs/{bot_id}.json.
    """
    from storage import append_security_event

    conversations = get_unprocessed_conversations(limit=1)
    if not conversations:
        return {"success": False, "message": "No more conversations to process", "processed": False}

    conversation    = conversations[0]
    conversation_id = str(conversation.get("_id") or conversation.get("conversationId", "unknown"))
    prompt          = conversation.get("activity", {}).get("text", "") or conversation.get("message", "")
    bot_id          = conversation.get("botId") or f"batch_{conversation_id}"
    thread_id       = conversation.get("threadId", "unknown")
    message_id      = conversation.get("messageId") or conversation_id

    if not prompt:
        return {"success": False, "message": "Empty prompt — skipping", "conversation_id": conversation_id}

    loop          = asyncio.get_event_loop()
    request_start = time.time()
    scan_results  = await loop.run_in_executor(None, detector.scan_prompt_parallel, prompt, bot_id)

    pii_data      = scan_results.detections.get("pii", {})
    pii_entities  = pii_data.get("entities", [])
    has_pii       = bool(pii_entities)
    has_jailbreak = scan_results.detections.get("prompt_injection", {}).get("detected", False)
    has_toxicity  = scan_results.detections.get("toxicity", {}).get("detected", False)
    has_secrets   = pii_data.get("secrets_detected", False)
    is_blocked    = not scan_results.is_safe

    security_event = {
        "message_id":        message_id,
        "thread_id":         thread_id,
        "conversation_id":   conversation_id,
        "bot_id":            bot_id,
        "timestamp":         now(),
        "prompt":            prompt,
        "prompt_length":     len(prompt),
        "anonymized_prompt": pii_data.get("anonymized_prompt") if pii_entities else None,
        "detections":        scan_results.detections,
        "risk_level":        scan_results.risk_level,
        "is_safe":           scan_results.is_safe,
        "blocked":           is_blocked,
        "block_reason":      scan_results.message if is_blocked else None,
        "scan_duration":     round(scan_results.scan_duration, 4),
        "metrics": {
            "scan_time":   round(scan_results.scan_duration, 4),
            "total_time":  round(time.time() - request_start, 4),
        },
    }

    append_security_event(
        bot_id        = bot_id,
        message_id    = message_id,
        security_event = security_event,
        is_blocked    = is_blocked,
        has_pii       = has_pii,
        has_jailbreak = has_jailbreak,
        has_toxicity  = has_toxicity,
        has_secrets   = has_secrets,
    )
    mark_conversation_processed(conversation_id, bot_id)

    return {
        "success":         True,
        "processed":       True,
        "conversation_id": conversation_id,
        "security_log_id": bot_id,
        "scan_results": {
            "is_safe":        scan_results.is_safe,
            "risk_level":     scan_results.risk_level,
            "pii_detected":   has_pii,
            "threat_detected": is_blocked,
            "scan_duration":  round(scan_results.scan_duration, 4),
            "message":        scan_results.message,
        },
        "processing_stats": get_processing_stats(),
        "timestamp":        now(),
    }


@app.post("/api/batch/process-bulk", tags=["Batch Processing"])
async def process_bulk_conversations(count: int = Query(10, ge=1, le=200)):
    """Process up to *count* unprocessed conversations in sequence."""
    from storage import append_security_event

    results = []

    for i in range(count):
        conversations = get_unprocessed_conversations(limit=1)
        if not conversations:
            logger.info(f"Batch done after {i} — no more data")
            break

        conversation    = conversations[0]
        conversation_id = str(conversation.get("_id") or conversation.get("conversationId", "unknown"))
        prompt          = conversation.get("activity", {}).get("text", "") or conversation.get("message", "")
        bot_id          = conversation.get("botId") or f"batch_{conversation_id}"
        thread_id       = conversation.get("threadId", "unknown")
        message_id      = conversation.get("messageId") or conversation_id

        if not prompt:
            mark_conversation_processed(conversation_id, bot_id)
            continue

        loop          = asyncio.get_event_loop()
        request_start = time.time()
        scan_results  = await loop.run_in_executor(None, detector.scan_prompt_parallel, prompt, bot_id)

        pii_data      = scan_results.detections.get("pii", {})
        pii_entities  = pii_data.get("entities", [])
        has_pii       = bool(pii_entities)
        has_jailbreak = scan_results.detections.get("prompt_injection", {}).get("detected", False)
        has_toxicity  = scan_results.detections.get("toxicity", {}).get("detected", False)
        has_secrets   = pii_data.get("secrets_detected", False)
        is_blocked    = not scan_results.is_safe

        security_event = {
            "message_id":        message_id,
            "thread_id":         thread_id,
            "conversation_id":   conversation_id,
            "bot_id":            bot_id,
            "timestamp":         now(),
            "prompt":            prompt,
            "prompt_length":     len(prompt),
            "anonymized_prompt": pii_data.get("anonymized_prompt") if pii_entities else None,
            "detections":        scan_results.detections,
            "risk_level":        scan_results.risk_level,
            "is_safe":           scan_results.is_safe,
            "blocked":           is_blocked,
            "block_reason":      scan_results.message if is_blocked else None,
            "scan_duration":     round(scan_results.scan_duration, 4),
            "metrics": {
                "scan_time":  round(scan_results.scan_duration, 4),
                "total_time": round(time.time() - request_start, 4),
            },
        }

        append_security_event(
            bot_id         = bot_id,
            message_id     = message_id,
            security_event = security_event,
            is_blocked     = is_blocked,
            has_pii        = has_pii,
            has_jailbreak  = has_jailbreak,
            has_toxicity   = has_toxicity,
            has_secrets    = has_secrets,
        )
        mark_conversation_processed(conversation_id, bot_id)

        results.append({
            "conversation_id": conversation_id,
            "is_safe":         scan_results.is_safe,
            "risk_level":      scan_results.risk_level,
            "scan_duration":   round(scan_results.scan_duration, 4),
        })

    return {
        "success":          True,
        "count_processed":  len(results),
        "results":          results,
        "processing_stats": get_processing_stats(),
        "timestamp":        now(),
    }


@app.get("/api/batch/status", tags=["Batch Processing"])
async def get_batch_status():
    """Current batch processing statistics from MongoDB."""
    return {"success": True, "stats": get_processing_stats(), "timestamp": now()}


# ============================================================================
#  STATS
# ============================================================================

@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    return StatsResponse(
        service="Guardrail Cloud Service",
        version="2.0.0",
        scanners={
            "prompt_injection": {
                "name": "Prompt Injection Scanner",
                "threshold": 0.8,
                "description": "Detects prompt injection and jailbreak attempts",
                "concurrent_safe": True,
            },
            "toxicity": {
                "name": "Toxicity Scanner",
                "threshold": 0.5,
                "description": "Detects toxic and harmful content",
                "concurrent_safe": True,
            },
            "pii": {
                "name": "PII Detection & Anonymization",
                "threshold": 0.5,
                "description": "Detects and anonymizes personal information",
                "concurrent_safe": True,
            },
            "secrets": {
                "name": "Secrets Scanner",
                "threshold": 0.0,
                "description": "Detects API keys, passwords, and tokens",
                "concurrent_safe": True,
            },
        },
        models_available=AVAILABLE_MODELS,
    )


# ============================================================================
#  STARTUP / SHUTDOWN
# ============================================================================

async def _backfill_unprocessed():
    """
    On startup, scan any messages that were inserted into MongoDB before
    the Change Stream opened (e.g. from previous server runs).
    Runs once as a background task after a short delay to let the monitor connect.
    After scanning each doc, marks it processed=True in MongoDB so it won't
    be picked up again on the next server restart.
    """
    await asyncio.sleep(5)          # wait for monitor Change Stream to open
    logger.info("🔄  Backfill: checking for unprocessed messages...")

    try:
        db = get_mongodb()
        if db is None:
            logger.warning("Backfill skipped — MongoDB not connected")
            return

        collection = db[MONGODB_CONVERSATIONS_COLLECTION]
        # Only user messages that haven't been processed
        unprocessed = list(collection.find({
            "processed": {"$ne": True},
            "from.role": "user"
        }).limit(500))

        if not unprocessed:
            logger.info("🔄  Backfill: nothing to process")
            return

        logger.info(f"🔄  Backfill: found {len(unprocessed)} unprocessed user messages")

        mon = get_monitor()
        processed = 0
        for doc in unprocessed:
            try:
                result = mon.process_message(doc)
                if not result.get("skipped"):
                    processed += 1
                    # ── Mark processed in MongoDB so it won't be backfilled again ──
                    msg_id = doc.get("messageId") or doc.get("message_id")
                    if msg_id:
                        mark_conversation_processed(msg_id)
            except Exception as exc:
                logger.error(f"Backfill error on {doc.get('messageId')}: {exc}")

        logger.info(f"✅  Backfill complete — {processed}/{len(unprocessed)} messages scanned")

    except Exception as exc:
        logger.error(f"Backfill failed: {exc}")


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 70)
    logger.info("🚀  Guardrail Cloud Service — starting up")
    logger.info("=" * 70)

    # MongoDB connection (shared module)
    logger.info("🔌  Connecting to MongoDB …")
    if connect_mongodb():
        logger.info("✅  MongoDB connected")
    else:
        logger.warning("⚠️   MongoDB unavailable — test-chat and conversation endpoints will fail")

    # Launch the real-time monitor (runs forever as a background task)
    monitor = get_monitor()
    asyncio.create_task(monitor.run_forever())
    logger.info("📡  Real-time monitor background task launched")

    # Polling loop handles all unprocessed messages — no separate backfill needed

    logger.info("✅  Security scanners: Prompt Injection | Toxicity | PII | Secrets")
    logger.info("=" * 70)

    if not OPENROUTER_API_KEY:
        logger.warning("⚠️   OPENROUTER_API_KEY not set")


@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scanner()
    shutdown_monitor()
    close_mongodb()


# ============================================================================
#  ENTRYPOINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)