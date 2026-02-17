from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
import time
import asyncio
import json

# Local imports
from config import API_CONFIG, ALLOWED_ORIGINS, AVAILABLE_MODELS, LOG_LEVEL, OPENROUTER_API_KEY

# MongoDB collection names - with backward compatibility
try:
    from config import MONGODB_SECURITY_LOGS_COLLECTION, MONGODB_CONVERSATIONS_COLLECTION, MONGODB_THREAD_SUMMARIES_COLLECTION
except ImportError:
    # Fallback for older config.py files
    MONGODB_SECURITY_LOGS_COLLECTION = "security_logs"
    MONGODB_CONVERSATIONS_COLLECTION = "conversations"
    MONGODB_THREAD_SUMMARIES_COLLECTION = "thread_summaries"
    print("⚠️  Warning: Using default MongoDB collection names. Consider updating config.py")
from models import (
    ChatRequest, ScanRequest, ChatResponse, SecurityScanResult,
    HealthResponse, StatsResponse
)
from mongodb_storage import (
    load_bot_security_log, save_bot_security_log,
    delete_bot_security_log, list_all_bot_sessions,
    connect_mongodb, close_mongodb,
    get_unprocessed_conversations, mark_conversation_processed,
    get_processing_stats, get_mongodb, save_conversation, build_conversation
)
from security_scanner import ConcurrentSecurityScanner, shutdown_scanner
from llm_client import call_openrouter
from datetime_utils import now
from realtime_monitor import get_monitor, shutdown_monitor
from pathlib import Path

# Import SECURITY_STORAGE_DIR with fallback
try:
    from config import SECURITY_STORAGE_DIR
except ImportError:
    SECURITY_STORAGE_DIR = Path("security_logs")
    SECURITY_STORAGE_DIR.mkdir(exist_ok=True)
    print("⚠️  Warning: Using default security_logs directory")

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


