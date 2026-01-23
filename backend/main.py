"""
Jailbreak-Protected LLM API Endpoint
FastAPI with OpenRouter GPT-4o mini integration and comprehensive jailbreak detection
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from llm_guard.input_scanners import PromptInjection, Language, Toxicity
from llm_guard.input_scanners.language import MatchType
import httpx
import os
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List

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

# CORS Configuration - Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scanners
prompt_injection_scanner = PromptInjection(threshold=0.8)
language_scanner = Language(valid_languages=["en"], match_type=MatchType.FULL, threshold=0.8)
toxicity_scanner = Toxicity(threshold=0.5)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# Pydantic models
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt")
    model: str = Field(default="openai/gpt-4o-mini", description="LLM model to use")

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


class ScannerDetection(BaseModel):
    is_valid: bool
    risk_score: float
    detected: bool
    error: Optional[str] = None


class SecurityScanResult(BaseModel):
    is_safe: bool
    detections: Dict[str, Any]
    risk_level: str
    message: str
    timestamp: str


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


class JailbreakDetector:
    """Comprehensive jailbreak detection system"""
    
    def __init__(self):
        self.scanners = {
            "prompt_injection": prompt_injection_scanner,
            "language": language_scanner,
            "toxicity": toxicity_scanner
        }
    
    def scan_prompt(self, prompt: str) -> SecurityScanResult:
        """
        Scan prompt with all available scanners
        
        Returns:
            SecurityScanResult: Comprehensive scan results
        """
        results = {
            "is_safe": True,
            "detections": {},
            "risk_level": "SAFE",
            "message": "Prompt passed all security checks",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        max_risk_score = 0.0
        detected_threats = []
        
        for scanner_name, scanner in self.scanners.items():
            try:
                sanitized, is_valid, risk_score = scanner.scan(prompt)
                
                results["detections"][scanner_name] = {
                    "is_valid": is_valid,
                    "risk_score": float(risk_score),
                    "detected": not is_valid
                }
                
                if not is_valid:
                    results["is_safe"] = False
                    detected_threats.append(scanner_name.replace("_", " ").title())
                    max_risk_score = max(max_risk_score, risk_score)
                
            except Exception as e:
                logger.error(f"Scanner {scanner_name} error: {str(e)}")
                results["detections"][scanner_name] = {
                    "error": str(e),
                    "is_valid": True,
                    "risk_score": 0.0
                }
        
        # Determine risk level
        if not results["is_safe"]:
            if max_risk_score >= 0.8:
                results["risk_level"] = "CRITICAL"
            elif max_risk_score >= 0.6:
                results["risk_level"] = "HIGH"
            else:
                results["risk_level"] = "MEDIUM"
            
            results["message"] = (
                f"⚠️ Security threat detected! "
                f"Your prompt triggered: {', '.join(detected_threats)}. "
                f"This appears to be a jailbreak attempt and has been blocked."
            )
        
        return SecurityScanResult(**results)


detector = JailbreakDetector()


async def call_openrouter(prompt: str, model: str = "openai/gpt-4o-mini") -> Dict[str, Any]:
    """
    Call OpenRouter API with GPT-4o mini (async)
    
    Args:
        prompt: User prompt
        model: Model identifier
        
    Returns:
        dict: API response
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Jailbreak-Protected LLM API"
    }
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
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
        status="healthy",
        service="Jailbreak-Protected LLM API",
        timestamp=datetime.utcnow().isoformat(),
        scanners_active=len(detector.scanners)
    )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={
        200: {"model": ChatResponse, "description": "Successful response"},
        403: {"model": ErrorResponse, "description": "Jailbreak attempt detected"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"}
    },
    tags=["Chat"]
)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with jailbreak protection
    
    Scans the prompt for security threats before forwarding to the LLM.
    """
    try:
        # Security scan
        logger.info(f"Scanning prompt: {request.prompt[:100]}...")
        scan_results = detector.scan_prompt(request.prompt)
        
        # Main Jailbreak checker
        if not scan_results.is_safe:
            logger.warning(f"Jailbreak detected - Risk level: {scan_results.risk_level}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "error": "Jailbreak attempt detected",
                    "message": scan_results.message,
                    "security_scan": scan_results.dict(),
                    "blocked": True
                }
            )
        
        # Prompt is safe - call LLM
        logger.info("Security check passed - forwarding to LLM")
        
        if not OPENROUTER_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable"
            )
        
        # Call OpenRouter API
        llm_response = await call_openrouter(request.prompt, request.model)
        
        # Extract response and return
        assistant_message = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
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
        logger.error(f"Unexpected error: {str(e)}")
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
    """
    Scan endpoint - only check for jailbreaks without calling LLM
    
    Useful for testing security measures or pre-validating prompts.
    """
    try:
        scan_results = detector.scan_prompt(request.prompt)
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
        service="Jailbreak-Protected LLM API",
        version="1.0.0",
        scanners={
            "prompt_injection": {
                "name": "Prompt Injection Scanner",
                "threshold": 0.5,
                "description": "Detects prompt injection and jailbreak attempts"
            },
            "language": {
                "name": "Language Scanner",
                "valid_languages": ["en"],
                "description": "Validates language and detects suspicious patterns"
            },
            "toxicity": {
                "name": "Toxicity Scanner",
                "threshold": 0.5,
                "description": "Detects toxic and harmful content"
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
    logger.info("🚀 Starting Jailbreak-Protected LLM API (FastAPI)")
    logger.info("=" * 80)
    logger.info(f"✓ Loaded {len(detector.scanners)} security scanners")
    logger.info("✓ CORS enabled for React frontend")
    logger.info("✓ Endpoints:")
    logger.info("  - GET  /health       - Health check")
    logger.info("  - POST /api/chat     - Protected chat endpoint")
    logger.info("  - POST /api/scan     - Security scan only")
    logger.info("  - GET  /api/stats    - API statistics")
    logger.info("  - GET  /docs         - Interactive API documentation")
    logger.info("  - GET  /redoc        - Alternative API documentation")
    logger.info("=" * 80)
    
    if not OPENROUTER_API_KEY:
        logger.warning("⚠️  OPENROUTER_API_KEY not set! Set it as environment variable.")
        logger.warning("   Export it: export OPENROUTER_API_KEY='your-key-here'")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )