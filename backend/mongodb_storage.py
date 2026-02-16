"""
MongoDB Storage Module
Thread-safe MongoDB operations for security logs
Replaces file-based JSON storage with MongoDB backend
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, DuplicateKeyError
from config import (
    MONGODB_URI, 
    MONGODB_DATABASE, 
    MONGODB_SECURITY_LOGS_COLLECTION,
    MONGODB_CONVERSATIONS_COLLECTION
)
from datetime_utils import now

logger = logging.getLogger(__name__)

# Global MongoDB client and database
_client: Optional[MongoClient] = None
_db = None


def connect_mongodb():
    """Initialize MongoDB connection"""
    global _client, _db
    
    try:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test the connection
        _client.admin.command('ping')
        _db = _client[MONGODB_DATABASE]
        
        # Create collections with indexes if they don't exist
        _create_indexes()
        
        logger.info(f"✅ Connected to MongoDB - Database: {MONGODB_DATABASE}")
        return True
    except ServerSelectionTimeoutError:
        logger.error(f"❌ Failed to connect to MongoDB at {MONGODB_URI}")
        return False
    except Exception as e:
        logger.error(f"❌ MongoDB connection error: {str(e)}")
        return False


def _create_indexes():
    """Create necessary MongoDB indexes"""
    if _db is None:
        return
    
    security_logs = _db[MONGODB_SECURITY_LOGS_COLLECTION]
    conversations = _db[MONGODB_CONVERSATIONS_COLLECTION]
    
    # Index on bot_id for fast lookups
    security_logs.create_index("bot_id", unique=True)
    security_logs.create_index("created_at")
    security_logs.create_index("last_updated")
    
    # Index on conversation_id and bot_id in conversations
    conversations.create_index("conversation_id", unique=True)
    conversations.create_index("bot_id")
    conversations.create_index("processed")
    
    logger.info("✅ MongoDB indexes created")


def get_mongodb():
    """Get MongoDB database instance"""
    global _db
    if _db is None:
        connect_mongodb()
    return _db


def load_bot_security_log(bot_id: str) -> dict:
    """Load security log for a bot session from MongoDB"""
    try:
        db = get_mongodb()
        if db is None:
            logger.error("MongoDB not connected")
            return _get_default_security_log(bot_id)
        
        security_logs = db[MONGODB_SECURITY_LOGS_COLLECTION]
        
        existing_log = security_logs.find_one({"bot_id": bot_id})
        
        if existing_log:
            # Remove MongoDB's _id field from response
            if "_id" in existing_log:
                del existing_log["_id"]
            return existing_log
        
        return _get_default_security_log(bot_id)
    
    except Exception as e:
        logger.error(f"Error loading security log for bot {bot_id}: {str(e)}")
        return _get_default_security_log(bot_id)


def save_bot_security_log(bot_id: str, security_data: dict):
    """Save security log for a bot session to MongoDB"""
    try:
        db = get_mongodb()
        if db is None:
            logger.error("MongoDB not connected - cannot save security log")
            return False
        
        security_logs = db[MONGODB_SECURITY_LOGS_COLLECTION]
        
        # Remove _id if present to allow update
        if "_id" in security_data:
            del security_data["_id"]
        
        # Ensure last_updated is set
        security_data["last_updated"] = now()
        
        # Upsert: update if exists, insert if not
        result = security_logs.update_one(
            {"bot_id": bot_id},
            {"$set": security_data},
            upsert=True
        )
        
        logger.debug(f"Saved security log for bot {bot_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving security log for bot {bot_id}: {str(e)}")
        return False


def delete_bot_security_log(bot_id: str) -> Dict[str, Any]:
    """Delete security log for a bot session from MongoDB"""
    try:
        db = get_mongodb()
        if db is None:
            return {"success": False, "message": "MongoDB not connected"}
        
        security_logs = db[MONGODB_SECURITY_LOGS_COLLECTION]
        result = security_logs.delete_one({"bot_id": bot_id})
        
        if result.deleted_count > 0:
            logger.info(f"Deleted security log for bot {bot_id}")
            return {"success": True, "message": f"Security log deleted for bot_id: {bot_id}"}
        else:
            return {"success": False, "message": f"No security log found for bot_id: {bot_id}"}
    
    except Exception as e:
        logger.error(f"Error deleting security log for bot {bot_id}: {str(e)}")
        return {"success": False, "message": f"Error deleting log: {str(e)}"}


def list_all_bot_sessions(limit: int = None, skip: int = 0) -> Dict[str, Any]:
    """List all bot sessions with security logs from MongoDB"""
    try:
        db = get_mongodb()
        if db is None:
            return {"sessions": [], "total": 0}
        
        security_logs = db[MONGODB_SECURITY_LOGS_COLLECTION]
        
        query = security_logs.find({})
        total = security_logs.count_documents({})
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
        
        bot_sessions = []
        for log in query:
            if "_id" in log:
                del log["_id"]
            bot_sessions.append(log)
        
        return {"sessions": bot_sessions, "total": total}
    
    except Exception as e:
        logger.error(f"Error listing bot sessions: {str(e)}")
        return {"sessions": [], "total": 0}


# ============================================================================
# BATCH PROCESSING FUNCTIONS FOR CONVERSATION SECURITY SCANNING
# ============================================================================

def get_unprocessed_conversations(limit: int = 1) -> List[Dict[str, Any]]:
    """Get unprocessed conversations from MongoDB"""
    try:
        db = get_mongodb()
        if db is None:
            logger.error("MongoDB not connected")
            return []
        
        conversations = db[MONGODB_CONVERSATIONS_COLLECTION]
        
        # Get conversations that haven't been processed (processed = False or missing)
        query = conversations.find({"processed": {"$ne": True}}).limit(limit)
        
        results = []
        for conv in query:
            if "_id" in conv:
                # Keep _id but don't remove it, we need it for tracking
                pass
            results.append(conv)
        
        return results
    
    except Exception as e:
        logger.error(f"Error fetching unprocessed conversations: {str(e)}")
        return []


def mark_conversation_processed(conversation_id: str, security_log_id: str = None) -> bool:
    """Mark a conversation as processed and link to security log"""
    try:
        db = get_mongodb()
        if db is None:
            return False
        
        conversations = db[MONGODB_CONVERSATIONS_COLLECTION]
        
        update_data = {
            "processed": True,
            "processed_at": now(),
        }
        
        if security_log_id:
            update_data["security_log_id"] = security_log_id
        
        # Use _id field if provided, or conversationId
        result = conversations.update_one(
            {"_id": conversation_id} if len(str(conversation_id)) == 24 else {"conversationId": conversation_id},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    except Exception as e:
        logger.error(f"Error marking conversation {conversation_id} as processed: {str(e)}")
        return False


def get_processing_stats() -> Dict[str, Any]:
    """Get batch processing statistics"""
    try:
        db = get_mongodb()
        if db is None:
            return {"error": "MongoDB not connected"}
        
        conversations = db[MONGODB_CONVERSATIONS_COLLECTION]
        security_logs = db[MONGODB_SECURITY_LOGS_COLLECTION]
        
        total_conversations = conversations.count_documents({})
        processed_conversations = conversations.count_documents({"processed": True})
        pending_conversations = total_conversations - processed_conversations
        
        total_security_logs = security_logs.count_documents({})
        total_security_events = 0
        
        # Count total security events across all logs
        for log in security_logs.find({}):
            events = log.get("security_events", [])
            total_security_events += len(events)
        
        return {
            "total_conversations": total_conversations,
            "processed_conversations": processed_conversations,
            "pending_conversations": pending_conversations,
            "processing_percentage": round((processed_conversations / total_conversations * 100), 2) if total_conversations > 0 else 0,
            "total_security_logs": total_security_logs,
            "total_security_events": total_security_events
        }
    
    except Exception as e:
        logger.error(f"Error getting processing stats: {str(e)}")
        return {"error": str(e)}


def _get_default_security_log(bot_id: str) -> dict:
    """Get default empty security log structure"""
    return {
        "bot_id": bot_id,
        "created_at": now(),
        "security_events": [],
        "total_prompts": 0,
        "blocked_prompts": 0,
        "pii_detections": 0,
        "jailbreak_attempts": 0,
        "toxicity_detections": 0,
        "secrets_detections": 0,
        "last_updated": now()
    }


def close_mongodb():
    """Close MongoDB connection"""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")
