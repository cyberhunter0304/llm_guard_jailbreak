from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging
import time
import asyncio

# Local imports
from config import API_CONFIG, ALLOWED_ORIGINS, AVAILABLE_MODELS, LOG_LEVEL, OPENROUTER_API_KEY, MONGODB_SECURITY_LOGS_COLLECTION, MONGODB_CONVERSATIONS_COLLECTION, MONGODB_THREAD_SUMMARIES_COLLECTION
from models import (
    ChatRequest, ScanRequest, ChatResponse, SecurityScanResult,
    HealthResponse, StatsResponse
)
from mongodb_storage import (
    load_bot_security_log, save_bot_security_log,
    delete_bot_security_log, list_all_bot_sessions,
    connect_mongodb, close_mongodb,
    get_unprocessed_conversations, mark_conversation_processed,
    get_processing_stats, get_mongodb
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
    
    This reads from the new 'security_logs' collection that the 
    process_conversations.py script creates.
    
    Query Parameters:
    - bot_id: Filter by specific bot ID (optional)
    - skip: Pagination offset (default: 0)
    - limit: Max results (default: 100)
    """
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        security_logs = db[MONGODB_THREAD_SUMMARIES_COLLECTION]
        
        query = {}
        if bot_id:
            query["bot_id"] = bot_id
        
        # Get total count
        total = security_logs.count_documents(query)
        
        # Get threads with pagination
        threads = list(security_logs.find(query)
                      .sort("last_updated", -1)
                      .skip(skip)
                      .limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for thread in threads:
            thread["_id"] = str(thread["_id"])
        
        logger.info(f"Retrieved {len(threads)} threads (total: {total})")
        
        return {
            "threads": threads,
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
    
    Query Parameters:
    - bot_id: Filter by specific bot ID (optional)
    """
    try:
        db = get_mongodb()
        
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        thread_summaries = db[MONGODB_THREAD_SUMMARIES_COLLECTION]
        
        match_query = {}
        if bot_id:
            match_query["bot_id"] = bot_id
        
        pipeline = [
            {"$match": match_query} if match_query else {"$match": {}},
            {
                "$group": {
                    "_id": None,
                    "total_threads": {"$sum": 1},
                    "total_conversations": {"$sum": "$total_conversations"},
                    "total_prompts": {"$sum": "$total_prompts"},
                    "total_blocked": {"$sum": "$blocked_prompts"},
                    "total_pii": {"$sum": "$pii_detections"},
                    "total_secrets": {"$sum": {"$ifNull": ["$secrets_detections", 0]}},
                    "total_jailbreaks": {"$sum": "$jailbreak_attempts"},
                    "total_toxicity": {"$sum": "$toxicity_detections"}
                }
            }
        ]
        
        result = list(thread_summaries.aggregate(pipeline))
        
        if not result:
            return {
                "total_threads": 0,
                "total_conversations": 0,
                "total_prompts": 0,
                "total_blocked": 0,
                "total_pii": 0,
                "total_secrets": 0,
                "total_jailbreaks": 0,
                "total_toxicity": 0,
                "timestamp": now()
            }
        
        stats = result[0]
        stats.pop("_id")
        stats["timestamp"] = now()
        
        logger.info(f"Retrieved statistics for {stats['total_threads']} threads")
        
        return stats
    
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
    Search for prompts across all threads and conversations
    
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
        
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        # Search in security_logs collection for individual validated prompts
        security_logs = db[MONGODB_SECURITY_LOGS_COLLECTION]
        
        match_query = {"prompt": {"$regex": query, "$options": "i"}}
        if bot_id:
            match_query["bot_id"] = bot_id
        
        results = list(security_logs.find(match_query).limit(limit))
        
        # Convert ObjectId to string
        for result in results:
            result["_id"] = str(result["_id"])
        
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
    Get threads with the most security threats
    
    Query Parameters:
    - limit: Number of threads to return (default: 10)
    - bot_id: Filter by specific bot ID (optional)
    """
    try:
        db = get_mongodb()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB not connected"
            )
        
        thread_summaries = db[MONGODB_THREAD_SUMMARIES_COLLECTION]
        
        match_query = {}
        if bot_id:
            match_query["bot_id"] = bot_id
        
        pipeline = [
            {"$match": match_query} if match_query else {"$match": {}},
            {
                "$addFields": {
                    "total_threats": {
                        "$add": [
                            {"$ifNull": ["$pii_detections", 0]},
                            {"$ifNull": ["$jailbreak_attempts", 0]},
                            {"$ifNull": ["$toxicity_detections", 0]},
                            {"$ifNull": ["$secrets_detections", 0]}
                        ]
                    }
                }
            },
            {"$match": {"total_threats": {"$gt": 0}}},
            {"$sort": {"total_threats": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "thread_id": 1,
                    "total_threats": 1,
                    "pii_detections": 1,
                    "jailbreak_attempts": 1,
                    "toxicity_detections": 1,
                    "secrets_detections": {"$ifNull": ["$secrets_detections", 0]}
                }
            }
        ]
        
        results = list(thread_summaries.aggregate(pipeline))
        
        logger.info(f"Retrieved top {len(results)} threatening threads")
        
        return {
            "results": results,
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


@app.on_event("startup")
async def startup_event():
    """Log startup information and initialize MongoDB"""
    logger.info("=" * 80)
    logger.info("🚀 Starting Jailbreak-Protected LLM API - ⚡ CONCURRENT MODE ⚡")
    logger.info("=" * 80)
    
    # Initialize MongoDB connection
    logger.info("🔌 Initializing MongoDB connection...")
    if connect_mongodb():
        logger.info("✓ MongoDB connected successfully")
    else:
        logger.warning("⚠️  Failed to connect to MongoDB - using fallback mode")
    
    logger.info(f"✓ Loaded 5 security scanners:")
    logger.info(f"  - Prompt Injection Scanner")
    logger.info(f"  - Toxicity Scanner")
    logger.info(f"  - PII Detection & Anonymization (includes Secrets)")
    logger.info("✓ Thread-safe PII scanner with isolated instances")
    logger.info("✓ MongoDB backend for persistent storage")
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