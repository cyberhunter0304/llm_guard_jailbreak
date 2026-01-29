from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import asyncio

# Local imports
from config import API_CONFIG, ALLOWED_ORIGINS, AVAILABLE_MODELS, LOG_LEVEL, OPENROUTER_API_KEY
from models import (
    ChatRequest, ScanRequest, ChatResponse, SecurityScanResult,
    HealthResponse, StatsResponse
)
from storage import (
    load_bot_security_log, save_bot_security_log,
    delete_bot_security_log, list_all_bot_sessions
)
from security_scanner import ConcurrentSecurityScanner, shutdown_scanner
from llm_client import call_openrouter
from datetime_utils import now

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(**API_CONFIG)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize security scanner
detector = ConcurrentSecurityScanner()


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="connected",
        service="Jailbreak-Protected LLM API (Concurrent Mode)",
        timestamp=now(),
        scanners_active=len(detector.scanners) + 1
    )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    tags=["Chat"]
)
async def chat(request: ChatRequest):
    """
    ⚡ CONCURRENT CHAT ENDPOINT ⚡
    Handles MULTIPLE BOTS simultaneously with thread-safe operations
    """
    try:
        request_start = time.time()
        
        # Load bot's security log (thread-safe)
        bot_security_log = load_bot_security_log(request.bot_id)
        bot_security_log["total_prompts"] += 1
        
        logger.info(f"[Bot: {request.bot_id[:16]}...] Processing prompt")
        
        # Run security scan in thread pool (concurrent-safe)
        loop = asyncio.get_event_loop()
        scan_results = await loop.run_in_executor(
            None,
            detector.scan_prompt_parallel, 
            request.prompt,
            request.bot_id
        )
        
        # Extract results
        pii_detection = scan_results.detections.get("pii", {})
        pii_entities = pii_detection.get("entities", [])
        anonymized_prompt = scan_results.detections.get("pii", {}).get("anonymized_prompt", request.prompt)
        
        # Prepare security event
        security_event = {
            "timestamp": now(),
            "prompt": request.prompt,
            "prompt_length": len(request.prompt),
            "detections": scan_results.detections,
            "risk_level": scan_results.risk_level,
            "is_safe": scan_results.is_safe,
            "scan_duration": scan_results.scan_duration,
            "blocked": False,
            "anonymized_prompt": anonymized_prompt if pii_entities else None,
            "llm_response": None
        }

        # Handle PII Detection
        if pii_entities:
            logger.info(f"[Bot: {request.bot_id[:16]}...] PII detected: {len(pii_entities)} entities")
            bot_security_log["pii_detections"] += 1
            prompt_to_send = anonymized_prompt
        else:
            prompt_to_send = request.prompt

        # Check for threats (BLOCK if detected)
        if not scan_results.is_safe:
            logger.warning(f"[Bot: {request.bot_id[:16]}...] Threat detected - {scan_results.risk_level}")
            
            bot_security_log["blocked_prompts"] += 1
            
            # 🔧 TRACK NEW SCANNER DETECTIONS:
            # Add counters to bot_security_log for new scanners
            # ====================================================================
            if scan_results.detections.get("prompt_injection", {}).get("detected"):
                bot_security_log["jailbreak_attempts"] += 1
            if scan_results.detections.get("toxicity", {}).get("detected"):
                bot_security_log["toxicity_detections"] += 1
            
            # Example for new scanners:
            # if scan_results.detections.get("secrets", {}).get("detected"):
            #     bot_security_log["secrets_detections"] += 1
            # if scan_results.detections.get("ban_topics", {}).get("detected"):
            #     bot_security_log["banned_topics_detections"] += 1
            # ====================================================================
            
            security_event["blocked"] = True
            security_event["block_reason"] = scan_results.message
            
            bot_security_log["security_events"].append(security_event)
            bot_security_log["last_updated"] = now()
            save_bot_security_log(request.bot_id, bot_security_log)
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "response": scan_results.message,
                    "security_scan": {
                        "is_safe": False,
                        "risk_level": scan_results.risk_level,
                        "message": scan_results.message,
                        "timestamp": scan_results.timestamp
                    },
                    "model": request.model,
                    "timestamp": now()
                }
            )
        
        # Prompt is safe - call LLM
        logger.info(f"[Bot: {request.bot_id[:16]}...] Safe - calling LLM")
        
        # Call OpenRouter (async for better concurrency)
        llm_response = await call_openrouter(prompt_to_send, request.model, has_pii=bool(pii_entities))
        
        assistant_message = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        security_event["llm_response"] = assistant_message
        security_event["model_used"] = request.model
        security_event["success"] = True
        
        bot_security_log["security_events"].append(security_event)
        bot_security_log["last_updated"] = now()
        save_bot_security_log(request.bot_id, bot_security_log)
        
        total_time = time.time() - request_start
        logger.info(f"[Bot: {request.bot_id[:16]}...] ✅ Completed in {total_time:.3f}s")
        
        return ChatResponse(
            success=True,
            response=assistant_message,
            security_scan=scan_results,
            model=request.model,
            usage=llm_response.get("usage", {}),
            timestamp=now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Bot: {request.bot_id[:16]}...] Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post(
    "/api/scan",
    response_model=SecurityScanResult,
    tags=["Security"]
)
async def scan_only(request: ScanRequest):
    """Scan prompt with all security checks - concurrent safe"""
    try:
        loop = asyncio.get_event_loop()
        scan_results = await loop.run_in_executor(
            None,
            detector.scan_prompt_parallel,
            request.prompt,
            "scan-only"
        )
        return scan_results
        
    except Exception as e:
        logger.error(f"Scan error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@app.get("/api/security/{bot_id}", tags=["Security Logs"])
async def get_bot_security_log(bot_id: str):
    """Retrieve complete security log for a specific bot session"""
    try:
        security_data = load_bot_security_log(bot_id)
        if not security_data.get("security_events"):
            return {
                "bot_id": bot_id,
                "message": "No security events found for this bot session",
                "security_events": []
            }
        return security_data
    except Exception as e:
        logger.error(f"Failed to retrieve security log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security log: {str(e)}"
        )


@app.get("/api/security/{bot_id}/summary", tags=["Security Logs"])
async def get_bot_security_summary(bot_id: str):
    """Get security summary for a bot session"""
    try:
        security_data = load_bot_security_log(bot_id)
        return {
            "bot_id": security_data.get("bot_id"),
            "created_at": security_data.get("created_at"),
            "last_updated": security_data.get("last_updated"),
            "statistics": {
                "total_prompts": security_data.get("total_prompts", 0),
                "blocked_prompts": security_data.get("blocked_prompts", 0),
                "pii_detections": security_data.get("pii_detections", 0),
                "jailbreak_attempts": security_data.get("jailbreak_attempts", 0),
                "toxicity_detections": security_data.get("toxicity_detections", 0),
                "total_events": len(security_data.get("security_events", []))
            }
        }
    except Exception as e:
        logger.error(f"Failed to retrieve security summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security summary: {str(e)}"
        )


@app.get("/api/security/{bot_id}/pii", tags=["Security Logs"])
async def get_bot_pii_only(bot_id: str):
    """Retrieve only PII detections for a specific bot session"""
    try:
        security_data = load_bot_security_log(bot_id)
        pii_events = [
            event for event in security_data.get("security_events", [])
            if event.get("detections", {}).get("pii", {}).get("detected", False)
        ]
        return {
            "bot_id": bot_id,
            "pii_detection_count": len(pii_events),
            "pii_events": pii_events
        }
    except Exception as e:
        logger.error(f"Failed to retrieve PII data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PII data: {str(e)}"
        )


@app.delete("/api/security/{bot_id}", tags=["Security Logs"])
async def delete_bot_log(bot_id: str):
    """Delete all security data for a specific bot session"""
    try:
        result = delete_bot_security_log(bot_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete security log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete security log: {str(e)}"
        )


@app.get("/api/security", tags=["Security Logs"])
async def list_bot_sessions():
    """List all bot sessions with security logs"""
    try:
        result = list_all_bot_sessions()
        return result
    except Exception as e:
        logger.error(f"Failed to list bot sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bot sessions: {str(e)}"
        )


@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """Get API statistics and configuration"""
    return StatsResponse(
        service="Jailbreak-Protected LLM API (Concurrent Mode)",
        version="2.0.0",
        scanners={
            "prompt_injection": {
                "name": "Prompt Injection Scanner",
                "threshold": 0.8,
                "description": "Detects prompt injection and jailbreak attempts",
                "concurrent_safe": True
            },
            "toxicity": {
                "name": "Toxicity Scanner",
                "threshold": 0.5,
                "description": "Detects toxic and harmful content",
                "concurrent_safe": True
            },
            "pii": {
                "name": "PII Detection & Anonymization",
                "threshold": 0.5,
                "description": "Detects and anonymizes personal information",
                "concurrent_safe": True
            }
            # 🔧 ADD NEW SCANNER INFO FOR API STATS:
            # Document your new scanners in the /api/stats endpoint
            # ================================================================
            # "secrets": {
            #     "name": "Secrets Scanner",
            #     "threshold": 0.0,
            #     "description": "Detects API keys, passwords, and tokens",
            #     "concurrent_safe": True
            # },
            # "ban_topics": {
            #     "name": "Banned Topics Scanner",
            #     "threshold": 0.7,
            #     "description": "Blocks specific prohibited topics",
            #     "concurrent_safe": True
            # }
            # ================================================================
        },
        models_available=AVAILABLE_MODELS
    )


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 80)
    logger.info("🚀 Starting Jailbreak-Protected LLM API - ⚡ CONCURRENT MODE ⚡")
    logger.info("=" * 80)
    logger.info(f"✓ Loaded 3 security scanners (Prompt Injection, Toxicity, PII)")
    logger.info("✓ Thread-safe PII scanner with isolated instances")
    logger.info("✓ File operations protected with locks")
    logger.info("✓ READY FOR CONCURRENT BOT SIMULATION")
    logger.info("=" * 80)
    logger.info("⚡ Can handle 50+ bots simultaneously! ⚡")
    logger.info("=" * 80 + "\n")
    
    if not OPENROUTER_API_KEY:
        logger.warning("⚠️  OPENROUTER_API_KEY not set! Set it as environment variable.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    shutdown_scanner()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        workers=1
    )