async def sse_event_generator(monitor):
    """Generate SSE-formatted events from monitor"""
    try:
        async for event in monitor.watch_and_process():
            event_type = event.get("event", "message")
            event_data = event.get("data", {})
            
            # Format as SSE
            sse_message = f"event: {event_type}\n"
            sse_message += f"data: {json.dumps(event_data)}\n\n"
            
            yield sse_message
            
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled")
        monitor.stop()
    except Exception as e:
        logger.error(f"SSE stream error: {str(e)}")
        error_event = f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
        yield error_event


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
            "llm_response": None,
            "metrics": {
                "request_start_time": request_start,
                "scan_time": round(scan_results.scan_duration, 4),
                "scanner_details": scan_results.detections.get("metrics", {}).get("scanner_times", {}),
                "llm_time": 0.0,
                "total_time": 0.0
            }
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
            
            # Track secrets from PII scanner results
            pii_results = scan_results.detections.get("pii", {})
            if pii_results.get("secrets_detected", False):
                bot_security_log["secrets_detections"] += 1
            
            # Example for new scanners:
            # if scan_results.detections.get("ban_topics", {}).get("detected"):
            #     bot_security_log["banned_topics_detections"] += 1
            # ====================================================================
            
            security_event["blocked"] = True
            security_event["block_reason"] = scan_results.message
            security_event["metrics"]["total_time"] = round(time.time() - request_start, 4)
            
            bot_security_log["security_events"].append(security_event)
            bot_security_log["last_updated"] = now()
            save_bot_security_log(request.bot_id, bot_security_log)
            
            # Save conversation to MongoDB
            conversation_data = {
                "conversationId": f"conv_{request.bot_id}_{int(time.time() * 1000)}",
                "botId": request.bot_id,
                "threadId": f"thread_{request.bot_id.split('_')[1]}" if "_" in request.bot_id else request.bot_id,
                "userId": f"user_{request.bot_id.split('_')[1]}" if "_" in request.bot_id else request.bot_id,
                "activity": {
                    "role": "user",
                    "text": request.prompt,
                    "timestamp": now()
                },
                "validation": {
                    "prompt": request.prompt,
                    "prompt_length": len(request.prompt),
                    "is_safe": False,
                    "blocked": True,
                    "message": scan_results.message,
                    "risk_level": scan_results.risk_level,
                    "detections": scan_results.detections,
                    "timestamp": now()
                },
                "model": request.model
            }
            save_conversation(conversation_data)
            
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
        
        # Track LLM call time
        llm_start = time.time()
        
        # Call OpenRouter (async for better concurrency)
        llm_response = await call_openrouter(prompt_to_send, request.model, has_pii=bool(pii_entities))
        
        llm_duration = time.time() - llm_start
        
        assistant_message = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        security_event["llm_response"] = assistant_message
        security_event["model_used"] = request.model
        security_event["success"] = True
        security_event["metrics"]["llm_time"] = round(llm_duration, 4)
        security_event["metrics"]["total_time"] = round(time.time() - request_start, 4)
        
        bot_security_log["security_events"].append(security_event)
        bot_security_log["last_updated"] = now()
        save_bot_security_log(request.bot_id, bot_security_log)
        
        # Save conversation to MongoDB (successful case)
        conversation_data = {
            "conversationId": f"conv_{request.bot_id}_{int(time.time() * 1000)}",
            "botId": request.bot_id,
            "threadId": f"thread_{request.bot_id.split('_')[1]}" if "_" in request.bot_id else request.bot_id,
            "userId": f"user_{request.bot_id.split('_')[1]}" if "_" in request.bot_id else request.bot_id,
            "activity": {
                "role": "user",
                "text": request.prompt,
                "timestamp": now()
            },
            "validation": {
                "prompt": request.prompt,
                "prompt_length": len(request.prompt),
                "llm_response": assistant_message,
                "is_safe": True,
                "blocked": False,
                "risk_level": scan_results.risk_level,
                "detections": scan_results.detections,
                "metrics": security_event["metrics"],
                "timestamp": now()
            },
            "model": request.model
        }
        save_conversation(conversation_data)
        
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
                "secrets_detections": security_data.get("secrets_detections", 0),
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
    """List all bot sessions with security logs from local folder"""
    try:
        sessions = []
        
        # Scan all thread directories in the local security_logs folder
        if SECURITY_STORAGE_DIR.exists():
            for thread_dir in sorted(SECURITY_STORAGE_DIR.iterdir()):
                if thread_dir.is_dir():
                    thread_id = thread_dir.name
                    conversations = []
                    
                    # Scan all conversation logs in this thread
                    for log_file in sorted(thread_dir.glob("*.json")):
                        try:
                            with open(log_file, 'r') as f:
                                log_data = json.load(f)
                                # Treat each log file as a conversation
                                conversations.append(log_data)
                        except Exception as e:
                            logger.warning(f"Could not read log file {log_file}: {str(e)}")
                    
                    # If we have conversations, include this thread
                    if conversations:
                        total_prompts = sum(conv.get("total_prompts", 0) for conv in conversations)
                        blocked_prompts = sum(conv.get("blocked_prompts", 0) for conv in conversations)
                        pii_detections = sum(conv.get("pii_detections", 0) for conv in conversations)
                        jailbreak_attempts = sum(conv.get("jailbreak_attempts", 0) for conv in conversations)
                        toxicity_detections = sum(conv.get("toxicity_detections", 0) for conv in conversations)
                        secrets_detections = sum(conv.get("secrets_detections", 0) for conv in conversations)
                        
                        sessions.append({
                            "thread_id": thread_id,
                            "bot_id": conversations[0].get("bot_id", ""),
                            "created_at": conversations[0].get("created_at", now()),
                            "last_updated": conversations[-1].get("last_updated", now()),
                            "conversations": conversations,
                            "total_prompts": total_prompts,
                            "blocked_prompts": blocked_prompts,
                            "pii_detections": pii_detections,
                            "jailbreak_attempts": jailbreak_attempts,
                            "toxicity_detections": toxicity_detections,
                            "secrets_detections": secrets_detections,
                            "conversation_count": len(conversations)
                        })
        
        logger.info(f"Retrieved {len(sessions)} sessions from local folder")
        
        return {
            "sessions": sessions,
            "timestamp": now()
        }
    except Exception as e:
        logger.error(f"Failed to list bot sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bot sessions: {str(e)}"
        )


# ============================================================================
# BATCH PROCESSING ENDPOINTS FOR CONVERSATION SECURITY SCANNING
# ============================================================================

