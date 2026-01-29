"""
Security Scanner Module
Concurrent-safe security scanning with multiple threat detectors

================================================================================
🔧 HOW TO ADD A NEW SCANNER - COMPLETE GUIDE
================================================================================

Follow these steps to add a new security scanner to the system:

STEP 1: Install and Import (THIS FILE - security_scanner.py)
------------------------------------------------------------
1. Install the scanner package if needed
2. Import at the top of this file
   Example: from llm_guard.input_scanners import BanTopics, Secrets

STEP 2: Configure Threshold (config.py)
----------------------------------------
1. Add threshold to SCANNER_CONFIG dictionary
   Example: "ban_topics_threshold": 0.7

STEP 3: Initialize Scanner (THIS FILE - Lines ~30-50)
------------------------------------------------------
1. Create scanner instance with threshold from config
   Example: ban_topics_scanner = BanTopics(topics=["violence"], threshold=SCANNER_CONFIG["ban_topics_threshold"])

STEP 4: Register Scanner (THIS FILE - ConcurrentSecurityScanner.__init__)
--------------------------------------------------------------------------
1. Add to self.scanners dictionary
   Example: "ban_topics": ban_topics_scanner

STEP 5: Add Friendly Message (THIS FILE - scan_prompt_parallel method)
-----------------------------------------------------------------------
1. Add user-friendly error message to friendly_messages dict
   Example: "Ban Topics": "This topic is not allowed. Please ask about something else."

STEP 6: Track Statistics (main.py - chat endpoint)
---------------------------------------------------
1. Add detection counter increment in the blocked prompts section
   Example: if scan_results.detections.get("ban_topics", {}).get("detected"):
                bot_security_log["banned_topics_detections"] += 1

STEP 7: Initialize Statistics (storage.py - load_bot_security_log)
-------------------------------------------------------------------
1. Add counter to default bot security log structure
   Example: "banned_topics_detections": 0

STEP 8: Update API Stats (main.py - get_stats endpoint)
--------------------------------------------------------
1. Add scanner info to the stats response
   Example: "ban_topics": {"name": "Banned Topics", "threshold": 0.7, ...}

STEP 9: Update Session Listing (storage.py - list_all_bot_sessions)
--------------------------------------------------------------------
1. Add stat to bot_sessions.append() dictionary
   Example: "banned_topics_detections": data.get("banned_topics_detections", 0)

OPTIONAL: Custom Scanner Method (THIS FILE)
--------------------------------------------
If your scanner needs special handling (like PII detector):
1. Create a custom _run_your_scanner method
2. Submit it separately in scan_prompt_parallel
   Example: custom_future = executor.submit(self._run_custom_scanner, prompt)

================================================================================
"""
import logging
import time
from typing import Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from llm_guard.input_scanners import PromptInjection, Toxicity
from pii_detector import ThreadSafePIIDetector
from models import SecurityScanResult
from config import SCANNER_CONFIG
from datetime_utils import now

logger = logging.getLogger(__name__)

# ============================================================================
# SCANNER INITIALIZATION - ADD NEW SCANNERS HERE
# ============================================================================
# Initialize SHARED scanners (thread-safe for reading)
prompt_injection_scanner = PromptInjection(threshold=SCANNER_CONFIG["prompt_injection_threshold"])
toxicity_scanner = Toxicity(threshold=SCANNER_CONFIG["toxicity_threshold"])

# 🔧 ADD MORE SCANNERS HERE:
# Example scanners you can add from llm_guard.input_scanners:
# - BanSubstrings: Block specific words/phrases
# - BanTopics: Block specific topics
# - Code: Detect code in prompts
# - Language: Detect language mismatches
# - PromptInjectionV2: Alternative prompt injection detector
# - Regex: Custom regex pattern matching
# - Secrets: Detect API keys, passwords, tokens
# - Sentiment: Detect sentiment (positive/negative)
# - TokenLimit: Limit token count
# 
# Example:
# from llm_guard.input_scanners import BanTopics, Secrets
# ban_topics_scanner = BanTopics(topics=["violence", "hate"], threshold=0.7)
# secrets_scanner = Secrets(redact_mode="all")
# ============================================================================

# Increased thread pool for handling many concurrent requests
executor = ThreadPoolExecutor(
    max_workers=SCANNER_CONFIG["thread_pool_workers"], 
    thread_name_prefix="SecurityScanner"
)


