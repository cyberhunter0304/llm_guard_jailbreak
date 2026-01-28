"""
Jailbreak-Protected LLM API Endpoint - Production Grade with PII Detection
FastAPI with OpenRouter GPT-4o mini integration and comprehensive security scanning
Includes: Input scanners, PII detection & tracking, advanced threat detection, and Analytics
Modified to return user-friendly messages instead of blocking requests
OUTPUT VALIDATORS REMOVED - Only input validation remains
PII DETECTION INTEGRATED - Tracks PII occurrences per bot (using external pii_detector module)
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging
import os
import httpx
import yaml
import asyncio
from pathlib import Path
from collections import defaultdict

# Import external PII detector module
from pii_detector import PIIDetector

# LLM Guard Input Scanners
from llm_guard.input_scanners import (
    PromptInjection,
    Toxicity,
    InvisibleText,
    TokenLimit
)

# Configure structured logging (JSON format)
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": %(message)s}'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Production-Grade LLM Security API with PII Detection",
    description="Enterprise-ready LLM API with comprehensive input security scanning and PII tracking",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://0.0.0.0:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Enhanced global metrics with PII tracking
METRICS = {
    "total_scans": 0,
    "total_blocks": 0,
    "input_blocks_by_scanner": {},
    "scanner_latencies": {},
    "scanner_errors": {},
    "bot_analytics": {},
    "bot_requests": defaultdict(list),
    "bot_pii": defaultdict(list)  # PII tracking per bot
}


class RequestLog(BaseModel):
    """Individual request log entry"""
    timestamp: str
    prompt: str
    prompt_length: int
    response_length: int
    input_blocked: bool
    output_blocked: bool
    blocked_by: List[str]
    risk_level: str
    response_time: float
    model: str
    pii_detected: bool = False
    pii_count: int = 0


class PIIDetection(BaseModel):
    """PII detection entry"""
    timestamp: str
    entity_type: str
    entity_value: str
    context: str
    prompt: str
    request_id: Optional[str] = None


def update_bot_analytics(
    bot_id: str, 
    bot_name: str,
    blocked: bool, 
    scan_type: str, 
    scanner_name: str = None,
    request_log: RequestLog = None
):
    """Update analytics for a specific bot"""
    if bot_id not in METRICS["bot_analytics"]:
        METRICS["bot_analytics"][bot_id] = {
            "bot_id": bot_id,
            "bot_name": bot_name,
            "total_requests": 0,
            "total_blocks": 0,
            "input_blocks": 0,
            "output_blocks": 0,
            "blocks_by_scanner": {},
            "toxicity_count": 0,
            "prompt_injection_count": 0,
            "pii_detected_count": 0,
            "pii_types": {},
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat()
        }
    
    bot_data = METRICS["bot_analytics"][bot_id]
    bot_data["total_requests"] += 1
    bot_data["last_seen"] = datetime.utcnow().isoformat()
    bot_data["bot_name"] = bot_name
    
    if blocked:
        bot_data["total_blocks"] += 1
        if scan_type == "input":
            bot_data["input_blocks"] += 1
        else:
            bot_data["output_blocks"] += 1
        
        if scanner_name:
            if scanner_name not in bot_data["blocks_by_scanner"]:
                bot_data["blocks_by_scanner"][scanner_name] = 0
            bot_data["blocks_by_scanner"][scanner_name] += 1
            
            if "toxicity" in scanner_name.lower():
                bot_data["toxicity_count"] += 1
            if "prompt_injection" in scanner_name.lower():
                bot_data["prompt_injection_count"] += 1
    
    if request_log:
        if len(METRICS["bot_requests"][bot_id]) >= 100:
            METRICS["bot_requests"][bot_id].pop(0)
        METRICS["bot_requests"][bot_id].append(request_log.dict())


def add_pii_detection(bot_id: str, pii_detection: PIIDetection):
    """Add a PII detection to bot's PII log"""
    if len(METRICS["bot_pii"][bot_id]) >= 200:
        METRICS["bot_pii"][bot_id].pop(0)
    METRICS["bot_pii"][bot_id].append(pii_detection.dict())
    
    if bot_id in METRICS["bot_analytics"]:
        bot_data = METRICS["bot_analytics"][bot_id]
        bot_data["pii_detected_count"] += 1
        
        entity_type = pii_detection.entity_type
        if entity_type not in bot_data["pii_types"]:
            bot_data["pii_types"][entity_type] = 0
        bot_data["pii_types"][entity_type] += 1