@app.post("/api/batch/process-next", tags=["Batch Processing"])
async def process_next_conversation():
    """
    Process the next unprocessed conversation from MongoDB
    - Fetches one conversation from conversations collection
    - Scans it for security threats
    - Stores security log in security_logs collection
    - Marks conversation as processed
    Returns immediately after processing one conversation
    """
    try:
        # Get next unprocessed conversation
        conversations = get_unprocessed_conversations(limit=1)
        
        if not conversations:
            return {
                "success": False,
                "message": "No more conversations to process",
                "processed": False
            }
        
        conversation = conversations[0]
        conversation_id = conversation.get("_id") or conversation.get("conversationId", "unknown")
        
        # Extract message from activity.text field (your MongoDB structure)
        prompt = conversation.get("activity", {}).get("text", "")
        
        # If no activity.text, try other common fields
        if not prompt:
            prompt = conversation.get("message", conversation.get("prompt", ""))
        
        logger.info(f"Processing conversation: {conversation_id}")
        
        # Create bot_id from conversation_id
        bot_id = f"batch_processing_{conversation_id}"
        
        request_start = time.time()
        
        # Load or create security log for this batch
        bot_security_log = load_bot_security_log(bot_id)
        bot_security_log["total_prompts"] += 1
        bot_security_log["conversation_id"] = str(conversation_id)
        
        # Run security scan
        loop = asyncio.get_event_loop()
        scan_results = await loop.run_in_executor(
            None,
            detector.scan_prompt_parallel,
            prompt,
            bot_id
        )
        
        # Extract PII detection results
        pii_detection = scan_results.detections.get("pii", {})
        pii_entities = pii_detection.get("entities", [])
        anonymized_prompt = pii_detection.get("anonymized_prompt", prompt)
        
        # Create security event
        security_event = {
            "timestamp": now(),
            "prompt": prompt,
            "prompt_length": len(prompt),
            "detections": scan_results.detections,
            "risk_level": scan_results.risk_level,
            "is_safe": scan_results.is_safe,
            "scan_duration": scan_results.scan_duration,
            "blocked": False,
            "anonymized_prompt": anonymized_prompt if pii_entities else None,
            "metrics": {
                "request_start_time": request_start,
                "scan_time": round(scan_results.scan_duration, 4),
                "total_time": round(time.time() - request_start, 4)
            }
        }
        
        # Update counters if threats detected
        if not scan_results.is_safe:
            bot_security_log["blocked_prompts"] += 1
            security_event["blocked"] = True
            security_event["block_reason"] = scan_results.message
            
            if scan_results.detections.get("prompt_injection", {}).get("detected"):
                bot_security_log["jailbreak_attempts"] += 1
            if scan_results.detections.get("toxicity", {}).get("detected"):
                bot_security_log["toxicity_detections"] += 1
        
        # Update PII counter
        if pii_entities:
            bot_security_log["pii_detections"] += 1
        
        # Add event to log and save to MongoDB
        bot_security_log["security_events"].append(security_event)
        bot_security_log["last_updated"] = now()
        save_bot_security_log(bot_id, bot_security_log)
        
        # Mark conversation as processed with reference to security log
        mark_conversation_processed(conversation_id, bot_id)
        
        # Get current processing stats
        stats = get_processing_stats()
        
        logger.info(f"✅ Processed conversation {conversation_id} - Safe: {scan_results.is_safe}")
        
        return {
            "success": True,
            "processed": True,
            "conversation_id": str(conversation_id),
            "security_log_id": bot_id,
            "scan_results": {
                "is_safe": scan_results.is_safe,
                "risk_level": scan_results.risk_level,
                "pii_detected": bool(pii_entities),
                "threat_detected": not scan_results.is_safe,
                "scan_duration": round(scan_results.scan_duration, 4),
                "message": scan_results.message
            },
            "processing_stats": stats,
            "timestamp": now()
        }
        
    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing conversation: {str(e)}"
        )


@app.get("/api/batch/status", tags=["Batch Processing"])
async def get_batch_processing_status():
    """Get current batch processing status and statistics"""
    try:
        stats = get_processing_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": now()
        }
    except Exception as e:
        logger.error(f"Error getting batch stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting batch stats: {str(e)}"
        )


@app.post("/api/batch/process-bulk", tags=["Batch Processing"])
async def process_bulk_conversations(count: int = 10):
    """
    Process multiple conversations in sequence
    - Processes 'count' conversations one by one
    - Each is immediately saved to MongoDB
    - Returns summary of all processed conversations
    """
    try:
        results = []
        
        for i in range(count):
            conversations = get_unprocessed_conversations(limit=1)
            
            if not conversations:
                logger.info(f"Processed {i} conversations - no more data")
                break
            
            conversation = conversations[0]
            conversation_id = conversation.get("_id") or conversation.get("conversationId", "unknown")
            
            # Extract message from activity.text field (your MongoDB structure)
            prompt = conversation.get("activity", {}).get("text", "")
            
            # If no activity.text, try other common fields
            if not prompt:
                prompt = conversation.get("message", conversation.get("prompt", ""))
            
            logger.info(f"({i+1}/{count}) Processing: {conversation_id}")
            
            bot_id = f"batch_processing_{conversation_id}"
            request_start = time.time()
            
            # Load or create security log
            bot_security_log = load_bot_security_log(bot_id)
            bot_security_log["total_prompts"] += 1
            bot_security_log["conversation_id"] = str(conversation_id)
            
            # Run security scan
            loop = asyncio.get_event_loop()
            scan_results = await loop.run_in_executor(
                None,
                detector.scan_prompt_parallel,
                prompt,
                bot_id
            )
            
            # Extract results
            pii_detection = scan_results.detections.get("pii", {})
            pii_entities = pii_detection.get("entities", [])
            anonymized_prompt = pii_detection.get("anonymized_prompt", prompt)
            
            # Create security event
            security_event = {
                "timestamp": now(),
                "prompt": prompt,
                "prompt_length": len(prompt),
                "detections": scan_results.detections,
                "risk_level": scan_results.risk_level,
                "is_safe": scan_results.is_safe,
                "scan_duration": scan_results.scan_duration,
                "blocked": False,
                "anonymized_prompt": anonymized_prompt if pii_entities else None,
                "metrics": {
                    "request_start_time": request_start,
                    "scan_time": round(scan_results.scan_duration, 4),
                    "total_time": round(time.time() - request_start, 4)
                }
            }
            
            # Update counters
            if not scan_results.is_safe:
                bot_security_log["blocked_prompts"] += 1
                security_event["blocked"] = True
                security_event["block_reason"] = scan_results.message
                
                if scan_results.detections.get("prompt_injection", {}).get("detected"):
                    bot_security_log["jailbreak_attempts"] += 1
                if scan_results.detections.get("toxicity", {}).get("detected"):
                    bot_security_log["toxicity_detections"] += 1
            
            if pii_entities:
                bot_security_log["pii_detections"] += 1
            
            # Save to MongoDB immediately
            bot_security_log["security_events"].append(security_event)
            bot_security_log["last_updated"] = now()
            save_bot_security_log(bot_id, bot_security_log)
            
            # Mark as processed
            mark_conversation_processed(conversation_id, bot_id)
            
            results.append({
                "conversation_id": str(conversation_id),
                "is_safe": scan_results.is_safe,
                "risk_level": scan_results.risk_level,
                "scan_duration": round(scan_results.scan_duration, 4)
            })
        
        stats = get_processing_stats()
        
        logger.info(f"✅ Batch processing complete - {len(results)} conversations processed")
        
        return {
            "success": True,
            "count_processed": len(results),
            "results": results,
            "processing_stats": stats,
            "timestamp": now()
        }
        
    except Exception as e:
        logger.error(f"Error in bulk processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk processing: {str(e)}"
        )



# ============================================================================
# SECURITY LOGS ENDPOINTS - Thread and Conversation Management
# ============================================================================

