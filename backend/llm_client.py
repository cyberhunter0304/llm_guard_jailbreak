"""
LLM Client Module
Handles communication with OpenRouter API
"""
import logging
import httpx
from typing import Dict, Any
from fastapi import HTTPException, status
from config import OPENROUTER_API_KEY, OPENROUTER_URL

logger = logging.getLogger(__name__)


async def call_openrouter(prompt: str, model: str = "openai/gpt-4o-mini", has_pii: bool = False) -> Dict[str, Any]:
    """Call OpenRouter API - Uses async client for better concurrency"""
    
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenRouter API key not configured"
        )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://0.0.0.0:8000",
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