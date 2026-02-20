"""
Chat Routes — Direct mode scans+LLM inline, Via MongoDB mode stores only.
"""
import asyncio, logging, time, uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from config import MONGODB_CONVERSATIONS_COLLECTION, AZURE_DEPLOYMENT
from datetime_utils import now
from llm_client import call_llm
from mongodb_storage import get_mongodb
from security_scanner import ConcurrentSecurityScanner
from storage import append_security_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Chat"])
_scanner = ConcurrentSecurityScanner()

BLOCKED_RESPONSES = {
    "injection": "I'm here to help, but I can't process that kind of request. Could you rephrase what you're looking for?",
    "toxicity":  "I'd love to help! Let's keep things respectful — feel free to ask me anything in a friendly way.",
    "secrets":   "Your message contains sensitive credentials. Please remove them and try again.",
    "default":   "I'm not able to respond to that. Please try rephrasing your question.",
}

# ── Session-based conversation tracking ──────────────────────────────────────
# A new conv_id is issued when a bot is silent for longer than this threshold.
CONVERSATION_TIMEOUT_MINUTES = 30

_conv_state: dict = {}  # bot_id -> {"conv_id": str, "last_seen": float}

def _get_or_create_conv_id(bot_id: str) -> str:
    """
    Return the current conv_id for this bot, or create a new one if:
      - this bot has never sent a message, OR
      - the last message was more than CONVERSATION_TIMEOUT_MINUTES ago
    """
    now_ts = time.time()
    state  = _conv_state.get(bot_id)

    if state is None or (now_ts - state["last_seen"]) > CONVERSATION_TIMEOUT_MINUTES * 60:
        new_conv_id = f"conv_{bot_id}_{int(now_ts * 1000)}_{uuid.uuid4().hex[:6]}"
        _conv_state[bot_id] = {"conv_id": new_conv_id, "last_seen": now_ts}
        logger.info(f"[conv] New conversation for bot={bot_id!r}: {new_conv_id}")
    else:
        _conv_state[bot_id]["last_seen"] = now_ts  # refresh activity
        logger.debug(f"[conv] Continuing conversation for bot={bot_id!r}: {state['conv_id']}")

    return _conv_state[bot_id]["conv_id"]


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10_000)
    bot_id: str = Field(...)
    model:  str = Field(default=AZURE_DEPLOYMENT)
    @validator("prompt")
    def strip_prompt(cls, v):
        v = v.strip()
        if not v: raise ValueError("prompt cannot be blank")
        return v

class TestChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10_000)
    bot_id: str = Field(...)
    model:  str = Field(default=AZURE_DEPLOYMENT)
    @validator("prompt")
    def strip_prompt(cls, v):
        v = v.strip()
        if not v: raise ValueError("prompt cannot be blank")
        return v

def _derive_ids(bot_id):
    # Always derive from bot_id only — same bot = same thread across all messages
    suffix = bot_id.split("_")[1] if "_" in bot_id else bot_id
    return f"thread_{suffix}", f"user_{suffix}"

async def _run_scan(prompt, bot_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scanner.scan_prompt_parallel, prompt, bot_id)


def _store_security_event(
    message_id, thread_id, conv_id, request, ts,
    scan_results, detections, pii_data,
    has_pii, has_injection, has_toxicity, has_secrets,
    is_blocked, llm_response,
):
    """Store a direct-mode scan result into security_logs/{bot_id}.json."""
    security_event = {
        "message_id":        message_id,
        "thread_id":         thread_id,
        "conversation_id":   conv_id,
        "bot_id":            request.bot_id,
        "timestamp":         ts,
        "prompt":            request.prompt,
        "prompt_length":     len(request.prompt),
        "anonymized_prompt": pii_data.get("anonymized_prompt") if has_pii else None,
        "llm_response":      llm_response,
        "detections":        detections,
        "risk_level":        scan_results.risk_level,
        "is_safe":           scan_results.is_safe,
        "blocked":           is_blocked,
        "block_reason":      scan_results.message if is_blocked else None,
        "scan_duration":     round(scan_results.scan_duration, 4),
        "metrics":           {"scan_time": round(scan_results.scan_duration, 4)},
    }
    appended = append_security_event(
        bot_id=request.bot_id, message_id=message_id,
        security_event=security_event,
        is_blocked=is_blocked, has_pii=has_pii,
        has_jailbreak=has_injection, has_toxicity=has_toxicity,
        has_secrets=has_secrets,
    )
    if appended:
        logger.info(f"[test-chat] Stored security event for msg={message_id}")
    else:
        logger.warning(f"[test-chat] Duplicate skipped for msg={message_id}")