@app.get("/api/security-logs", tags=["Security Logs"])
async def get_all_threads(
    bot_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Get all security log threads (users)
    
    This reads from the local 'security_logs' folder in the backend.
    
    Query Parameters:
    - bot_id: Filter by specific bot ID (optional)
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100)
    """
    try:
        threads = []
        
        # Scan all thread directories in the local security_logs folder
        if SECURITY_STORAGE_DIR.exists():
            for thread_dir in sorted(SECURITY_STORAGE_DIR.iterdir()):
                if thread_dir.is_dir():
                    thread_logs = []
                    
                    # Scan all conversation logs in this thread
                    for log_file in sorted(thread_dir.glob("*.json")):
                        try:
                            with open(log_file, 'r') as f:
                                log_data = json.load(f)
                                log_data["_id"] = str(log_file.stem)
                                thread_logs.append(log_data)
                        except Exception as e:
                            logger.warning(f"Could not read log file {log_file}: {str(e)}")
                    
                    # If we have logs and bot_id filter matches (or no filter), include thread
                    if thread_logs:
                        thread_bot_id = thread_logs[0].get("bot_id", "")
                        if bot_id is None or bot_id == thread_bot_id:
                            threads.append({
                                "thread_id": thread_dir.name,
                                "bot_id": thread_bot_id,
                                "logs": thread_logs,
                                "last_updated": thread_logs[-1].get("last_updated", now()),
                                "total_logs": len(thread_logs)
                            })
        
        # Sort by last_updated descending
        threads = sorted(threads, key=lambda x: x.get("last_updated", ""), reverse=True)
        
        # Apply pagination
        total = len(threads)
        paginated_threads = threads[skip:skip + limit]
        
        logger.info(f"Retrieved {len(paginated_threads)} threads from local folder (total: {total})")
        
        return {
            "threads": paginated_threads,
            "total": total,
            "skip": skip,
            "limit": limit,
            "timestamp": now()
        }
    
    except Exception as e:
        logger.error(f"Error fetching threads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching threads: {str(e)}"
        )


@app.get("/api/security-logs/{thread_id}", tags=["Security Logs"])
async def get_thread_details(thread_id: str):
    """
    Get detailed information for a specific thread
    
    Returns complete thread document with all conversations and security events
    """
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        thread_summaries = db[MONGODB_THREAD_SUMMARIES_COLLECTION]
        thread = thread_summaries.find_one({"thread_id": thread_id})
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread {thread_id} not found"
            )
        
        # Convert ObjectId to string
        thread["_id"] = str(thread["_id"])
        
        logger.info(f"Retrieved thread: {thread_id}")
        
        return thread
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching thread {thread_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching thread: {str(e)}"
        )


@app.get("/api/security-logs/{thread_id}/conversations/{conversation_id}", tags=["Security Logs"])
async def get_conversation_details(thread_id: str, conversation_id: str):
    """
    Get details for a specific conversation within a thread
    """
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        thread_summaries = db[MONGODB_THREAD_SUMMARIES_COLLECTION]
        thread = thread_summaries.find_one(
            {"thread_id": thread_id},
            {"conversations": {"$elemMatch": {"conversation_id": conversation_id}}}
        )
        
        if not thread or "conversations" not in thread or len(thread["conversations"]) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found in thread {thread_id}"
            )
        
        logger.info(f"Retrieved conversation: {conversation_id} from thread: {thread_id}")
        
        return thread["conversations"][0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching conversation: {str(e)}"
        )


@app.delete("/api/security-logs/{thread_id}", tags=["Security Logs"])
async def delete_thread(thread_id: str):
    """
    Delete a specific thread
    """
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        thread_summaries = db[MONGODB_THREAD_SUMMARIES_COLLECTION]
        result = thread_summaries.delete_one({"thread_id": thread_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread {thread_id} not found"
            )
        
        logger.info(f"Deleted thread: {thread_id}")
        
        return {
            "deleted": True,
            "thread_id": thread_id,
            "timestamp": now()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting thread: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting thread: {str(e)}"
        )


@app.get("/api/security-logs/stats/summary", tags=["Security Logs"])
async def get_threads_statistics(bot_id: Optional[str] = None):
    """
    Get aggregate statistics across all threads
    
    Reads from local security_logs folder
    
    Query Parameters:
    - bot_id: Filter by specific bot ID (optional)
    """
    try:
        total_threads = 0
        total_conversations = 0
        total_prompts = 0
        total_blocked = 0
        total_pii = 0
        total_secrets = 0
        total_jailbreaks = 0
        total_toxicity = 0
        
        # Scan all thread directories
        if SECURITY_STORAGE_DIR.exists():
            for thread_dir in SECURITY_STORAGE_DIR.iterdir():
                if thread_dir.is_dir():
                    total_threads += 1
                    
                    # Scan all conversation logs in this thread
                    for log_file in thread_dir.glob("*.json"):
                        try:
                            with open(log_file, 'r') as f:
                                log_data = json.load(f)
                                
                                # Check bot_id filter
                                if bot_id and log_data.get("bot_id") != bot_id:
                                    continue
                                
                                total_conversations += 1
                                total_prompts += log_data.get("total_prompts", 0)
                                total_blocked += log_data.get("blocked_prompts", 0)
                                total_pii += log_data.get("pii_detections", 0)
                                total_secrets += log_data.get("secrets_detections", 0)
                                total_jailbreaks += log_data.get("jailbreak_attempts", 0)
                                total_toxicity += log_data.get("toxicity_detections", 0)
                        except Exception as e:
                            logger.warning(f"Could not read log file {log_file}: {str(e)}")
        
        logger.info(f"Retrieved statistics for {total_threads} threads from local folder")
        
        return {
            "total_threads": total_threads,
            "total_conversations": total_conversations,
            "total_prompts": total_prompts,
            "total_blocked": total_blocked,
            "total_pii": total_pii,
            "total_secrets": total_secrets,
            "total_jailbreaks": total_jailbreaks,
            "total_toxicity": total_toxicity,
            "timestamp": now()
        }
    
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching statistics: {str(e)}"
        )


@app.get("/api/security-logs/search/prompts", tags=["Security Logs"])
async def search_prompts(
    query: str,
    bot_id: Optional[str] = None,
    limit: int = 100
):
    """
    Search for prompts across all threads and conversations from local folder
    
    Query Parameters:
    - query: Search term (minimum 3 characters)
    - bot_id: Filter by specific bot ID (optional)
    - limit: Maximum results to return (default: 100)
    """
    try:
        if len(query) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be at least 3 characters long"
            )
        
        results = []
        query_lower = query.lower()
        
        # Search in local security logs
        if SECURITY_STORAGE_DIR.exists():
            for thread_dir in SECURITY_STORAGE_DIR.iterdir():
                if thread_dir.is_dir():
                    for log_file in thread_dir.glob("*.json"):
                        try:
                            with open(log_file, 'r') as f:
                                log_data = json.load(f)
                                
                                # Check bot_id filter
                                if bot_id and log_data.get("bot_id") != bot_id:
                                    continue
                                
                                # Search prompt and anonymized_prompt
                                if query_lower in log_data.get("prompt", "").lower():
                                    results.append(log_data)
                                elif query_lower in log_data.get("anonymized_prompt", "").lower():
                                    results.append(log_data)
                                
                                if len(results) >= limit:
                                    break
                        except Exception as e:
                            logger.warning(f"Could not read log file {log_file}: {str(e)}")
                    
                    if len(results) >= limit:
                        break
        
        results = results[:limit]
        
        logger.info(f"Found {len(results)} matches for query: '{query}'")
        
        return {
            "results": results,
            "total_matches": len(results),
            "query": query,
            "timestamp": now()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching prompts: {str(e)}"
        )


@app.get("/api/security-logs/threats/top", tags=["Security Logs"])
async def get_top_threatening_threads(
    limit: int = 10,
    bot_id: Optional[str] = None
):
    """
    Get threads with the most security threats from local folder
    
    Query Parameters:
    - limit: Number of threads to return (default: 10)
    - bot_id: Filter by specific bot ID (optional)
    """
    try:
        threat_threads = []
        
        # Scan all thread directories
        if SECURITY_STORAGE_DIR.exists():
            for thread_dir in SECURITY_STORAGE_DIR.iterdir():
                if thread_dir.is_dir():
                    thread_id = thread_dir.name
                    thread_threats = {
                        "thread_id": thread_id,
                        "pii_detections": 0,
                        "jailbreak_attempts": 0,
                        "toxicity_detections": 0,
                        "secrets_detections": 0,
                        "total_threats": 0,
                        "log_count": 0
                    }
                    
                    # Scan all conversation logs in this thread
                    for log_file in thread_dir.glob("*.json"):
                        try:
                            with open(log_file, 'r') as f:
                                log_data = json.load(f)
                                
                                # Check bot_id filter
                                if bot_id and log_data.get("bot_id") != bot_id:
                                    continue
                                
                                thread_threats["bot_id"] = log_data.get("bot_id", "")
                                thread_threats["pii_detections"] += log_data.get("pii_detections", 0)
                                thread_threats["jailbreak_attempts"] += log_data.get("jailbreak_attempts", 0)
                                thread_threats["toxicity_detections"] += log_data.get("toxicity_detections", 0)
                                thread_threats["secrets_detections"] += log_data.get("secrets_detections", 0)
                                thread_threats["log_count"] += 1
                        except Exception as e:
                            logger.warning(f"Could not read log file {log_file}: {str(e)}")
                    
                    # Calculate total threats
                    thread_threats["total_threats"] = (
                        thread_threats["pii_detections"] +
                        thread_threats["jailbreak_attempts"] +
                        thread_threats["toxicity_detections"] +
                        thread_threats["secrets_detections"]
                    )
                    
                    # Only add threads with threats
                    if thread_threats["total_threats"] > 0:
                        threat_threads.append(thread_threats)
        
        # Sort by total_threats descending
        threat_threads = sorted(threat_threads, key=lambda x: x["total_threats"], reverse=True)
        
        # Limit results
        threat_threads = threat_threads[:limit]
        
        logger.info(f"Retrieved top {len(threat_threads)} threatening threads from local folder")
        
        return {
            "results": threat_threads,
            "timestamp": now()
        }
    
    except Exception as e:
        logger.error(f"Error fetching top threats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching top threats: {str(e)}"
        )


@app.post("/api/security-logs/process", tags=["Security Logs"])
async def trigger_conversation_processing(
    bot_id: str,
    limit: int = 100
):
    """
    Manually trigger conversation processing for a specific bot
    This does what process_conversations.py does, but via API
    
    Use this to process conversations on-demand instead of running the script
    """
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        conversations_collection = db[MONGODB_CONVERSATIONS_COLLECTION]
        security_logs_collection = db[MONGODB_SECURITY_LOGS_COLLECTION]
        
        # Get latest conversations for the bot
        pipeline = [
            {"$match": {"botId": bot_id}},
            {"$sort": {"createdAt": -1}},
            {"$group": {
                "_id": "$conversationId",
                "latest_message": {"$first": "$$ROOT"}
            }},
            {"$sort": {"latest_message.createdAt": -1}},
            {"$limit": limit},
            {"$project": {"_id": 1}}
        ]
        
        conversation_ids = [doc["_id"] for doc in conversations_collection.aggregate(pipeline)]
        
        if not conversation_ids:
            return {
                "success": True,
                "message": "No conversations found for this bot",
                "processed": 0,
                "timestamp": now()
            }
        
        # Fetch all messages
        all_messages = list(conversations_collection.find({
            "botId": bot_id,
            "conversationId": {"$in": conversation_ids}
        }).sort("createdAt", 1))
        
        # Aggregate by thread
        threads = {}
        for msg in all_messages:
            thread_id = msg.get("threadId")
            conversation_id = msg.get("conversationId")
            
            if thread_id and conversation_id:
                if thread_id not in threads:
                    threads[thread_id] = {}
                if conversation_id not in threads[thread_id]:
                    threads[thread_id][conversation_id] = []
                threads[thread_id][conversation_id].append(msg)
        
        # Process each thread (simplified version - you'd want to add full validation)
        processed_count = 0
        
        for thread_id, conversations in threads.items():
            conversation_logs = []
            
            for conv_id, messages in conversations.items():
                sorted_messages = sorted(messages, key=lambda x: x.get("createdAt"))
                
                # Simple processing - in production, call your validation logic here
                security_events = []
                for msg in sorted_messages:
                    if msg.get("from", {}).get("role") == "user":
                        prompt = msg.get("activity", {}).get("text", "")
                        
                        # Here you would call: detector.scan_prompt_parallel(prompt, bot_id)
                        # For now, just store the message
                        security_events.append({
                            "timestamp": msg.get("createdAt"),
                            "message_id": msg.get("messageId"),
                            "prompt": prompt,
                            "prompt_length": len(prompt)
                        })
                
                conversation_logs.append({
                    "conversation_id": conv_id,
                    "started_at": sorted_messages[0].get("createdAt"),
                    "ended_at": sorted_messages[-1].get("createdAt"),
                    "security_events": security_events,
                    "total_prompts": len(security_events)
                })
                
                processed_count += 1
            
            # Save to security_logs
            thread_document = {
                "thread_id": thread_id,
                "bot_id": bot_id,
                "user_id": all_messages[0].get("userId"),
                "conversations": conversation_logs,
                "total_conversations": len(conversation_logs),
                "last_updated": now()
            }
            
            security_logs_collection.update_one(
                {"thread_id": thread_id},
                {"$set": thread_document},
                upsert=True
            )
        
        logger.info(f"Processed {processed_count} conversations into {len(threads)} threads")
        
        return {
            "success": True,
            "processed_conversations": processed_count,
            "processed_threads": len(threads),
            "bot_id": bot_id,
            "timestamp": now()
        }
    
    except Exception as e:
        logger.error(f"Error processing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing conversations: {str(e)}"
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
            },
            "secrets": {
                "name": "Secrets Scanner",
                "threshold": 0.0,
                "description": "Detects API keys, passwords, and tokens",
                "concurrent_safe": True
            }
            # 🔧 ADD NEW SCANNER INFO FOR API STATS:
            # Document your new scanners in the /api/stats endpoint
            # ================================================================
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

# ============================================================================
# REAL-TIME MONITORING ENDPOINTS (SSE)
# ============================================================================

@app.get("/api/monitor/stream", tags=["Real-Time Monitor"])
async def stream_monitor():
    """
    SSE endpoint for real-time conversation monitoring.

    Connect from frontend:
        const eventSource = new EventSource('/api/monitor/stream');
        eventSource.addEventListener('processed', (e) => {
            const data = JSON.parse(e.data);
            console.log('Conversation processed:', data);
        });
    """
    monitor = get_monitor()
    return StreamingResponse(
        monitor.sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/monitor/status", tags=["Real-Time Monitor"])
async def get_monitor_status():
    """Get current monitor status"""
    monitor = get_monitor()
    return {
        "running":         monitor.running,
        "processed_count": monitor.processed_count,
        "skipped_count":   monitor.skipped_count,
        "error_count":     monitor.error_count,
        "subscribers":     len(monitor._sse_queues),
        "timestamp":       now()
    }


@app.post("/api/monitor/stop", tags=["Real-Time Monitor"])
async def stop_monitor():
    """Stop the real-time monitor"""
    monitor = get_monitor()
    monitor.stop()
    return {
        "success":         True,
        "message":         "Monitor stopped",
        "processed_count": monitor.processed_count,
        "error_count":     monitor.error_count,
        "timestamp":       now()
    }


# ============================================================================
# LOCAL SECURITY LOGS ENDPOINTS
# ============================================================================

@app.get("/api/security-logs/local", tags=["Security Logs"])
async def get_local_security_logs():
    """
    Get all security logs from local JSON files.
    This is what the dashboard reads from.
    """
    logs = []

    for log_file in SECURITY_STORAGE_DIR.glob("*.json"):
        # Skip the hidden resume token file
        if log_file.name.startswith("."):
            continue
        with open(log_file, 'r') as f:
            logs.append(json.load(f))

    total_stats = {
        "totalConversations": len(logs),
        "totalPrompts":       sum(log.get("total_prompts", 0)       for log in logs),
        "totalBlocked":       sum(log.get("blocked_prompts", 0)     for log in logs),
        "totalPII":           sum(log.get("pii_detections", 0)      for log in logs),
        "totalJailbreaks":    sum(log.get("jailbreak_attempts", 0)  for log in logs),
        "totalToxicity":      sum(log.get("toxicity_detections", 0) for log in logs),
        "totalSecrets":       sum(log.get("secrets_detections", 0)  for log in logs),
    }

    return {
        "success":   True,
        "sessions":  logs,   # "sessions" key keeps dashboard compatibility
        "stats":     total_stats,
        "timestamp": now()
    }


@app.get("/api/security-logs/local/{bot_id}", tags=["Security Logs"])
async def get_local_security_log(bot_id: str):
    """Get the security log for a specific bot"""
    log_path = SECURITY_STORAGE_DIR / f"{bot_id}.json"

    if not log_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No security log found for bot_id: {bot_id}"
        )

    with open(log_path, 'r') as f:
        log_data = json.load(f)

    return {"success": True, "log": log_data, "timestamp": now()}


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information, initialize MongoDB, and launch the monitor."""
    logger.info("=" * 80)
    logger.info("🚀 Starting Jailbreak-Protected LLM API - ⚡ CONCURRENT MODE ⚡")
    logger.info("=" * 80)

    # Launch real-time monitor as a background task — runs for the life of the server
    monitor = get_monitor()
    asyncio.create_task(monitor.run_forever())
    logger.info("📡 Real-time monitor background task launched")

    # Initialize MongoDB connection
    logger.info("🔌 Initializing MongoDB connection...")
    if connect_mongodb():
        logger.info("✓ MongoDB connected successfully")
    else:
        logger.warning("⚠️  Failed to connect to MongoDB - using fallback mode")

    logger.info("✓ Loaded security scanners:")
    logger.info("  - Prompt Injection Scanner")
    logger.info("  - Toxicity Scanner")
    logger.info("  - PII Detection & Anonymization (includes Secrets)")
    logger.info("✓ Thread-safe PII scanner with isolated instances")
    logger.info("✓ READY FOR CONCURRENT BOT SIMULATION")
    logger.info("=" * 80)
    logger.info("⚡ Can handle 50+ bots simultaneously! ⚡")
    logger.info("=" * 80 + "\n")

    if not OPENROUTER_API_KEY:
        logger.warning("⚠️  OPENROUTER_API_KEY not set! Set it as environment variable.")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown — stop scanner, monitor, and MongoDB."""
    shutdown_scanner()
    shutdown_monitor()
    close_mongodb()

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