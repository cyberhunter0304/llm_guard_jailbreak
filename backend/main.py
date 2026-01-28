from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from llm_guard.vault import Vault
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from llm_guard.input_scanners import PromptInjection, Toxicity, Anonymize
from llm_guard.input_scanners.anonymize_helpers import BERT_LARGE_NER_CONF
import httpx
import os
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List, Tuple
import json
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

SECURITY_STORAGE_DIR = Path("security_logs")
SECURITY_STORAGE_DIR.mkdir(exist_ok=True)

def get_bot_security_file(bot_id: str) -> Path:
    """Get the security log file path for a bot session"""
    return SECURITY_STORAGE_DIR / f"{bot_id}.json"

def load_bot_security_log(bot_id: str) -> dict:
    """Load security log for a bot session"""
    security_file = get_bot_security_file(bot_id)
    if security_file.exists():
        with open(security_file, 'r') as f:
            return json.load(f)
    return {
        "bot_id": bot_id, 
        "created_at": datetime.utcnow().isoformat(),
        "security_events": [],
        "total_prompts": 0,
        "blocked_prompts": 0,
        "pii_detections": 0,
        "jailbreak_attempts": 0,
        "toxicity_detections": 0
    }

def save_bot_security_log(bot_id: str, security_data: dict):
    """Save security log for a bot session"""
    security_file = get_bot_security_file(bot_id)
    with open(security_file, 'w') as f:
        json.dump(security_data, f, indent=2)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Jailbreak-Protected LLM API",
    description="Secure LLM API with comprehensive jailbreak detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://0.0.0.0:8000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scanners
prompt_injection_scanner = PromptInjection(threshold=0.8)
toxicity_scanner = Toxicity(threshold=0.5)

# Thread pool for parallel security scanning
executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="SecurityScanner")

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "") 
print("OPEN ROUTER API KEY SET")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# Pydantic models
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt")
    model: str = Field(default="openai/gpt-4o-mini", description="LLM model to use")
    bot_id: str = Field(..., description="Unique bot session ID")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Prompt must be a non-empty string")
        return v.strip()


class ScanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="Prompt to scan")
    
    @validator('prompt')
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
    scan_duration: float


class ChatResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    security_scan: SecurityScanResult
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    timestamp: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: Optional[str] = None
    security_scan: Optional[SecurityScanResult] = None
    blocked: Optional[bool] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    scanners_active: int


class StatsResponse(BaseModel):
    service: str
    version: str
    scanners: Dict[str, Any]
    models_available: List[str]


class PIIDetector:
    """PII Detection using LLM Guard"""

    def __init__(
        self,
        preamble: str = "The following text contains sensitive information.",
        allowed_names: List[str] = None,
        hidden_names: List[str] = None,
        entity_types: List[str] = None,
        use_faker: bool = False,
        threshold: float = 0.0,
        language: str = "en"
    ):
        self.vault = Vault()
        self.scanner = Anonymize(
            vault=self.vault,
            preamble=preamble,
            allowed_names=allowed_names or [],
            hidden_names=hidden_names or [],
            entity_types=entity_types,
            use_faker=use_faker,
            recognizer_conf=BERT_LARGE_NER_CONF,
            threshold=threshold,
            language=language
        )
        self.preamble = preamble
        self.language = language
        self.threshold = threshold

    def anonymize(self, text: str) -> Tuple[str, List[Dict]]:
        """Detect and anonymize PII using tokens"""
        try:
            self.reset_vault()
            sanitized_text, _, risk_score = self.scanner.scan(text)

            entities = []
            import re
            tokens = re.findall(r'\[([A-Z_]+)_(\d+)\]', sanitized_text)
            
            for entity_type, entity_num in tokens:
                full_token = f"[{entity_type}_{entity_num}]"
                entities.append({
                    "type": entity_type,
                    "value": "REDACTED",
                    "token": full_token
                })

            print("\n" + "="*60)
            print("🔍 PII ANONYMIZATION COMPLETE 🔍")
            print("="*60)
            
            if not entities:
                print("✅ ✅ ✅  NO PII DETECTED  ✅ ✅ ✅")
                print("="*60 + "\n")
            else:
                print("🚨 🚨 🚨  PII DETECTED & ANONYMIZED  🚨 🚨 🚨")
                print("="*60)
                print(f"📋 Found {len(entities)} PII entities:")
                print("-"*60)
                for entity in entities:
                    print(f"   ⚠️  Type: {entity['type']}")
                    print(f"      Token: {entity['token']}")
                    print("-"*60)
                print(f"📊 Risk Score: {float(risk_score) if risk_score else 0.0:.2f}")
                print("="*60 + "\n")

            return sanitized_text, entities
            
        except Exception as e:
            logger.error(f"Anonymization failed: {str(e)}")
            print("\n" + "="*60)
            print("❌ PII ANONYMIZATION ERROR ❌")
            print(f"Error: {str(e)}")
            print("="*60 + "\n")
            return text, []

    def reset_vault(self):
        """Clears vault and reinitializes scanner"""
        self.vault = Vault()
        self.scanner = Anonymize(
            vault=self.vault,
            preamble=self.preamble,
            recognizer_conf=BERT_LARGE_NER_CONF,
            threshold=self.threshold,
            language=self.language
        )


