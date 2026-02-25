"""
Storage Module
Thread-safe file operations for security logs

Structure per file: security_logs/{thread_id}.json
Each file contains ALL messages for a single thread.
Messages are deduplicated via processed_message_ids.
"""
import json
import threading
from pathlib import Path
from typing import Dict, Any
from config import SECURITY_STORAGE_DIR, DEFAULT_BOT_ID
from datetime_utils import now

# Thread-safe file operations lock
file_lock = threading.Lock()


def get_thread_security_file(thread_id: str) -> Path:
    """Get the security log file path for a thread"""
    return SECURITY_STORAGE_DIR / f"{thread_id}.json"


def _default_security_log(thread_id: str, bot_id: str = DEFAULT_BOT_ID) -> dict:
    """Default empty security log structure for a new thread"""
    return {
        "bot_id":               bot_id,
        "thread_id":            thread_id,
        "created_at":           now(),
        "last_updated":         now(),
        "security_events":      [],
        "processed_message_ids": [],
        "total_prompts":        0,
        "blocked_prompts":      0,
        "pii_detections":       0,
        "jailbreak_attempts":   0,
        "toxicity_detections":  0,
        "secrets_detections":   0,
    }


def load_thread_security_log(thread_id: str) -> dict:
    """Load security log for a thread - THREAD SAFE"""
    security_file = get_thread_security_file(thread_id)
    with file_lock:
        if security_file.exists():
            with open(security_file, "r") as f:
                data = json.load(f)
            if "processed_message_ids" not in data:
                data["processed_message_ids"] = []
            return data
        return _default_security_log(thread_id)


def save_thread_security_log(thread_id: str, security_data: dict):
    """Save security log for a thread - THREAD SAFE"""
    security_file = get_thread_security_file(thread_id)
    with file_lock:
        with open(security_file, "w") as f:
            json.dump(security_data, f, indent=2)


def append_security_event(
    thread_id: str,
    message_id: str,
    security_event: dict,
    is_blocked: bool,
    has_pii: bool,
    has_jailbreak: bool,
    has_toxicity: bool,
    has_secrets: bool,
    bot_id: str = DEFAULT_BOT_ID,
) -> bool:
    """
    Atomically append a security event to the thread log.
    Returns True if appended, False if duplicate (already processed).

    Each thread gets its own file: security_logs/{thread_id}.json
    """
    security_file = get_thread_security_file(thread_id)

    with file_lock:
        if security_file.exists():
            with open(security_file, "r") as f:
                log = json.load(f)
            if "processed_message_ids" not in log:
                log["processed_message_ids"] = []
        else:
            log = _default_security_log(thread_id, bot_id)

        if message_id in log["processed_message_ids"]:
            return False

        log["security_events"].append(security_event)
        log["processed_message_ids"].append(message_id)

        log["total_prompts"]       = log.get("total_prompts",       0) + 1
        if is_blocked:
            log["blocked_prompts"] = log.get("blocked_prompts",     0) + 1
        if has_pii:
            log["pii_detections"]  = log.get("pii_detections",      0) + 1
        if has_jailbreak:
            log["jailbreak_attempts"]  = log.get("jailbreak_attempts",  0) + 1
        if has_toxicity:
            log["toxicity_detections"] = log.get("toxicity_detections", 0) + 1
        if has_secrets:
            log["secrets_detections"]  = log.get("secrets_detections",  0) + 1

        log["last_updated"] = now()

        with open(security_file, "w") as f:
            json.dump(log, f, indent=2)

    return True


def is_message_processed(thread_id: str, message_id: str) -> bool:
    """Quick check if a messageId was already processed for this thread."""
    security_file = get_thread_security_file(thread_id)
    with file_lock:
        if not security_file.exists():
            return False
        with open(security_file, "r") as f:
            data = json.load(f)
        return message_id in data.get("processed_message_ids", [])


def delete_thread_security_log(thread_id: str) -> Dict[str, Any]:
    """Delete security log for a thread - THREAD SAFE"""
    security_file = get_thread_security_file(thread_id)
    with file_lock:
        if security_file.exists():
            security_file.unlink()
            return {"success": True,  "message": f"Deleted log for thread_id: {thread_id}"}
        return {"success": False, "message": f"No log found for thread_id: {thread_id}"}


def list_all_threads() -> Dict[str, Any]:
    """List all threads that have security logs - THREAD SAFE"""
    threads = []
    with file_lock:
        for f in sorted(SECURITY_STORAGE_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                threads.append({
                    "bot_id":              data.get("bot_id",    DEFAULT_BOT_ID),
                    "thread_id":           data.get("thread_id", f.stem),
                    "created_at":          data.get("created_at"),
                    "last_updated":        data.get("last_updated"),
                    "total_prompts":       data.get("total_prompts",       0),
                    "blocked_prompts":     data.get("blocked_prompts",     0),
                    "pii_detections":      data.get("pii_detections",      0),
                    "jailbreak_attempts":  data.get("jailbreak_attempts",  0),
                    "toxicity_detections": data.get("toxicity_detections", 0),
                    "secrets_detections":  data.get("secrets_detections",  0),
                })
            except Exception:
                pass
    return {"total_threads": len(threads), "threads": threads}
