"""
Language Detection Scanner
--------------------------
Detects the language of a prompt using the XLM-RoBERTa model:
  papluca/xlm-roberta-base-language-detection

Supports 20 languages:
  ar, bg, de, el, en, es, fr, hi, it, ja, nl, pl, pt, ru,
  sw, th, tr, ur, vi, zh

Configuration (in config.py SCANNER_CONFIG):
  language_detection_enabled      bool   — bypass scanner without unloading model
  language_detection_model        str    — HuggingFace model ID
  language_confidence_threshold   float  — ignore detections below this confidence
  allowed_languages               list   — ISO-639-1 codes; empty = allow all
  blocked_languages               list   — always blocked regardless of allow list

Eager loading: the pipeline is initialised at module import time so the
first real request doesn't pay the model-load penalty.

Thread-safe: HuggingFace pipelines are not thread-safe by default, so we
protect the call with a threading.Lock().
"""
import logging
import threading
import time
from typing import Dict, Any, List, Optional

from config import SCANNER_CONFIG

logger = logging.getLogger(__name__)

_PIPELINE      = None
_PIPELINE_LOCK = threading.Lock()
_LOAD_LOCK     = threading.Lock()
_LOADED        = False

# Human-readable language names for nicer log messages / API responses
LANGUAGE_NAMES: Dict[str, str] = {
    "ar": "Arabic",    "bg": "Bulgarian",  "de": "German",
    "el": "Greek",     "en": "English",    "es": "Spanish",
    "fr": "French",    "hi": "Hindi",      "it": "Italian",
    "ja": "Japanese",  "nl": "Dutch",      "pl": "Polish",
    "pt": "Portuguese","ru": "Russian",    "sw": "Swahili",
    "th": "Thai",      "tr": "Turkish",    "ur": "Urdu",
    "vi": "Vietnamese","zh": "Chinese",
}


def _load_pipeline() -> None:
    """Load the XLM-RoBERTa language detection pipeline at module import time."""
    global _PIPELINE, _LOADED

    with _LOAD_LOCK:
        if _LOADED:
            return

        model_id  = SCANNER_CONFIG.get(
            "language_detection_model",
            "papluca/xlm-roberta-base-language-detection",
        )
        try:
            from transformers import pipeline as hf_pipeline
            logger.info(f"[LanguageScanner] Loading model: {model_id} ...")
            t0 = time.time()
            _PIPELINE = hf_pipeline(
                "text-classification",
                model=model_id,
                top_k=1,          # return only the top prediction
                truncation=True,
                max_length=512,
            )
            logger.info(f"[LanguageScanner] ✓ Model loaded in {time.time()-t0:.2f}s")
            _LOADED = True
        except Exception as exc:
            logger.error(f"[LanguageScanner] Failed to load model: {exc}")
            _PIPELINE = None
            _LOADED   = True   # mark as done so we don't retry on every request


# Eagerly load at import time (server startup)
logger.info("[LanguageScanner] Starting eager model load …")
_load_pipeline()
logger.info("[LanguageScanner] Model load complete.")


class LanguageScanner:
    """
    Detects the language of a prompt and optionally blocks/allows it.

    scan() always returns a result dict even if the underlying model
    failed to load — in that case detection is skipped gracefully.
    """

    def scan(self, text: str) -> Dict[str, Any]:
        """
        Detect language and apply allow/block policy.

        Returns:
        {
            "detected_language":   str,    # ISO-639-1 code, e.g. "en"
            "language_name":       str,    # human-readable, e.g. "English"
            "confidence":          float,  # model confidence 0–1
            "is_allowed":          bool,   # False → should be blocked
            "is_valid":            bool,   # True when allowed (llm-guard convention)
            "risk_score":          float,  # 1.0 if blocked, 0.0 if allowed
            "policy_reason":       str,    # why blocked/allowed
            "enabled":             bool,   # False if scanner is disabled in config
        }
        """
        enabled = SCANNER_CONFIG.get("language_detection_enabled", True)
        if not enabled:
            return self._passthrough_result("Scanner disabled in config")

        if _PIPELINE is None:
            return self._passthrough_result("Model not loaded — skipping")

        if not text or not text.strip():
            return self._passthrough_result("Empty text")

        try:
            # Truncate to avoid OOM on huge prompts; model max is 512 tokens
            scan_text = text[:2000]

            with _PIPELINE_LOCK:
                preds = _PIPELINE(scan_text)

            # pipeline returns [[{"label": "en", "score": 0.99}]] when top_k=1
            if preds and isinstance(preds[0], list):
                top = preds[0][0]
            elif preds and isinstance(preds[0], dict):
                top = preds[0]
            else:
                return self._passthrough_result("Unexpected pipeline output")

            lang_code  = top["label"].lower()[:2]   # "en_XX" → "en"
            confidence = float(top["score"])

            threshold = SCANNER_CONFIG.get("language_confidence_threshold", 0.7)
            if confidence < threshold:
                return self._passthrough_result(
                    f"Low confidence ({confidence:.2f} < {threshold}) — language undetermined"
                )

            lang_name   = LANGUAGE_NAMES.get(lang_code, lang_code.upper())
            allowed     = self._apply_policy(lang_code)
            policy_desc = self._policy_reason(lang_code, allowed)

            return {
                "detected_language": lang_code,
                "language_name":     lang_name,
                "confidence":        round(confidence, 4),
                "is_allowed":        allowed,
                "is_valid":          allowed,
                "risk_score":        0.0 if allowed else 1.0,
                "policy_reason":     policy_desc,
                "enabled":           True,
            }

        except Exception as exc:
            logger.error(f"[LanguageScanner] Error: {exc}")
            return self._passthrough_result(f"Scanner error: {exc}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_policy(lang_code: str) -> bool:
        """Return True if the language is allowed by the current policy."""
        blocked  = [c.lower() for c in SCANNER_CONFIG.get("blocked_languages", [])]
        allowed  = [c.lower() for c in SCANNER_CONFIG.get("allowed_languages",  [])]

        if lang_code in blocked:
            return False
        if allowed and lang_code not in allowed:
            return False
        return True

    @staticmethod
    def _policy_reason(lang_code: str, is_allowed: bool) -> str:
        if is_allowed:
            return f"Language '{lang_code}' is permitted"
        blocked = [c.lower() for c in SCANNER_CONFIG.get("blocked_languages", [])]
        allowed = [c.lower() for c in SCANNER_CONFIG.get("allowed_languages",  [])]
        if lang_code in blocked:
            return f"Language '{lang_code}' is explicitly blocked"
        if allowed:
            return (
                f"Language '{lang_code}' is not in the allowed list: {allowed}"
            )
        return f"Language '{lang_code}' blocked by policy"

    @staticmethod
    def _passthrough_result(reason: str) -> Dict[str, Any]:
        return {
            "detected_language": None,
            "language_name":     None,
            "confidence":        None,
            "is_allowed":        True,
            "is_valid":          True,
            "risk_score":        0.0,
            "policy_reason":     reason,
            "enabled":           SCANNER_CONFIG.get("language_detection_enabled", True),
        }