class ConcurrentSecurityScanner:
    """
    Concurrent-Safe Security Scanner
    Handles multiple bot requests simultaneously
    """
    
    def __init__(self):
        # ====================================================================
        # REGISTER SCANNERS - ADD YOUR NEW SCANNERS TO THIS DICTIONARY
        # ====================================================================
        self.scanners = {
            "prompt_injection": prompt_injection_scanner,
            "toxicity": toxicity_scanner
            # 🔧 ADD NEW SCANNERS HERE:
            # "ban_topics": ban_topics_scanner,
            # "secrets": secrets_scanner,
            # "code_detection": code_scanner,
            # "sentiment": sentiment_scanner,
        }
        # ====================================================================
    
    def _run_single_scanner(self, scanner_name: str, scanner, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Execute a single scanner in a thread"""
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
            
            logger.debug(f"{scanner_name} completed in {execution_time:.3f}s")
            return scanner_name, result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{scanner_name} error: {str(e)}")
            return scanner_name, {
                "error": str(e),
                "is_valid": True,
                "risk_score": 0.0,
                "execution_time": execution_time
            }
    
    def _run_pii_scanner(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Execute PII scanner with isolated instance"""
        start_time = time.time()
        
        try:
            # Each call gets its own detector instance
            anonymized_prompt, pii_entities = ThreadSafePIIDetector.anonymize(prompt)
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
                "execution_time": execution_time,
                "entity_count": len(pii_entities)
            }
            
            logger.debug(f"PII scanner completed in {execution_time:.3f}s")
            return "pii", result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"PII scanner error: {str(e)}")
            return "pii", {
                "error": str(e),
                "is_valid": True,
                "risk_score": 0.0,
                "detected": False,
                "anonymized_prompt": prompt,
                "execution_time": execution_time
            }
    
    def scan_prompt_parallel(self, prompt: str, bot_id: str = "unknown") -> SecurityScanResult:
        """
        Run ALL security checks in parallel - THREAD SAFE
        Each request gets isolated PII scanner instance
        """
        scan_start_time = time.time()
        
        logger.debug(f"[Bot: {bot_id}] Starting parallel security scan")
        
        results = {
            "is_safe": True,
            "detections": {},
            "risk_level": "SAFE",
            "message": "Prompt passed all security checks",
            "timestamp": now(),
            "scan_duration": 0.0
        }
        
        # Submit ALL scanners to thread pool
        futures = {}
        
        # ====================================================================
        # SCANNER EXECUTION - Scanners are submitted to thread pool here
        # ====================================================================
        # Submit jailbreak/toxicity scanners
        for scanner_name, scanner in self.scanners.items():
            future = executor.submit(self._run_single_scanner, scanner_name, scanner, prompt)
            futures[future] = scanner_name
        
        # Submit PII scanner (gets its own isolated instance)
        pii_future = executor.submit(self._run_pii_scanner, prompt)
        futures[pii_future] = "pii"
        
        # 🔧 ADD CUSTOM SCANNER EXECUTION HERE (if needed):
        # If you have scanners that need special handling (like PII), add them here:
        # Example:
        # custom_future = executor.submit(self._run_custom_scanner, prompt)
        # futures[custom_future] = "custom_scanner_name"
        # ====================================================================
        
        # Wait for ALL scanners to complete
        max_risk_score = 0.0
        detected_threats = []
        anonymized_prompt = prompt
        
        for future in as_completed(futures):
            scanner_name, detection_result = future.result()
            results["detections"][scanner_name] = detection_result
            
            # Track anonymized prompt
            if scanner_name == "pii" and detection_result.get("anonymized_prompt"):
                anonymized_prompt = detection_result["anonymized_prompt"]
            
            # Check for threats (excluding PII which is just anonymized)
            if not detection_result.get("is_valid", True) and scanner_name != "pii":
                results["is_safe"] = False
                detected_threats.append(scanner_name.replace("_", " ").title())
                max_risk_score = max(max_risk_score, detection_result.get("risk_score", 0.0))
            
            # 🔧 CUSTOM THREAT HANDLING FOR NEW SCANNERS:
            # Add special handling for specific scanners here if needed
            # Example: Different actions for different scanner types
            # if scanner_name == "secrets" and detection_result.get("detected"):
            #     results["contains_secrets"] = True
            # if scanner_name == "ban_topics" and detection_result.get("detected"):
            #     results["banned_topic_found"] = True
            # ====================================================================
        
        # Calculate total scan duration
        scan_duration = time.time() - scan_start_time
        results["scan_duration"] = scan_duration
        
        # Determine risk level and messages
        if not results["is_safe"]:
            if max_risk_score >= 0.8:
                results["risk_level"] = "CRITICAL"
            elif max_risk_score >= 0.6:
                results["risk_level"] = "HIGH"
            else:
                results["risk_level"] = "MEDIUM"
            
            friendly_messages = {
                "Prompt Injection": "I'm sorry, but I cannot process this request. Please rephrase your question in a different way.",
                "Toxicity": "Please ask your question respectfully. I'm here to help when you communicate in a kind manner."
                # 🔧 ADD FRIENDLY MESSAGES FOR NEW SCANNERS:
                # These messages are shown to users when their prompt is blocked
                # "Ban Topics": "This topic is not allowed. Please ask about something else.",
                # "Secrets": "Your message contains sensitive information. Please remove any passwords or API keys.",
                # "Code Detection": "Code execution is not allowed in prompts. Please rephrase your question.",
                # "Sentiment": "Your message seems concerning. Please reach out if you need support.",
                # ====================================================================
            }
            
            if len(detected_threats) == 1:
                results["message"] = friendly_messages.get(
                    detected_threats[0], 
                    "I'm unable to process this request. Please try rephrasing your question."
                )
            else:
                results["message"] = "I'm unable to process this request. Please rephrase your question respectfully and try again."
        
        results["anonymized_prompt"] = anonymized_prompt
        
        logger.debug(f"[Bot: {bot_id}] Scan completed in {scan_duration:.3f}s")
        
        return SecurityScanResult(**results)


def shutdown_scanner():
    """Shutdown the thread pool executor"""
    executor.shutdown(wait=True)
    logger.info("SecurityScanner ThreadPoolExecutor shut down successfully")
