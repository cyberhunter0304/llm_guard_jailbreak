"""
Chat Routes — ULTRA-OPTIMIZED FOR 3s TOTAL TIME
Uses truly async background tasks (no blocking)
"""
import asyncio
import logging
import time
import uuid
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, validator
from config import MONGODB_CONVERSATIONS_COLLECTION, AZURE_DEPLOYMENT, DEFAULT_BOT_ID
from datetime_utils import now
from llm_client import call_llm
from mongodb_storage import get_mongodb
from security_scanner import ConcurrentSecurityScanner
from async_background_tasks import store_security_event_async

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Chat"])
_scanner = ConcurrentSecurityScanner()

BLOCKED_RESPONSES = {
    "injection": "I'm here to help, but I can't process that kind of request. Could you rephrase what you're looking for?",
    "toxicity":  "I'd love to help! Let's keep things respectful — feel free to ask me anything in a friendly way.",
    "secrets":   "Your message contains sensitive credentials. Please remove them and try again.",
    "default":   "I'm not able to respond to that. Please try rephrasing your question.",
}

# Session-based conversation tracking
CONVERSATION_TIMEOUT_MINUTES = 30
_conv_state: dict = {}

def _get_or_create_conv_id(bot_id: str) -> str:
    """Return current conv_id or create new one if timeout exceeded"""
    now_ts = time.time()
    state = _conv_state.get(bot_id)

    if state is None or (now_ts - state["last_seen"]) > CONVERSATION_TIMEOUT_MINUTES * 60:
        new_conv_id = f"conv_{bot_id}_{int(now_ts * 1000)}_{uuid.uuid4().hex[:6]}"
        _conv_state[bot_id] = {"conv_id": new_conv_id, "last_seen": now_ts}
        logger.info(f"[conv] New conversation: {new_conv_id}")
    else:
        _conv_state[bot_id]["last_seen"] = now_ts

    return _conv_state[bot_id]["conv_id"]


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10_000)
    bot_id: str = Field(...)
    model: str = Field(default=AZURE_DEPLOYMENT)
    
    @validator("prompt")
    def strip_prompt(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("prompt cannot be blank")
        return v


class TestChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10_000)
    bot_id: str = Field(...)
    model: str = Field(default=AZURE_DEPLOYMENT)
    
    @validator("prompt")
    def strip_prompt(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("prompt cannot be blank")
        return v


def _derive_ids(bot_id: str):
    """Derive thread and user IDs from bot_id"""
    suffix = bot_id.split("_")[1] if "_" in bot_id else bot_id
    return f"thread_{suffix}", f"user_{suffix}"


@router.post("/test-chat")
async def test_chat(request: TestChatRequest, background_tasks: BackgroundTasks):
    """
    ⚡ ULTRA-OPTIMIZED CHAT ENDPOINT (3s TOTAL)
    
    Performance optimizations:
    1. Async parallel scanning (0.5-1.0s saved)
    2. Truly async background I/O (no blocking)
    3. Early exit on threats (0.3-0.8s saved)
    
    Expected time:
    - Scan: 1-2s
    - LLM: 1-2s
    - Background task: 0s (truly non-blocking!)
    - TOTAL: ~3s ✅
    """
    try:
        ts_ms = int(time.time() * 1000)
        message_id = f"msg_user_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:6]}"
        conv_id = _get_or_create_conv_id(request.bot_id)
        thread_id, user_id = _derive_ids(request.bot_id)
        ts = now()

        # ======================================================================
        # ⚡ STEP 1: PARALLEL ASYNC SCANNING (1-2s)
        # ======================================================================
        scan_start = time.time()
        scan_results = await _scanner.scan_prompt(request.prompt, request.bot_id)
        scan_time = time.time() - scan_start
        logger.info(f"[test-chat] ⚡ Async scan: {scan_time:.3f}s")

        detections = scan_results.detections
        has_injection = detections.get("prompt_injection", {}).get("detected", False)
        has_toxicity = detections.get("toxicity", {}).get("detected", False)
        pii_data = detections.get("pii", {})
        has_pii = bool(pii_data.get("entities", []))
        has_secrets = pii_data.get("secrets_detected", False)

        logger.info(
            f"[test-chat] Results: injection={has_injection} toxicity={has_toxicity} "
            f"pii={has_pii} secrets={has_secrets}"
        )

        # ======================================================================
        # BLOCKED: Return immediately, store in background (truly async!)
        # ======================================================================
        if not scan_results.is_safe and (has_injection or has_toxicity or has_secrets):
            reply = BLOCKED_RESPONSES[
                "secrets" if has_secrets else "injection" if has_injection else "toxicity"
            ]
            logger.warning(f"[test-chat] 🚫 BLOCKED: {scan_results.risk_level}")
            
            # Build security event
            security_event = {
                "message_id": message_id,
                "thread_id": thread_id,
                "conversation_id": conv_id,
                "bot_id": DEFAULT_BOT_ID,
                "timestamp": ts,
                "prompt": request.prompt,
                "prompt_length": len(request.prompt),
                "anonymized_prompt": None,
                "llm_response": None,
                "detections": detections,
                "risk_level": scan_results.risk_level,
                "is_safe": scan_results.is_safe,
                "blocked": True,
                "block_reason": scan_results.message,
                "scan_duration": round(scan_results.scan_duration, 4),
                "metrics": {"scan_time": round(scan_results.scan_duration, 4)},
            }
            
            # ================================================================
            # ⚡ TRULY ASYNC: Store in background (doesn't block response!)
            # Uses loop.run_in_executor() for file I/O
            # ================================================================
            background_tasks.add_task(
                asyncio.run,
                store_security_event_async(
                    thread_id=thread_id,
                    message_id=message_id,
                    security_event=security_event,
                    is_blocked=True,
                    has_pii=has_pii,
                    has_jailbreak=has_injection,
                    has_toxicity=has_toxicity,
                    has_secrets=has_secrets,
                    bot_id=DEFAULT_BOT_ID,
                )
            )
            # ================================================================
            
            # Return IMMEDIATELY (file write happens in background, doesn't block!)
            return {
                "success": True,
                "response": reply,
                "message_id": message_id,
                "conversation_id": conv_id,
                "model": request.model,
                "usage": {},
                "security": {
                    "is_safe": False,
                    "blocked": True,
                    "risk_level": scan_results.risk_level,
                    "scan_duration": round(scan_results.scan_duration, 4),
                    "detections": detections,
                },
                "timestamp": ts,
            }

        # ======================================================================
        # ⚡ STEP 2: CALL LLM (1-2s)
        # ======================================================================
        prompt_for_llm = (
            pii_data.get("anonymized_prompt") if has_pii else request.prompt
        )
        
        llm_start = time.time()
        raw = await call_llm(prompt_for_llm, model=request.model, has_pii=has_pii)
        llm_time = time.time() - llm_start
        logger.info(f"[test-chat] LLM response: {llm_time:.3f}s")
        
        assistant_message = raw.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Build security event
        security_event = {
            "message_id": message_id,
            "thread_id": thread_id,
            "conversation_id": conv_id,
            "bot_id": DEFAULT_BOT_ID,
            "timestamp": ts,
            "prompt": request.prompt,
            "prompt_length": len(request.prompt),
            "anonymized_prompt": pii_data.get("anonymized_prompt") if has_pii else None,
            "llm_response": assistant_message,
            "detections": detections,
            "risk_level": scan_results.risk_level,
            "is_safe": scan_results.is_safe,
            "blocked": False,
            "block_reason": None,
            "scan_duration": round(scan_results.scan_duration, 4),
            "metrics": {"scan_time": round(scan_results.scan_duration, 4)},
        }

        # ================================================================
        # ⚡ TRULY ASYNC: Store in background (doesn't block response!)
        # ================================================================
        background_tasks.add_task(
            asyncio.run,
            store_security_event_async(
                thread_id=thread_id,
                message_id=message_id,
                security_event=security_event,
                is_blocked=False,
                has_pii=has_pii,
                has_jailbreak=has_injection,
                has_toxicity=has_toxicity,
                has_secrets=has_secrets,
                bot_id=DEFAULT_BOT_ID,
            )
        )
        # ================================================================

        total_time = time.time() - scan_start
        logger.info(f"[test-chat] ✅ Complete: scan={scan_time:.3f}s + llm={llm_time:.3f}s = {total_time:.3f}s")

        # Return IMMEDIATELY (response sent before background task completes)
        return {
            "success": True,
            "response": assistant_message,
            "message_id": message_id,
            "conversation_id": conv_id,
            "model": request.model,
            "usage": raw.get("usage", {}),
            "security": {
                "is_safe": scan_results.is_safe,
                "blocked": False,
                "risk_level": scan_results.risk_level,
                "pii_detected": has_pii,
                "scan_duration": round(scan_results.scan_duration, 4),
                "detections": detections,
            },
            "timestamp": ts,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[test-chat] Error: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/chat/result/{message_id}")
async def get_chat_result(message_id: str, bot_id: str):
    """Poll for the LLM response after storing message"""
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
                key = (
                    "toxicity" if det.get("toxicity", {}).get("detected")
                    else "injection" if det.get("prompt_injection", {}).get("detected")
                    else "secrets" if det.get("pii", {}).get("secrets_detected")
                    else "default"
                )
                return {
                    "status": "blocked",
                    "message_id": message_id,
                    "response": BLOCKED_RESPONSES.get(key, BLOCKED_RESPONSES["default"]),
                    "security": event,
                }
            
            llm_response = event.get("llm_response")
            if llm_response:
                return {
                    "status": "ready",
                    "message_id": message_id,
                    "response": llm_response,
                    "security": event,
                }
            
            return {"status": "scanning", "message_id": message_id}

    return {"status": "pending", "message_id": message_id}


@router.post("/chat")
async def chat(request: ChatRequest):
    """Via MongoDB mode — store only, monitor handles scan + LLM"""
    try:
        ts_ms = int(time.time() * 1000)
        message_id = f"msg_user_{request.bot_id}_{ts_ms}_{uuid.uuid4().hex[:6]}"
        conv_id = _get_or_create_conv_id(request.bot_id)
        thread_id, user_id = _derive_ids(request.bot_id)
        ts = now()

        db = get_mongodb()
        if db is None:
            raise HTTPException(status_code=503, detail="MongoDB not connected")

        db[MONGODB_CONVERSATIONS_COLLECTION].insert_one({
            "messageId": message_id,
            "botId": request.bot_id,
            "threadId": thread_id,
            "conversationId": conv_id,
            "userId": user_id,
            "from": {"role": "user", "id": user_id},
            "activity": {"role": "user", "text": request.prompt, "timestamp": ts},
            "model": request.model,
            "processed": False,
            "source": "chat",
            "createdAt": ts,
            "updatedAt": ts,
        })
        logger.info(f"[chat] Stored {message_id} → monitor will scan async")

        return {
            "success": True,
            "message": "Message stored. Monitor will scan and call LLM if safe.",
            "message_id": message_id,
            "conversation_id": conv_id,
            "thread_id": thread_id,
            "bot_id": DEFAULT_BOT_ID,
            "timestamp": ts,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[chat] Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))