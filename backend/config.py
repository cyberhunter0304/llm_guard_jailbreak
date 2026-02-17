"""
Configuration Module
Centralized configuration for the Guardrail Cloud Service
"""
import os
from pathlib import Path

# Load .env file automatically — searches current dir and all parent dirs
# so it works whether uvicorn is launched from /backend or the project root.
try:
    from dotenv import load_dotenv, find_dotenv
    _env_file = find_dotenv(usecwd=True)
    if _env_file:
        load_dotenv(_env_file, override=True)
        print(f"[config] Loaded .env from: {_env_file}")
    else:
        print("[config] No .env file found — relying on system environment variables")
except ImportError:
    print("[config] python-dotenv not installed — run: pip install python-dotenv")

# ============================================================================
# MongoDB Configuration - CUSTOMIZE HERE
# ============================================================================

# MongoDB Connection URI
# Examples:
# - Local: "mongodb://localhost:27017/"
# - Atlas: "mongodb+srv://user:password@cluster.mongodb.net/"
# - Replica Set: "mongodb://host1:27017,host2:27017,host3:27017/?replicaSet=rs0"
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

# Warn loudly at import time if the required env vars are missing
import warnings as _warnings
if not MONGODB_URI:
    _warnings.warn(
        "MONGODB_URI environment variable is not set. "
        "MongoDB features will fail. Add it to your .env file.",
        RuntimeWarning,
        stacklevel=2,
    )
if not MONGODB_DATABASE:
    _warnings.warn(
        "MONGODB_DATABASE environment variable is not set. "
        "MongoDB features will fail. Add it to your .env file.",
        RuntimeWarning,
        stacklevel=2,
    )

# Collection Names
# The external app writes to this collection:
MONGODB_CONVERSATIONS_COLLECTION = "messages"

# Internal collections (security results and thread summaries)
MONGODB_SECURITY_LOGS_COLLECTION = "security_logs"
MONGODB_THREAD_SUMMARIES_COLLECTION = "thread_summaries"

# ============================================================================
# Local Storage Configuration
# ============================================================================

# Directory for storing security logs as JSON files
SECURITY_STORAGE_DIR = Path("security_logs")
SECURITY_STORAGE_DIR.mkdir(exist_ok=True)

# ============================================================================
# LLM Provider Configuration
# ============================================================================

# Choose provider: "openrouter" or "azure"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")

# OpenRouter Configuration (Legacy)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Azure AI Foundry Configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT", "")  # e.g., https://llm-guard-foundry.openai.azure.com/
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "")
AZURE_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT", "gpt-4-turbo")  # Deployment name
AZURE_PROJECT_ID = os.getenv("AZURE_PROJECT_ID", "")
AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING", "")

# ============================================================================
# CORS Configuration
# ============================================================================

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://0.0.0.0:8000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://192.168.68.111:3001",
    "http://192.168.68.111:3000",
    "*"  # Allow all origins for development
]

# ============================================================================
# Scanner Configuration
# ============================================================================

SCANNER_CONFIG = {
    "prompt_injection_threshold": 0.8,
    "toxicity_threshold": 0.5,
    "pii_threshold": 0.5,
    "secrets_threshold": 0.0,  # Binary detection for API keys, passwords, tokens
    "thread_pool_workers": 20
}

# ============================================================================
# API Configuration
# ============================================================================

API_CONFIG = {
    "title": "Jailbreak-Protected LLM API - Concurrent",
    "description": "Secure LLM API with comprehensive jailbreak detection - Handles multiple concurrent bots",
    "version": "2.0.0",
    "docs_url": "/docs",
    "redoc_url": "/redoc"
}

# LLM Models
AVAILABLE_MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet"
]

# Logging Configuration
LOG_LEVEL = "INFO"