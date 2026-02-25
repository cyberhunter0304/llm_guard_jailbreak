"""
Security Log Routes
-------------------
All security / validation data is read from LOCAL JSON files only
(security_logs/{thread_id}.json).  Never mix with MongoDB conversation data.

GET    /api/security-logs                          — all logs (paginated)
GET    /api/security-logs/stats/summary            — aggregate stats
GET    /api/security-logs/search/prompts           — full-text search
GET    /api/security-logs/threats/top              — threads with most threats
GET    /api/security-logs/{thread_id}              — single thread log
GET    /api/security-logs/{thread_id}/summary      — stats for one thread
GET    /api/security-logs/{thread_id}/pii          — PII events for one thread
DELETE /api/security-logs/{thread_id}              — delete a thread log
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from config import SECURITY_STORAGE_DIR, DEFAULT_BOT_ID
from datetime_utils import now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security-logs", tags=["Security Logs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_log_files(thread_id: Optional[str] = None, bot_id: Optional[str] = None):
    """Yield parsed log dicts, optionally filtered by thread_id or bot_id."""
    SECURITY_STORAGE_DIR.mkdir(exist_ok=True)
    for log_file in sorted(SECURITY_STORAGE_DIR.glob("*.json")):
        if log_file.name.startswith("."):
            continue
        try:
            data = json.loads(log_file.read_text())
            if thread_id and data.get("thread_id") != thread_id:
                continue
            if bot_id and data.get("bot_id") != bot_id:
                continue
            yield data
        except Exception as exc:
            logger.warning(f"Could not read {log_file}: {exc}")


def _get_log_or_404(thread_id: str) -> dict:
    log_path = SECURITY_STORAGE_DIR / f"{thread_id}.json"
    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for thread_id: {thread_id}",
        )
    return json.loads(log_path.read_text())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/stats/summary")
async def get_security_stats_summary(
    bot_id:    Optional[str] = Query(None),
    thread_id: Optional[str] = Query(None),
):
    """Aggregate statistics across all local security-log files."""
    totals = {
        "total_threads":    0,
        "total_prompts":    0,
        "total_blocked":    0,
        "total_pii":        0,
        "total_secrets":    0,
        "total_jailbreaks": 0,
        "total_toxicity":   0,
    }
    for data in _iter_log_files(thread_id=thread_id, bot_id=bot_id):
        totals["total_threads"]    += 1
        totals["total_prompts"]    += data.get("total_prompts",       0)
        totals["total_blocked"]    += data.get("blocked_prompts",     0)
        totals["total_pii"]        += data.get("pii_detections",      0)
        totals["total_secrets"]    += data.get("secrets_detections",  0)
        totals["total_jailbreaks"] += data.get("jailbreak_attempts",  0)
        totals["total_toxicity"]   += data.get("toxicity_detections", 0)

    return {**totals, "timestamp": now()}


@router.get("/search/prompts")
async def search_prompts(
    query:     str            = Query(..., min_length=3),
    thread_id: Optional[str] = Query(None),
    bot_id:    Optional[str] = Query(None),
    limit:     int            = Query(100, ge=1, le=500),
):
    """Full-text search over security-log event prompts."""
    results = []
    q = query.lower()

    for data in _iter_log_files(thread_id=thread_id, bot_id=bot_id):
        if len(results) >= limit:
            break
        for ev in data.get("security_events", []):
            if q in ev.get("prompt", "").lower() or q in (ev.get("anonymized_prompt") or "").lower():
                results.append(ev)
                if len(results) >= limit:
                    break

    return {
        "results":       results[:limit],
        "total_matches": len(results),
        "query":         query,
        "timestamp":     now(),
    }


@router.get("/threats/top")
async def get_top_threatening_threads(
    limit:     int            = Query(10, ge=1, le=100),
    bot_id:    Optional[str] = Query(None),
):
    """Return threads with the most threat events."""
    threats = []
    for data in _iter_log_files(bot_id=bot_id):
        pii   = data.get("pii_detections",      0)
        jb    = data.get("jailbreak_attempts",  0)
        tox   = data.get("toxicity_detections", 0)
        sec   = data.get("secrets_detections",  0)
        total = pii + jb + tox + sec
        if total > 0:
            threats.append({
                "bot_id":              data.get("bot_id", DEFAULT_BOT_ID),
                "thread_id":           data.get("thread_id"),
                "pii_detections":      pii,
                "jailbreak_attempts":  jb,
                "toxicity_detections": tox,
                "secrets_detections":  sec,
                "total_threats":       total,
            })

    threats.sort(key=lambda x: x["total_threats"], reverse=True)
    return {"results": threats[:limit], "timestamp": now()}


@router.get("")
async def get_all_security_logs(
    bot_id:    Optional[str] = Query(None),
    thread_id: Optional[str] = Query(None),
    skip:      int           = Query(0, ge=0),
    limit:     int           = Query(100, ge=1, le=1000),
):
    """Read all security logs from the local security_logs/ folder."""
    logs          = list(_iter_log_files(thread_id=thread_id, bot_id=bot_id))
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
            "totalThreads":       total,
            "totalPrompts":       total_prompts,
            "totalBlocked":       total_blocked,
            "totalPII":           total_pii,
            "totalJailbreaks":    total_jb,
            "totalToxicity":      total_tox,
            "totalSecrets":       total_sec,
        },
        "timestamp": now(),
    }


@router.get("/{thread_id}/summary")
async def get_thread_security_summary(thread_id: str):
    """Statistics summary for one thread."""
    data = _get_log_or_404(thread_id)
    return {
        "bot_id":       data.get("bot_id", DEFAULT_BOT_ID),
        "thread_id":    data.get("thread_id"),
        "created_at":   data.get("created_at"),
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


@router.get("/{thread_id}/pii")
async def get_thread_pii_events(thread_id: str):
    """Return only PII-flagged events for a thread."""
    data = _get_log_or_404(thread_id)
    pii_events = [
        ev for ev in data.get("security_events", [])
        if ev.get("detections", {}).get("pii", {}).get("detected", False)
    ]
    return {
        "bot_id":              data.get("bot_id", DEFAULT_BOT_ID),
        "thread_id":           thread_id,
        "pii_detection_count": len(pii_events),
        "pii_events":          pii_events,
    }


@router.get("/{thread_id}")
async def get_thread_security_log(thread_id: str):
    """Read the full security log for a specific thread."""
    data = _get_log_or_404(thread_id)
    return {"success": True, "log": data, "timestamp": now()}


@router.delete("/{thread_id}")
async def delete_thread_security_log(thread_id: str):
    """Delete the local security log for a thread."""
    log_path = SECURITY_STORAGE_DIR / f"{thread_id}.json"
    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for thread_id: {thread_id}",
        )
    log_path.unlink()
    return {"success": True, "message": f"Deleted security log for thread_id: {thread_id}", "timestamp": now()}