class ParallelSecurityScanner:
    """
    Parallel Security Scanner using Threading
    Runs ALL security checks simultaneously on a single prompt
    """
    
    def __init__(self):
        self.scanners = {
            "prompt_injection": prompt_injection_scanner,
            "toxicity": toxicity_scanner
        }
    
    def _run_single_scanner(self, scanner_name: str, scanner, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Execute a single scanner (runs in separate thread)
        
        Returns:
            Tuple of (scanner_name, detection_result)
        """
        thread_id = threading.current_thread().name
        logger.info(f"🔍 [{thread_id}] Running {scanner_name} scanner...")
        
        start_time = time.time()
        
        try:
            sanitized, is_valid, risk_score = scanner.scan(prompt)
            execution_time = time.time() - start_time
            
            result = {
                "is_valid": is_valid,
                "risk_score": float(risk_score),
                "detected": not is_valid,
                "execution_time": execution_time
            }
            
            logger.info(f"✅ [{thread_id}] {scanner_name} completed in {execution_time:.3f}s")
            return scanner_name, result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ [{thread_id}] {scanner_name} error: {str(e)}")
            return scanner_name, {
                "error": str(e),
                "is_valid": True,
                "risk_score": 0.0,
                "execution_time": execution_time
            }
    
    def _run_pii_scanner(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Execute PII scanner (runs in separate thread)
        
        Returns:
            Tuple of ("pii", pii_result_dict)
        """
        thread_id = threading.current_thread().name
        logger.info(f"🔍 [{thread_id}] Running PII scanner...")
        
        start_time = time.time()
        
        try:
            pii_detector = PIIDetector(
                preamble="The following text contains sensitive information.",
                threshold=0.5
            )
            
            anonymized_prompt, pii_entities = pii_detector.anonymize(prompt)
            execution_time = time.time() - start_time
            
            result = {
                "is_valid": len(pii_entities) == 0,
                "risk_score": 1.0 if pii_entities else 0.0,
                "detected": len(pii_entities) > 0,
                "entities_found": len(pii_entities),
                "entity_types": list(set([e["type"] for e in pii_entities])) if pii_entities else [],
                "entities": pii_entities,
                "anonymized_prompt": anonymized_prompt,
                "anonymized": len(pii_entities) > 0,
                "execution_time": execution_time
            }
            
            logger.info(f"✅ [{thread_id}] PII scanner completed in {execution_time:.3f}s")
            return "pii", result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ [{thread_id}] PII scanner error: {str(e)}")
            return "pii", {
                "error": str(e),
                "is_valid": True,
                "risk_score": 0.0,
                "detected": False,
                "anonymized_prompt": prompt,
                "execution_time": execution_time
            }
    
    def scan_prompt_parallel(self, prompt: str) -> SecurityScanResult:
        """
        ⚡ PARALLEL SCAN: Run ALL security checks simultaneously
        
        This method:
        1. Creates separate threads for each scanner
        2. Runs all scanners at the same time
        3. Waits for all to complete
        4. Aggregates results
        
        Returns:
            SecurityScanResult with all scan results
        """
        scan_start_time = time.time()
        
        logger.info("="*80)
        logger.info("⚡⚡⚡ STARTING PARALLEL SECURITY SCAN ⚡⚡⚡")
        logger.info("="*80)
        
        results = {
            "is_safe": True,
            "detections": {},
            "risk_level": "SAFE",
            "message": "Prompt passed all security checks",
            "timestamp": datetime.utcnow().isoformat(),
            "scan_duration": 0.0
        }
        
        # Submit ALL scanners to thread pool at once
        futures = {}
        
        # Submit jailbreak/toxicity scanners
        for scanner_name, scanner in self.scanners.items():
            future = executor.submit(self._run_single_scanner, scanner_name, scanner, prompt)
            futures[future] = scanner_name
        
        # Submit PII scanner
        pii_future = executor.submit(self._run_pii_scanner, prompt)
        futures[pii_future] = "pii"
        
        logger.info(f"📤 Submitted {len(futures)} scanners to thread pool")
        
        # Wait for ALL scanners to complete
        max_risk_score = 0.0
        detected_threats = []
        anonymized_prompt = prompt  # Default to original
        
        for future in as_completed(futures):
            scanner_name, detection_result = future.result()
            results["detections"][scanner_name] = detection_result
            
            # Track anonymized prompt if PII detected
            if scanner_name == "pii" and detection_result.get("anonymized_prompt"):
                anonymized_prompt = detection_result["anonymized_prompt"]
            
            # Check if threat detected
            if not detection_result.get("is_valid", True) and scanner_name != "pii":
                results["is_safe"] = False
                detected_threats.append(scanner_name.replace("_", " ").title())
                max_risk_score = max(max_risk_score, detection_result.get("risk_score", 0.0))
        
        # Calculate total scan duration
        scan_duration = time.time() - scan_start_time
        results["scan_duration"] = scan_duration
        
        # Determine risk level and friendly messages
        if not results["is_safe"]:
            if max_risk_score >= 0.8:
                results["risk_level"] = "CRITICAL"
            elif max_risk_score >= 0.6:
                results["risk_level"] = "HIGH"
            else:
                results["risk_level"] = "MEDIUM"
            
            # Friendly user-facing messages based on threat type
            friendly_messages = {
                "Prompt Injection": "I'm sorry, but I cannot process this request. Please rephrase your question in a different way.",
                "Toxicity": "Please ask your question respectfully. I'm here to help when you communicate in a kind manner."
            }
            
            # Use specific message for single threat, or generic for multiple
            if len(detected_threats) == 1:
                results["message"] = friendly_messages.get(
                    detected_threats[0], 
                    "I'm unable to process this request. Please try rephrasing your question."
                )
            else:
                results["message"] = "I'm unable to process this request. Please rephrase your question respectfully and try again."
        
        # Store anonymized prompt in results
        results["anonymized_prompt"] = anonymized_prompt
        
        logger.info("="*80)
        logger.info(f"⚡ PARALLEL SCAN COMPLETED IN {scan_duration:.3f}s ⚡")
        logger.info("="*80)
        
        # Log individual scanner times
        for scanner_name, detection in results["detections"].items():
            exec_time = detection.get("execution_time", 0.0)
            logger.info(f"  ├─ {scanner_name}: {exec_time:.3f}s")
        logger.info("="*80 + "\n")
        
        return SecurityScanResult(**results)


# Initialize parallel scanner
detector = ParallelSecurityScanner()


async def call_openrouter(prompt: str, model: str = "openai/gpt-4o-mini", has_pii: bool = False) -> Dict[str, Any]:
    """Call OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Jailbreak-Protected LLM API"
    }
    
    messages = []
    
    if has_pii:
        system_message = {
            "role": "system",
            "content": "You are the iNextLabs AI Assistant, a helpful and knowledgeable virtual assistant representing iNextLabs. Your primary role is to answer questions about iNextLabs, its services, products, and expertise in AI, technology, and innovation. You are professional, friendly, and informative. When users ask about iNextLabs, provide detailed and accurate information about the company's offerings in areas such as AI solutions, software development, digital transformation, and technology consulting. If you don't have specific information about iNextLabs, politely let the user know and offer to help with related questions. Always maintain a professional yet approachable tone that reflects the innovative and customer-focused nature of iNextLabs. The user's message may contain privacy tokens in square brackets like [PERSON_1] or [EMAIL_ADDRESS_1]. These are system placeholders you must completely ignore. Treat the message as normal conversation and respond naturally without ever mentioning tokens, brackets, privacy, sensitive information, or redaction."
        }
        messages.append(system_message)
        
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"OpenRouter API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to LLM service: {str(e)}"
        )
    
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="connected",
        service="Jailbreak-Protected LLM API (Parallel Threading)",
        timestamp=datetime.utcnow().isoformat(),
        scanners_active=len(detector.scanners) + 1  # +1 for PII
    )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={
        200: {"model": ChatResponse, "description": "Successful response"},
        403: {"model": ErrorResponse, "description": "Security threat detected"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"}
    },
    tags=["Chat"]
)
async def chat(request: ChatRequest):
    """
    ⚡ PARALLEL SECURITY CHAT ENDPOINT ⚡
    
    Runs ALL security checks (Prompt Injection, Toxicity, PII) 
    simultaneously using threading for maximum speed.
    """
    try:
        request_start = time.time()
        
        # Load bot's security log
        bot_security_log = load_bot_security_log(request.bot_id)
        bot_security_log["total_prompts"] += 1
        
        logger.info(f"\n[Bot: {request.bot_id}] Processing prompt: {request.prompt[:100]}...")
        
        # ⚡⚡⚡ RUN ALL SECURITY CHECKS IN PARALLEL ⚡⚡⚡
        scan_results = detector.scan_prompt_parallel(request.prompt)
        
        # Extract results
        pii_detection = scan_results.detections.get("pii", {})
        pii_entities = pii_detection.get("entities", [])
        anonymized_prompt = scan_results.detections.get("pii", {}).get("anonymized_prompt", request.prompt)
        
        # Prepare security event log
        security_event = {
            "timestamp": datetime.utcnow().isoformat(),
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
            logger.warning(f"[Bot: {request.bot_id}] PII detected: {len(pii_entities)} entities found")
            bot_security_log["pii_detections"] += 1
            prompt_to_send = anonymized_prompt
        else:
            prompt_to_send = request.prompt

        # Check for Jailbreak/Toxicity (BLOCK if detected)
        if not scan_results.is_safe:
            logger.warning(f"[Bot: {request.bot_id}] Security threat detected - Risk level: {scan_results.risk_level}")
            
            bot_security_log["blocked_prompts"] += 1
            
            if scan_results.detections.get("prompt_injection", {}).get("detected"):
                bot_security_log["jailbreak_attempts"] += 1
            if scan_results.detections.get("toxicity", {}).get("detected"):
                bot_security_log["toxicity_detections"] += 1
            
            security_event["blocked"] = True
            security_event["block_reason"] = scan_results.message
            
            bot_security_log["security_events"].append(security_event)
            bot_security_log["last_updated"] = datetime.utcnow().isoformat()
            save_bot_security_log(request.bot_id, bot_security_log)
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,  # Return 200 instead of 403
                content={
                    "success": True,  # Keep success true for smooth UX
                    "response": scan_results.message,  # Return friendly message as response
                    "security_scan": {
                        "is_safe": False,
                        "risk_level": scan_results.risk_level,
                        "message": scan_results.message,
                        "timestamp": scan_results.timestamp
                    },
                    "model": request.model,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Prompt is safe - call LLM
        logger.info(f"[Bot: {request.bot_id}] Security check passed - forwarding to LLM")
        
        if not OPENROUTER_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenRouter API key not configured"
            )
        
        # Call OpenRouter API
        llm_response = await call_openrouter(prompt_to_send, request.model, has_pii=bool(pii_entities))
        
        assistant_message = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        security_event["llm_response"] = assistant_message
        security_event["model_used"] = request.model
        security_event["success"] = True
        
        bot_security_log["security_events"].append(security_event)
        bot_security_log["last_updated"] = datetime.utcnow().isoformat()
        save_bot_security_log(request.bot_id, bot_security_log)
        
        total_time = time.time() - request_start
        logger.info(f"[Bot: {request.bot_id}] ✅ Total request completed in {total_time:.3f}s\n")
        
        return ChatResponse(
            success=True,
            response=assistant_message,
            security_scan=scan_results,
            model=request.model,
            usage=llm_response.get("usage", {}),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Bot: {request.bot_id}] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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
async def delete_bot_security_log(bot_id: str):
    """Delete all security data for a specific bot session"""
    try:
        security_file = get_bot_security_file(bot_id)
        if security_file.exists():
            security_file.unlink()
            return {
                "success": True,
                "message": f"Security log deleted for bot_id: {bot_id}"
            }
        else:
            return {
                "success": False,
                "message": f"No security log found for bot_id: {bot_id}"
            }
    except Exception as e:
        logger.error(f"Failed to delete security log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete security log: {str(e)}"
        )


@app.get("/api/security", tags=["Security Logs"])
async def list_all_bot_sessions():
    """List all bot sessions with security logs"""
    try:
        security_files = list(SECURITY_STORAGE_DIR.glob("*.json"))
        bot_sessions = []
        
        for security_file in security_files:
            with open(security_file, 'r') as f:
                data = json.load(f)
                bot_sessions.append({
                    "bot_id": data.get("bot_id"),
                    "created_at": data.get("created_at"),
                    "last_updated": data.get("last_updated"),
                    "total_prompts": data.get("total_prompts", 0),
                    "blocked_prompts": data.get("blocked_prompts", 0),
                    "pii_detections": data.get("pii_detections", 0),
                    "jailbreak_attempts": data.get("jailbreak_attempts", 0),
                    "toxicity_detections": data.get("toxicity_detections", 0)
                })
        
        return {
            "total_sessions": len(bot_sessions),
            "sessions": bot_sessions
        }
    except Exception as e:
        logger.error(f"Failed to list bot sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bot sessions: {str(e)}"
        )

@app.post(
    "/api/scan",
    response_model=SecurityScanResult,
    tags=["Security"]
)
async def scan_only(request: ScanRequest):
    """
    ⚡ PARALLEL SCAN ENDPOINT ⚡
    
    Scan prompt with all security checks running simultaneously.
    Does not call LLM - only returns security scan results.
    """
    try:
        scan_results = detector.scan_prompt_parallel(request.prompt)
        return scan_results
        
    except Exception as e:
        logger.error(f"Scan error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """Get API statistics and configuration"""
    return StatsResponse(
        service="Jailbreak-Protected LLM API (Parallel Threading)",
        version="1.0.0",
        scanners={
            "prompt_injection": {
                "name": "Prompt Injection Scanner",
                "threshold": 0.8,
                "description": "Detects prompt injection and jailbreak attempts",
                "parallel": True
            },
            "toxicity": {
                "name": "Toxicity Scanner",
                "threshold": 0.5,
                "description": "Detects toxic and harmful content",
                "parallel": True
            },
            "pii": {
                "name": "PII Detection & Anonymization",
                "threshold": 0.5,
                "description": "Detects and anonymizes personal information",
                "parallel": True
            }
        },
        models_available=[
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet"
        ]
    )


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 80)
    logger.info("🚀 Starting Jailbreak-Protected LLM API - ⚡ PARALLEL THREADING MODE ⚡")
    logger.info("=" * 80)
    logger.info(f"✓ Loaded 3 security scanners (Prompt Injection, Toxicity, PII)")
    logger.info(f"✓ Thread pool initialized with {executor._max_workers} workers")
    logger.info("✓ ALL scanners run in PARALLEL for maximum speed")
    logger.info("✓ CORS enabled for React frontend")
    logger.info(f"✓ Security logs directory: {SECURITY_STORAGE_DIR}")
    logger.info("=" * 80)
    logger.info("⚡ PERFORMANCE MODE: All security checks run simultaneously! ⚡")
    logger.info("=" * 80 + "\n")
    
    if not OPENROUTER_API_KEY:
        logger.warning("⚠️  OPENROUTER_API_KEY not set! Set it as environment variable.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    executor.shutdown(wait=True)
    logger.info("ThreadPoolExecutor shut down successfully")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )