"""
Storage Module
Thread-safe file operations for security logs
"""
import json
import threading
from pathlib import Path
from typing import Dict
from config import SECURITY_STORAGE_DIR
from datetime_utils import now

# Thread-safe file operations lock
file_lock = threading.Lock()


def get_bot_security_file(bot_id: str) -> Path:
    """Get the security log file path for a bot session"""
    return SECURITY_STORAGE_DIR / f"{bot_id}.json"


def load_bot_security_log(bot_id: str) -> dict:
    """Load security log for a bot session - THREAD SAFE"""
    security_file = get_bot_security_file(bot_id)
    
    with file_lock:
        if security_file.exists():
            with open(security_file, 'r') as f:
                return json.load(f)
        return {
            "bot_id": bot_id, 
            "created_at": now(),
            "security_events": [],
            "total_prompts": 0,
            "blocked_prompts": 0,
            "pii_detections": 0,
            "jailbreak_attempts": 0,
            "toxicity_detections": 0
            # 🔧 ADD NEW SCANNER STATISTICS COUNTERS:
            # Initialize counters for your new scanners here
            # ================================================================
            # "secrets_detections": 0,
            # "banned_topics_detections": 0,
            # "code_detections": 0,
            # "sentiment_issues": 0,
            # ================================================================
        }


def save_bot_security_log(bot_id: str, security_data: dict):
    """Save security log for a bot session - THREAD SAFE"""
    security_file = get_bot_security_file(bot_id)
    
    with file_lock:
        with open(security_file, 'w') as f:
            json.dump(security_data, f, indent=2)


def delete_bot_security_log(bot_id: str) -> Dict[str, any]:
    """Delete security log for a bot session - THREAD SAFE"""
    security_file = get_bot_security_file(bot_id)
    
    with file_lock:
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


def list_all_bot_sessions() -> Dict[str, any]:
    """List all bot sessions with security logs - THREAD SAFE"""
    security_files = list(SECURITY_STORAGE_DIR.glob("*.json"))
    bot_sessions = []
    
    with file_lock:
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
                    # 🔧 ADD NEW SCANNER STATISTICS TO LISTING:
                    # Include your new scanner stats in the session list
                    # ============================================================
                    # "secrets_detections": data.get("secrets_detections", 0),
                    # "banned_topics_detections": data.get("banned_topics_detections", 0),
                    # "code_detections": data.get("code_detections", 0),
                    # ============================================================
                })
    
    return {
        "total_sessions": len(bot_sessions),
        "sessions": bot_sessions
    }
