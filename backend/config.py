"""
Configuration Module
Centralized configuration for the Guardrail Cloud Service
"""
import os
from pathlib import Path

# Security Storage
SECURITY_STORAGE_DIR = Path("security_logs")
SECURITY_STORAGE_DIR.mkdir(exist_ok=True)

# LLM Provider Configuration
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

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://0.0.0.0:8000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://192.168.68.111:3001",
    "http://192.168.68.111:3000"
]

# Scanner Configuration
SCANNER_CONFIG = {
    "prompt_injection_threshold": 0.8,
    "toxicity_threshold": 0.5,
    "pii_threshold": 0.5,
    "secrets_threshold": 0.0,  # Binary detection for API keys, passwords, tokens
    "thread_pool_workers": 20
    # 🔧 ADD NEW SCANNER THRESHOLDS HERE:
    # "ban_topics_threshold": 0.7,
    # "code_detection_threshold": 0.6,
    # "sentiment_threshold": 0.5,
    # "language_match_threshold": 0.8,
    # ====================================================================
}

# API Configuration
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