@router.post("/test-chat")
async def test_chat(request: TestChatRequest):
    """Direct mode — scan first, LLM if safe, respond immediately."""
    try:
        ts_ms      = int(time.time() * 1000)
        message_id = f"msg_user_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:6]}"
        conv_id    = _get_or_create_conv_id(request.bot_id)
        thread_id, user_id = _derive_ids(request.bot_id)
        ts = now()

        scan_results  = await _run_scan(request.prompt, request.bot_id)
        detections    = scan_results.detections
        has_injection = detections.get("prompt_injection", {}).get("detected", False)
        has_toxicity  = detections.get("toxicity", {}).get("detected", False)
        pii_data      = detections.get("pii", {})
        has_pii       = bool(pii_data.get("entities", []))
        has_secrets   = pii_data.get("secrets_detected", False)

        logger.info(f"[test-chat] scan={scan_results.risk_level} injection={has_injection} toxicity={has_toxicity} pii={has_pii} secrets={has_secrets}")

        if not scan_results.is_safe and (has_injection or has_toxicity or has_secrets):
            reply = BLOCKED_RESPONSES["secrets" if has_secrets else "injection" if has_injection else "toxicity"]
            logger.warning(f"[test-chat] BLOCKED bot={request.bot_id!r}")
            _store_security_event(
                message_id=message_id, thread_id=thread_id, conv_id=conv_id,
                request=request, ts=ts, scan_results=scan_results,
                detections=detections, pii_data=pii_data,
                has_pii=has_pii, has_injection=has_injection,
                has_toxicity=has_toxicity, has_secrets=has_secrets,
                is_blocked=True, llm_response=None,
            )
            return {"success": True, "response": reply, "message_id": message_id,
                    "conversation_id": conv_id, "model": request.model, "usage": {},
                    "security": {"is_safe": False, "blocked": True, "risk_level": scan_results.risk_level,
                                 "scan_duration": round(scan_results.scan_duration, 4), "detections": detections},
                    "timestamp": ts}

        prompt_for_llm = pii_data.get("anonymized_prompt") or request.prompt if has_pii else request.prompt
        raw = await call_llm(prompt_for_llm, model=request.model, has_pii=has_pii)
        assistant_message = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"[test-chat] LLM responded for bot={request.bot_id!r}")

        _store_security_event(
            message_id=message_id, thread_id=thread_id, conv_id=conv_id,
            request=request, ts=ts, scan_results=scan_results,
            detections=detections, pii_data=pii_data,
            has_pii=has_pii, has_injection=has_injection,
            has_toxicity=has_toxicity, has_secrets=has_secrets,
            is_blocked=False, llm_response=assistant_message,
        )
        return {"success": True, "response": assistant_message, "message_id": message_id,
                "conversation_id": conv_id, "model": request.model, "usage": raw.get("usage", {}),
                "security": {"is_safe": scan_results.is_safe, "blocked": False, "risk_level": scan_results.risk_level,
                             "pii_detected": has_pii, "scan_duration": round(scan_results.scan_duration, 4),
                             "detections": detections},
                "timestamp": ts}

    except HTTPException: raise
    except Exception as exc:
        logger.error(f"[test-chat] Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/chat/result/{message_id}")
async def get_chat_result(message_id: str, bot_id: str):
    """Poll for the LLM response after Via MongoDB mode stores a message."""
    import json
    from config import SECURITY_STORAGE_DIR
    log_path = SECURITY_STORAGE_DIR / f"{bot_id}.json"

    if not log_path.exists():
        return {"status": "pending", "message_id": message_id}
    try:
        with open(log_path) as f:
            log = json.load(f)
    except Exception:
        return {"status": "pending", "message_id": message_id}

    for event in log.get("security_events", []):
        if event.get("message_id") == message_id:
            if event.get("blocked"):
                det = event.get("detections", {})
                key = ("toxicity" if det.get("toxicity", {}).get("detected")
                       else "injection" if det.get("prompt_injection", {}).get("detected")
                       else "secrets" if det.get("pii", {}).get("secrets_detected")
                       else "default")
                return {"status": "blocked", "message_id": message_id,
                        "response": BLOCKED_RESPONSES.get(key, BLOCKED_RESPONSES["default"]),
                        "security": event}
            llm_response = event.get("llm_response")
            if llm_response:
                return {"status": "ready", "message_id": message_id, "response": llm_response, "security": event}
            return {"status": "scanning", "message_id": message_id}

    return {"status": "pending", "message_id": message_id}


@router.post("/chat")
async def chat(request: ChatRequest):
    """Via MongoDB mode — store only, monitor handles scan + LLM."""
    try:
        ts_ms      = int(time.time() * 1000)
        message_id = f"msg_user_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:6]}"
        conv_id    = _get_or_create_conv_id(request.bot_id)
        thread_id, user_id = _derive_ids(request.bot_id)
        ts = now()

        db = get_mongodb()
        if db is None:
            raise HTTPException(status_code=503, detail="MongoDB not connected")

        db[MONGODB_CONVERSATIONS_COLLECTION].insert_one({
            "messageId": message_id, "botId": request.bot_id,
            "threadId": thread_id, "conversationId": conv_id,
            "userId": user_id, "from": {"role": "user", "id": user_id},
            "activity": {"role": "user", "text": request.prompt, "timestamp": ts},
            "model": request.model, "processed": False,
            "source": "chat", "createdAt": ts, "updatedAt": ts,
        })
        logger.info(f"[chat] Stored {message_id} — monitor will scan + call LLM")

        return {"success": True, "message": "Message stored. Monitor will scan and call LLM if safe.",
                "message_id": message_id, "conversation_id": conv_id,
                "thread_id": thread_id, "bot_id": request.bot_id, "timestamp": ts}

    except HTTPException: raise
    except Exception as exc:
        logger.error(f"[chat] Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))