# ============================================================================
# FRIENDLY ERROR MESSAGES
# ============================================================================

def get_friendly_input_message(blocked_by: List[str]) -> str:
    """Generate user-friendly error messages"""
    if not blocked_by:
        return "I'm sorry, but I couldn't process your request. Please try rephrasing your message."
    
    primary_trigger = blocked_by[0].lower()
    
    if "toxicity" in primary_trigger:
        return "Sorry, I can't process your query. Please ask it nicely and respectfully."
    elif "prompt_injection" in primary_trigger or "injection" in primary_trigger:
        return "I detected something unusual in your message. Please rephrase your question in a straightforward way."
    elif "invisible" in primary_trigger:
        return "I noticed some hidden characters in your message. Please type your question normally."
    elif "token" in primary_trigger:
        return "Your message is too long for me to process. Please try breaking it into smaller questions."
    else:
        return "I couldn't process your request due to security guidelines. Please rephrase your message and try again."


# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = Path("config.yaml")
    
    default_config = {
        "input_scanners": {
            "prompt_injection": {"enabled": True, "threshold": 0.9},
            "toxicity": {"enabled": True, "threshold": 0.5},
            "invisible_text": {"enabled": True},
            "token_limit": {"enabled": True, "max_tokens": 4000}
        },
        "pii_detection": {
            "enabled": True,
            "threshold": 0.8,
            "language": "en"
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f'{{"message": "Configuration loaded from {config_path}"}}')
                return config
        except Exception as e:
            logger.warning(f'{{"message": "Failed to load config.yaml, using defaults", "error": "{str(e)}"}}')
            return default_config
    else:
        logger.info(f'{{"message": "config.yaml not found, using default configuration"}}')
        return default_config


CONFIG = load_config()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt")
    model: str = Field(default="openai/gpt-4o-mini", description="LLM model to use")
    test_mode: bool = Field(default=False, description="Return scan results without blocking")
    bot_id: str = Field(default="default", description="Unique identifier for the bot/application")
    bot_name: str = Field(default="Default Bot", description="Display name for the bot")

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Prompt must be a non-empty string")
        return v.strip()
class SecurityScanResult(BaseModel):
    is_safe: bool
    detections: Dict[str, Any]
    risk_level: str
    message: str
    timestamp: str
    sanitized_text: Optional[str] = None
    scanner_latencies: Optional[Dict[str, float]] = None
class ChatResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    input_security_scan: SecurityScanResult
    output_security_scan: Optional[SecurityScanResult] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    timestamp: str


# ============================================================================
# JAILBREAK DETECTOR
# ============================================================================

class JailbreakDetector:
    """Comprehensive input security scanner"""
    
    def __init__(self, config: dict):
        self.config = config["input_scanners"]
        self.scanners = {}
        
        if self.config["prompt_injection"]["enabled"]:
            self.scanners["prompt_injection"] = PromptInjection(
                threshold=self.config["prompt_injection"]["threshold"]
            )
        
        if self.config["toxicity"]["enabled"]:
            self.scanners["toxicity"] = Toxicity(
                threshold=self.config["toxicity"]["threshold"]
            )
        
        if self.config["invisible_text"]["enabled"]:
            self.scanners["invisible_text"] = InvisibleText()
        
        if self.config["token_limit"]["enabled"]:
            self.scanners["token_limit"] = TokenLimit(
                limit=self.config["token_limit"]["max_tokens"],
                encoding_name="cl100k_base"
            )
        
        logger.info(f'{{"message": "JailbreakDetector initialized", "scanners": {list(self.scanners.keys())}}}')
    
    def scan_prompt(self, prompt: str, test_mode: bool = False) -> Tuple[str, SecurityScanResult]:
        """Scan prompt with all enabled input scanners"""
        start_time = datetime.utcnow()
        detections = {}
        scanner_latencies = {}
        sanitized = prompt
        blocked_scanners = []
        
        for scanner_name, scanner in self.scanners.items():
            try:
                scanner_start = datetime.utcnow()
                sanitized, is_valid, risk_score = scanner.scan(sanitized)
                scanner_end = datetime.utcnow()
                
                latency = (scanner_end - scanner_start).total_seconds()
                scanner_latencies[scanner_name] = round(latency, 4)
                
                if scanner_name not in METRICS["scanner_latencies"]:
                    METRICS["scanner_latencies"][scanner_name] = []
                METRICS["scanner_latencies"][scanner_name].append(latency)
                
                detections[scanner_name] = {
                    "is_valid": is_valid,
                    "risk_score": float(risk_score) if risk_score is not None else 0.0
                }
                
                if not is_valid:
                    blocked_scanners.append(scanner_name)
                    if scanner_name not in METRICS["input_blocks_by_scanner"]:
                        METRICS["input_blocks_by_scanner"][scanner_name] = 0
                    METRICS["input_blocks_by_scanner"][scanner_name] += 1
                    
            except Exception as e:
                logger.error(f'{{"message": "Scanner error", "scanner": "{scanner_name}", "error": "{str(e)}"}}')
                if scanner_name not in METRICS["scanner_errors"]:
                    METRICS["scanner_errors"][scanner_name] = 0
                METRICS["scanner_errors"][scanner_name] += 1
                detections[scanner_name] = {"error": str(e)}
        
        METRICS["total_scans"] += 1
        
        is_safe = len(blocked_scanners) == 0
        
        if not is_safe:
            METRICS["total_blocks"] += 1
            risk_level = "HIGH"
            message = f"Input blocked by: {', '.join(blocked_scanners)}"
        else:
            high_risk_scanners = [
                name for name, result in detections.items()
                if isinstance(result.get("risk_score"), (int, float)) and result["risk_score"] > 0.5
            ]
            if high_risk_scanners:
                risk_level = "MEDIUM"
                message = f"Input passed with warnings from: {', '.join(high_risk_scanners)}"
            else:
                risk_level = "LOW"
                message = "Input validation passed"
        
        return sanitized, SecurityScanResult(
            is_safe=is_safe,
            detections=detections,
            risk_level=risk_level,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            sanitized_text=sanitized if sanitized != prompt else None,
            scanner_latencies=scanner_latencies
        )


# ============================================================================
# LLM INTEGRATION
# ============================================================================

async def call_openrouter(prompt: str, model: str) -> dict:
    """Call OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://your-app.com",
        "X-Title": "LLM Security API"
    }
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to LLM service: {str(e)}"
        )


# ============================================================================
# API ENDPOINTS - SYSTEM
# ============================================================================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Production-Grade LLM Security API with PII Detection",
        "timestamp": datetime.utcnow().isoformat(),
        "input_scanners": len(detector.scanners),
        "output_scanners": 0,
        "pii_detection": pii_detector is not None,
        "scanners": {
            "input": list(detector.scanners.keys()),
            "output": []
        }
    }


@app.get("/api/config", tags=["System"])
async def get_config():
    """View active scanner configuration"""
    return {
        "input_scanners": {
            name: {
                "enabled": True,
                "threshold": cfg.get("threshold", "N/A")
            }
            for name, cfg in CONFIG["input_scanners"].items()
            if cfg.get("enabled", False)
        },
        "output_scanners": {},
        "pii_detection": {
            "enabled": pii_detector is not None,
            "threshold": CONFIG.get("pii_detection", {}).get("threshold", 0.0),
            "language": CONFIG.get("pii_detection", {}).get("language", "en")
        }
    }


@app.get("/api/stats", tags=["System"])
async def scanner_stats():
    """Get scanner performance statistics"""
    avg_latencies = {}
    for scanner_name, latencies in METRICS["scanner_latencies"].items():
        if latencies:
            avg_latencies[scanner_name] = round(sum(latencies) / len(latencies), 4)
    
    total_pii = sum(len(pii_list) for pii_list in METRICS["bot_pii"].values())
    
    return {
        "total_scans": METRICS["total_scans"],
        "total_blocks": METRICS["total_blocks"],
        "total_pii_detections": total_pii,
        "input_blocks_by_scanner": METRICS["input_blocks_by_scanner"],
        "output_blocks_by_scanner": {},
        "average_scanner_latencies": avg_latencies,
        "scanner_errors": METRICS["scanner_errors"],
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# API ENDPOINTS - ANALYTICS
# ============================================================================

@app.get("/api/analytics/overview", tags=["Analytics"])
async def get_analytics_overview():
    """Get overall system analytics"""
    total_requests = sum(bot["total_requests"] for bot in METRICS["bot_analytics"].values())
    total_blocks = sum(bot["total_blocks"] for bot in METRICS["bot_analytics"].values())
    total_pii = sum(bot["pii_detected_count"] for bot in METRICS["bot_analytics"].values())
    
    all_scanner_blocks = defaultdict(int)
    for bot in METRICS["bot_analytics"].values():
        for scanner, count in bot["blocks_by_scanner"].items():
            all_scanner_blocks[scanner] += count
    
    top_blocked_scanners = [
        {"scanner": scanner, "count": count}
        for scanner, count in sorted(all_scanner_blocks.items(), key=lambda x: x[1], reverse=True)
    ][:10]
    
    block_rate = (total_blocks / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "total_bots": len(METRICS["bot_analytics"]),
        "total_requests": total_requests,
        "total_blocks": total_blocks,
        "total_pii_detections": total_pii,
        "block_rate": round(block_rate, 2),
        "input_blocks": sum(bot["input_blocks"] for bot in METRICS["bot_analytics"].values()),
        "output_blocks": sum(bot["output_blocks"] for bot in METRICS["bot_analytics"].values()),
        "top_blocked_scanners": top_blocked_scanners,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/analytics/bots", tags=["Analytics"])
async def get_bots_analytics(
    limit: int = 100,
    sort_by: str = "total_requests"
):
    """Get analytics for all bots"""
    bots = list(METRICS["bot_analytics"].values())
    
    if sort_by == "total_blocks":
        bots.sort(key=lambda x: x["total_blocks"], reverse=True)
    elif sort_by == "last_seen":
        bots.sort(key=lambda x: x["last_seen"], reverse=True)
    else:
        bots.sort(key=lambda x: x["total_requests"], reverse=True)
    
    for bot in bots:
        bot["last_request_at"] = bot["last_seen"]
    
    return {
        "bots": bots[:limit],
        "total": len(bots),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/analytics/bot/{bot_id}", tags=["Analytics"])
async def get_bot_analytics(bot_id: str):
    """Get detailed analytics for a specific bot"""
    if bot_id not in METRICS["bot_analytics"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found in analytics"
        )
    
    bot_data = METRICS["bot_analytics"][bot_id]
    recent_requests = METRICS["bot_requests"].get(bot_id, [])
    pii_detections = METRICS["bot_pii"].get(bot_id, [])
    
    return {
        "bot": bot_data,
        "recent_requests": recent_requests[-50:],
        "pii_detections": pii_detections[-100:],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/analytics/bot/{bot_id}/pii", tags=["Analytics"])
async def get_bot_pii(bot_id: str, limit: int = 100):
    """Get PII detections for a specific bot"""
    if bot_id not in METRICS["bot_analytics"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found in analytics"
        )
    
    pii_detections = METRICS["bot_pii"].get(bot_id, [])
    
    return {
        "bot_id": bot_id,
        "bot_name": METRICS["bot_analytics"][bot_id]["bot_name"],
        "total_pii_detections": len(pii_detections),
        "pii_detections": pii_detections[-limit:],
        "pii_by_type": METRICS["bot_analytics"][bot_id].get("pii_types", {}),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# API ENDPOINTS - CHAT
# ============================================================================

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Main chat endpoint with input security scanning and PII detection
    
    Pipeline:
    1. Detect PII in input (log but don't block)
    2. Scan input with JailbreakDetector
    3. If unsafe, return friendly message
    4. If safe, call LLM
    5. Return response
    6. Log analytics
    """
    request_start_time = datetime.utcnow()
    
    try:
        # PHASE 0: PII DETECTION (NON-BLOCKING)
        pii_detected = False
        pii_count = 0
        
        if pii_detector:
            try:
                pii_entities, risk_score = pii_detector.detect_pii(request.prompt)
                pii_count = len(pii_entities)
                
                if pii_count > 0:
                    pii_detected = True
                    logger.info(f'{{"message": "PII detected", "bot_id": "{request.bot_id}", "pii_count": {pii_count}, "risk_score": {risk_score}}}')
                    
                    for entity in pii_entities:
                        pii_detection = PIIDetection(
                            timestamp=datetime.utcnow().isoformat(),
                            entity_type=entity["type"],
                            entity_value=entity["value"],
                            context=entity["context"],
                            prompt=request.prompt
                        )
                        add_pii_detection(request.bot_id, pii_detection)
            except Exception as e:
                logger.error(f'{{"message": "PII detection error", "error": "{str(e)}"}}')
        
        # PHASE 1: INPUT SECURITY SCANNING
        logger.info(f'{{"message": "Processing chat request", "bot_id": "{request.bot_id}", "prompt_length": {len(request.prompt)}}}')
        
        sanitized_prompt, input_scan = detector.scan_prompt(request.prompt, test_mode=request.test_mode)
        
        input_blocked = not input_scan.is_safe
        blocked_by = []
        
        if input_blocked:
            blocked_by = [
                name for name, result in input_scan.detections.items()
                if isinstance(result, dict) and not result.get("is_valid", True)
            ]
        
        if input_blocked and not request.test_mode:
            logger.warning(f'{{"message": "Request blocked at input", "bot_id": "{request.bot_id}", "risk_level": "{input_scan.risk_level}"}}')
            
            friendly_message = get_friendly_input_message(blocked_by)
            
            response_time = (datetime.utcnow() - request_start_time).total_seconds()
            request_log = RequestLog(
                timestamp=datetime.utcnow().isoformat(),
                prompt=request.prompt,
                prompt_length=len(request.prompt),
                response_length=len(friendly_message),
                input_blocked=True,
                output_blocked=False,
                blocked_by=blocked_by,
                risk_level=input_scan.risk_level,
                response_time=response_time,
                model=request.model,
                pii_detected=pii_detected,
                pii_count=pii_count
            )
            update_bot_analytics(
                request.bot_id,
                request.bot_name,
                blocked=True,
                scan_type="input",
                scanner_name=blocked_by[0] if blocked_by else None,
                request_log=request_log
            )
            
            return ChatResponse(
                success=True,
                response=friendly_message,
                input_security_scan=input_scan,
                output_security_scan=None,
                model=request.model,
                timestamp=datetime.utcnow().isoformat()
            )
        
        logger.info(f'{{"message": "Input security check passed", "bot_id": "{request.bot_id}"}}')
        
        # PHASE 2: CALL LLM
        if not OPENROUTER_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenRouter API key not configured"
            )
        
        logger.info(f'{{"message": "Calling LLM", "bot_id": "{request.bot_id}", "model": "{request.model}"}}')
        llm_response = await call_openrouter(sanitized_prompt, request.model)
        assistant_message = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # PHASE 3: LOG ANALYTICS & RETURN
        response_time = (datetime.utcnow() - request_start_time).total_seconds()
        overall_risk = input_scan.risk_level
        
        request_log = RequestLog(
            timestamp=datetime.utcnow().isoformat(),
            prompt=request.prompt,
            prompt_length=len(request.prompt),
            response_length=len(assistant_message),
            input_blocked=False,
            output_blocked=False,
            blocked_by=[],
            risk_level=overall_risk,
            response_time=response_time,
            model=request.model,
            pii_detected=pii_detected,
            pii_count=pii_count
        )
        
        update_bot_analytics(
            request.bot_id,
            request.bot_name,
            blocked=False,
            scan_type="none",
            request_log=request_log
        )
        
        return ChatResponse(
            success=True,
            response=assistant_message,
            input_security_scan=input_scan,
            output_security_scan=None,
            model=request.model,
            usage=llm_response.get("usage", {}),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'{{"message": "Internal server error", "bot_id": "{request.bot_id}", "error": "{str(e)}"}}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    print("=" * 80)
    print("🚀 Starting Production-Grade LLM Security API v2.1 (Input + PII Detection)")
    print("=" * 80)
    print(f"✓ Input scanners loaded: {len(detector.scanners)}")
    for scanner_name in detector.scanners.keys():
        print(f"  - {scanner_name}")
    print(f"✓ Output scanners: REMOVED (no output validation)")
    print(f"✓ PII Detection: {'ENABLED' if pii_detector else 'DISABLED'} (external module)")
    print(f"✓ Analytics enabled: True")
    print(f"✓ Friendly error messages: Enabled")
    print("=" * 80)
    
    if not OPENROUTER_API_KEY:
        print("⚠️  OPENROUTER_API_KEY not set! Set it as environment variable.")
        print("   Export it: export OPENROUTER_API_KEY='your-key-here'")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )