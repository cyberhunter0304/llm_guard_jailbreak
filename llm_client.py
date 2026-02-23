"""
LLM Client Module
Handles communication with Azure AI Foundry (primary) or OpenRouter (fallback).
OpenRouter uses an OpenAI-compatible endpoint so the payload shape is identical.
"""
import logging
import httpx
from typing import Dict, Any
from fastapi import HTTPException, status
from config import (
    AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT, AZURE_API_VERSION,
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
)

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _azure_url(deployment: str) -> str:
    base = AZURE_ENDPOINT.rstrip("/")
    return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={AZURE_API_VERSION}"


def _use_azure() -> bool:
    return bool(AZURE_API_KEY and AZURE_ENDPOINT)


def _use_openrouter() -> bool:
    return bool(OPENROUTER_API_KEY)


async def call_llm(
    prompt: str,
    model: str = None,
    has_pii: bool = False,
) -> Dict[str, Any]:
    """
    Call the LLM — Azure first, OpenRouter as fallback.
    """
    messages = []

    if has_pii:
        messages.append({
            "role": "system",
            "content": (
                "The following message may contain anonymized PII placeholders "
                "such as [PERSON_1] or [EMAIL_1]. Treat them as opaque tokens "
                "and respond helpfully without referencing them."
            ),
        })

    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages":    messages,
        "temperature": 0.7,
        "max_tokens":  1000,
    }

    # Try Azure first
    if _use_azure():
        deployment = model or AZURE_DEPLOYMENT
        url     = _azure_url(deployment)
        headers = {
            "api-key":      AZURE_API_KEY,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                logger.info(f"[llm] Azure responded OK (deployment={deployment})")
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"[llm] Azure HTTP {e.response.status_code} — falling back to OpenRouter")
            if not _use_openrouter():
                raise HTTPException(status_code=503, detail=f"Azure LLM returned {e.response.status_code}: {e.response.text}")
        except httpx.HTTPError as e:
            logger.warning(f"[llm] Azure connection error: {e} — falling back to OpenRouter")
            if not _use_openrouter():
                raise HTTPException(status_code=503, detail=f"Failed to connect to Azure LLM: {e}")

    # Fallback: OpenRouter
    if _use_openrouter():
        or_model = OPENROUTER_MODEL
        logger.info(f"[llm] Using OpenRouter (model={or_model})")
        payload["model"] = or_model
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://inextlabs.com",
            "X-Title":       "Guardrail Cloud Service",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                response.raise_for_status()
                logger.info("[llm] OpenRouter responded OK")
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[llm] OpenRouter HTTP {e.response.status_code}: {e.response.text}")
            raise HTTPException(status_code=503, detail=f"OpenRouter returned {e.response.status_code}: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"[llm] OpenRouter connection error: {e}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to OpenRouter: {e}")

    raise HTTPException(
        status_code=500,
        detail="No LLM provider configured. Set AZURE_API_KEY or OPENROUTER_API_KEY in .env",
    )