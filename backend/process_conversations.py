import os
import time
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from collections import defaultdict
from dotenv import load_dotenv
import logging

# Import security scanner
from security_scanner import ConcurrentSecurityScanner

"""
COMPREHENSIVE BATCH PROCESSOR WITH DUAL-LEVEL AGGREGATION

Storage: MongoDB security_logs collection

Output Structure:
{
  "thread_id": "thread-123",
  "user_id": "user-456",
  
  # THREAD-LEVEL AGGREGATIONS (sum of all conversations)
  "conversation_count": 3,
  "total_messages": 45,
  "total_prompts": 20,
  "blocked_prompts": 2,
  "pii_detections": 5,
  "jailbreak_attempts": 1,
  "toxicity_detections": 0,
  "secrets_detections": 3,
  
  # NESTED CONVERSATIONS (each with own aggregations)
  "conversations": [
    {
      "conversation_id": "conv-789",
      
      # CONVERSATION-LEVEL AGGREGATIONS (sum of messages in this conversation)
      "total_messages": 15,
      "total_prompts": 7,
      "blocked_prompts": 1,
      "pii_detections": 2,
      "jailbreak_attempts": 0,
      "toxicity_detections": 0,
      "secrets_detections": 1,
      
      # MESSAGES WITH INLINE VALIDATIONS
      "messages": [
        {
          "role": "user",
          "text": "My email is john@example.com",
          "validation": {
            "detections": {
              "pii": {"detected": true, "entities_found": 1}
            },
            "blocked": false,
            "risk_level": "MEDIUM"
          }
        },
        {
          "role": "bot",
          "text": "Bot response here"
        }
      ]
    }
  ]
}

This creates:
- ONE object per thread stored in security_logs collection
- Thread-level aggregations (all conversations summed)
- Conversation-level aggregations (all messages in that conversation summed)
- Message-level validation data (individual prompt scans)
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration from environment
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "guardrails_dev")
BOT_ID = os.getenv("BOT_ID")  # Required: bot-yahavarshini
CONVERSATIONS_COLLECTION = os.getenv("CONVERSATIONS_COLLECTION", "conversations")
SECURITY_LOGS_COLLECTION = os.getenv("SECURITY_LOGS_COLLECTION", "security_logs")
THREAD_SUMMARIES_COLLECTION = os.getenv("THREAD_SUMMARIES_COLLECTION", "thread_summaries")


def validate_message(prompt_text, llm_response=None, scanner=None, bot_id="batch_process"):
    """
    Validate a user prompt by running it through all security scanners
    
    Args:
        prompt_text: User prompt text (required, must not be N/A)
        llm_response: Bot response text (optional)
        scanner: ConcurrentSecurityScanner instance for real validation
        bot_id: Bot identifier for logging
        
    Returns:
        dict: Validation results with real detection data or safe defaults
    """
    # Skip if no meaningful prompt
    if not prompt_text or prompt_text.strip().upper() == "N/A":
        return None
    
    timestamp = datetime.now(timezone.utc)
    
    if scanner:
        try:
            # Run prompt through all security validators
            scan_results = scanner.scan_prompt_parallel(prompt_text, bot_id)
            
            validation_result = {
                "timestamp": timestamp.isoformat(),
                "prompt": prompt_text.strip(),
                "prompt_length": len(prompt_text),
                "llm_response": llm_response.strip() if llm_response else None,
                "detections": scan_results.detections,
                "risk_level": scan_results.risk_level,
                "is_safe": scan_results.is_safe,
                "scan_duration": scan_results.scan_duration,
                "blocked": not scan_results.is_safe,
                "message": scan_results.message,
                "metrics": {
                    "request_start_time": time.time(),
                    "scan_time": scan_results.scan_duration,
                    "scanner_details": {},
                    "llm_time": 0.0,
                    "total_time": scan_results.scan_duration
                },
                "success": True
            }
            
            logger.info(f"Scanned prompt: {prompt_text[:50]}... | Risk: {scan_results.risk_level}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during prompt scanning: {str(e)}")
            # Fallback to safe result on error
            safe_result = {
                "timestamp": timestamp.isoformat(),
                "prompt": prompt_text.strip(),
                "prompt_length": len(prompt_text),
                "llm_response": llm_response.strip() if llm_response else None,
                "detections": {
                    "prompt_injection": {"is_valid": True, "risk_score": -1.0, "detected": False, "execution_time": 0.0},
                    "toxicity": {"is_valid": True, "risk_score": -1.0, "detected": False, "execution_time": 0.0},
                    "pii": {"is_valid": True, "risk_score": 0.0, "detected": False, "entities_found": 0, "entity_types": [], "entities": [], "anonymized_prompt": None, "anonymized": False, "execution_time": 0.0, "entity_count": 0, "secrets_detected": False, "secrets_risk_score": -1.0}
                },
                "risk_level": "SAFE",
                "is_safe": True,
                "scan_duration": 0.0,
                "blocked": False,
                "message": "Scan failed, treating as safe",
                "metrics": {"request_start_time": time.time(), "scan_time": 0.0, "scanner_details": {}, "llm_time": 0.0, "total_time": 0.0},
                "success": False
            }
            return safe_result
    
    # If no scanner provided, return default safe result
    validation_result = {
        "timestamp": timestamp.isoformat(),
        "prompt": prompt_text.strip(),
        "prompt_length": len(prompt_text),
        "llm_response": llm_response.strip() if llm_response else None,
        "detections": {
            "prompt_injection": {"is_valid": True, "risk_score": -1.0, "detected": False, "execution_time": 0.0},
            "toxicity": {"is_valid": True, "risk_score": -1.0, "detected": False, "execution_time": 0.0},
            "pii": {"is_valid": True, "risk_score": 0.0, "detected": False, "entities_found": 0, "entity_types": [], "entities": [], "anonymized_prompt": None, "anonymized": False, "execution_time": 0.0, "entity_count": 0, "secrets_detected": False, "secrets_risk_score": -1.0}
        },
        "risk_level": "SAFE",
        "is_safe": True,
        "scan_duration": 0.0,
        "blocked": False,
        "message": "No scanner provided",
        "metrics": {"request_start_time": time.time(), "scan_time": 0.0, "scanner_details": {}, "llm_time": 0.0, "total_time": 0.0},
        "success": True
    }
    
    return validation_result


def organize_messages_by_structure(messages):
    """
    Organize messages into nested structure: threads → conversations → messages
    
    For this data structure:
    - Thread ID: userId (represents all conversations for one user)
    - Conversation ID: conversationId (represents one chat session)
    
    Args:
        messages: List of message documents from MongoDB
        
    Returns:
        dict: {userId: {conversationId: [sorted_messages]}}
    """
    structure = defaultdict(lambda: defaultdict(list))
    skipped_count = 0
    
    for msg in messages:
        # Primary: Use userId as thread identifier (one user = one thread)
        user_id = msg.get("userId")
        conversation_id = msg.get("conversationId")
        
        if user_id and conversation_id:
            structure[user_id][conversation_id].append(msg)
        else:
            skipped_count += 1
    
    if skipped_count > 0:
        print(f"   ⚠️  Skipped {skipped_count} messages without userId/conversationId")
    
    # Sort messages within each conversation by timestamp
    for user_id in structure:
        for conv_id in structure[user_id]:
            structure[user_id][conv_id].sort(
                key=lambda x: x.get("createdAt", datetime.min)
            )
    
    return structure


def process_conversation_with_validations(conversation_messages, scanner=None, bot_id="batch_process"):
    """
    Process a conversation and validate each user prompt with security scanners.
    Returns conversation object with messages, validations, and conversation-level aggregated statistics.
    
    Args:
        conversation_messages: List of sorted messages in a conversation
        scanner: ConcurrentSecurityScanner instance
        bot_id: Bot identifier
        
    Returns:
        dict: Conversation object with:
              - conversation_id
              - conversation-level aggregated statistics
              - messages array with validation data inline
    """
    if not conversation_messages:
        return None
    
    # Extract conversation metadata
    first_msg = conversation_messages[0]
    last_msg = conversation_messages[-1]
    
    conversation_id = first_msg.get("conversationId")
    thread_id = first_msg.get("threadId")
    
    # Process messages with validation
    processed_messages = []
    user_prompts_count = 0
    bot_responses_count = 0
    
    # Conversation-level statistics (aggregated from all messages in this conversation)
    conversation_stats = {
        "total_prompts": 0,
        "blocked_prompts": 0,
        "pii_detections": 0,
        "jailbreak_attempts": 0,
        "toxicity_detections": 0,
        "secrets_detections": 0
    }
    
    # Build message pairs (user + bot response)
    pending_user_message = None
    
    for msg in conversation_messages:
        role = msg.get("from", {}).get("role", "").lower()
        text = msg.get("activity", {}).get("text", "").strip()
        
        message_obj = {
            "message_id": msg.get("messageId"),
            "timestamp": msg.get("createdAt").isoformat() if hasattr(msg.get("createdAt"), 'isoformat') else str(msg.get("createdAt")),
            "role": role,
            "text": text,
            "validation": None  # Will be populated for user messages
        }
        
        if role == "user":
            user_prompts_count += 1
            
            # Validate user prompt if it's meaningful
            if text and text.upper() != "N/A":
                validation_result = validate_message(
                    prompt_text=text,
                    llm_response=None,  # Will be added later if bot responds
                    scanner=scanner,
                    bot_id=bot_id
                )
                
                if validation_result:
                    message_obj["validation"] = validation_result
                    
                    # Aggregate statistics for this conversation
                    conversation_stats["total_prompts"] += 1
                    if validation_result.get("blocked"):
                        conversation_stats["blocked_prompts"] += 1
                    
                    detections = validation_result.get("detections", {})
                    if detections.get("pii", {}).get("detected"):
                        conversation_stats["pii_detections"] += 1
                    if detections.get("prompt_injection", {}).get("detected"):
                        conversation_stats["jailbreak_attempts"] += 1
                    if detections.get("toxicity", {}).get("detected"):
                        conversation_stats["toxicity_detections"] += 1
                    if detections.get("pii", {}).get("secrets_detected"):
                        conversation_stats["secrets_detections"] += 1
            
            pending_user_message = message_obj
            processed_messages.append(message_obj)
            
        elif role == "bot":
            bot_responses_count += 1
            
            # Update previous user message validation with bot response
            if pending_user_message and pending_user_message.get("validation"):
                pending_user_message["validation"]["llm_response"] = text
            
            pending_user_message = None  # Reset
            processed_messages.append(message_obj)
    
    # Build conversation object with conversation-level aggregations
    conversation_obj = {
        "conversation_id": conversation_id,
        "thread_id": thread_id if thread_id else first_msg.get("userId"),  # Fallback to userId
        "started_at": first_msg.get("createdAt").isoformat() if hasattr(first_msg.get("createdAt"), 'isoformat') else str(first_msg.get("createdAt")),
        "ended_at": last_msg.get("createdAt").isoformat() if hasattr(last_msg.get("createdAt"), 'isoformat') else str(last_msg.get("createdAt")),
        
        # Conversation-level counts
        "total_messages": len(conversation_messages),
        "user_prompts_count": user_prompts_count,
        "bot_responses_count": bot_responses_count,
        
        # Conversation-level aggregated statistics
        "total_prompts": conversation_stats["total_prompts"],
        "blocked_prompts": conversation_stats["blocked_prompts"],
        "pii_detections": conversation_stats["pii_detections"],
        "jailbreak_attempts": conversation_stats["jailbreak_attempts"],
        "toxicity_detections": conversation_stats["toxicity_detections"],
        "secrets_detections": conversation_stats["secrets_detections"],
        
        # All messages in this conversation with inline validations
        "messages": processed_messages
    }
    
    return conversation_obj


def build_comprehensive_thread_object(thread_id, conversations_data, all_messages):
    """
    Build a comprehensive thread object with all conversations and their validations.
    Aggregates statistics at both thread level and conversation level.
    
    Note: thread_id in this context is actually the userId (one user = one thread)
    
    Args:
        thread_id: User identifier (userId from messages)
        conversations_data: List of processed conversation objects
        all_messages: All messages in the thread (for metadata)
        
    Returns:
        dict: Complete thread object with nested conversations and validations
    """
    if not conversations_data:
        return None
    
    # Get thread metadata from first message
    first_msg = all_messages[0] if all_messages else {}
    last_msg = all_messages[-1] if all_messages else {}
    
    # Aggregate statistics across all conversations in thread
    thread_level_stats = {
        "total_prompts": 0,
        "blocked_prompts": 0,
        "pii_detections": 0,
        "jailbreak_attempts": 0,
        "toxicity_detections": 0,
        "secrets_detections": 0
    }
    
    # Sum up all conversation statistics for thread-level aggregation
    for conv in conversations_data:
        thread_level_stats["total_prompts"] += conv.get("total_prompts", 0)
        thread_level_stats["blocked_prompts"] += conv.get("blocked_prompts", 0)
        thread_level_stats["pii_detections"] += conv.get("pii_detections", 0)
        thread_level_stats["jailbreak_attempts"] += conv.get("jailbreak_attempts", 0)
        thread_level_stats["toxicity_detections"] += conv.get("toxicity_detections", 0)
        thread_level_stats["secrets_detections"] += conv.get("secrets_detections", 0)
    
    # Sort conversations by start time
    conversations_data.sort(key=lambda x: x.get("started_at", ""))
    
    # Build comprehensive thread object
    thread_obj = {
        "thread_id": thread_id,  # This is actually userId
        "bot_id": first_msg.get("botId"),
        "user_id": thread_id,  # Same as thread_id in this case
        "channel_session_id": first_msg.get("channelSessionId"),
        "created_at": first_msg.get("createdAt").isoformat() if hasattr(first_msg.get("createdAt"), 'isoformat') else str(first_msg.get("createdAt")),
        "last_updated": last_msg.get("createdAt").isoformat() if hasattr(last_msg.get("createdAt"), 'isoformat') else str(last_msg.get("createdAt")),
        
        # Thread-level aggregations
        "conversation_count": len(conversations_data),
        "total_messages": sum(c.get("total_messages", 0) for c in conversations_data),
        "total_prompts": thread_level_stats["total_prompts"],
        "blocked_prompts": thread_level_stats["blocked_prompts"],
        "pii_detections": thread_level_stats["pii_detections"],
        "jailbreak_attempts": thread_level_stats["jailbreak_attempts"],
        "toxicity_detections": thread_level_stats["toxicity_detections"],
        "secrets_detections": thread_level_stats["secrets_detections"],
        
        # Nested conversations with their own aggregations
        "conversations": conversations_data  # Each conversation has its own statistics
    }
    
    return thread_obj


def process_all_conversations():
    """
    Main function to process conversations and build comprehensive thread objects.
    Optimized for speed with batch processing and minimal redundant operations.
    Each thread object contains: threadId → conversations → messages → validations
    """
    
    print("="*80)
    print("COMPREHENSIVE SECURITY LOG PROCESSOR (OPTIMIZED)")
    print("="*80)
    print("Structure: Thread → Conversations → Messages → Validations")
    print("Aggregation Levels:")
    print("  1. Thread Level: Aggregates statistics across all conversations")
    print("  2. Conversation Level: Aggregates statistics for each conversation")
    print("  3. Message Level: Individual validations for each user prompt")
    print("="*80)
    
    # Validate BOT_ID
    if not BOT_ID:
        print("❌ ERROR: BOT_ID not set in environment variables")
        print("Please set BOT_ID in your .env file (e.g., BOT_ID=bot-yahavarshini)")
        return
    
    print(f"Bot ID: {BOT_ID}")
    print(f"Database: {MONGODB_DATABASE}")
    print(f"Output: Comprehensive thread objects with nested conversations and validations")
    print("="*80)
    
    # Initialize security scanner ONCE (reuse for all validations)
    print("\n🔐 Initializing security scanners...")
    try:
        scanner = ConcurrentSecurityScanner()
        print("✅ Security scanners initialized successfully")
    except Exception as e:
        print(f"⚠️  Could not initialize security scanner: {str(e)}")
        print("   Proceeding with fallback validation mode")
        scanner = None
    
    # Connect to MongoDB
    try:
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        conversations_collection = db[CONVERSATIONS_COLLECTION]
        security_logs_collection = db[SECURITY_LOGS_COLLECTION]
        
        print(f"✅ Connected to MongoDB: {MONGODB_DATABASE}")
        print(f"   Source Collection: {CONVERSATIONS_COLLECTION}")
        print(f"   Output Collection: {SECURITY_LOGS_COLLECTION}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {str(e)}")
        return
    
    start_time = time.time()
    
    # Fetch ALL messages for the bot IN ONE QUERY (faster than multiple queries)
    print(f"\n📥 Fetching all messages for bot: {BOT_ID}...")
    
    try:
        all_messages = list(conversations_collection.find(
            {"botId": BOT_ID},
            {
                # Only fetch fields we need (reduces data transfer)
                "threadId": 1,
                "conversationId": 1,
                "messageId": 1,
                "createdAt": 1,
                "from.role": 1,
                "activity.text": 1,
                "botId": 1,
                "userId": 1,
                "channelSessionId": 1
            }
        ).sort("createdAt", 1))
        
        print(f"✅ Fetched {len(all_messages)} total messages")
        
        if not all_messages:
            print("⚠️  No messages found for this bot")
            return
        
    except Exception as e:
        print(f"❌ Error fetching messages: {str(e)}")
        return
    
    # Organize messages by thread → conversation (in memory, very fast)
    print("\n📊 Organizing messages by userId (thread) and conversationId...")
    
    # Debug: Show sample message structure
    if all_messages:
        sample_msg = all_messages[0]
        print(f"   📋 Sample message structure:")
        print(f"      userId: {sample_msg.get('userId')}")
        print(f"      conversationId: {sample_msg.get('conversationId')}")
        print(f"      botId: {sample_msg.get('botId')}")
    
    organized_data = organize_messages_by_structure(all_messages)
    
    total_threads = len(organized_data)
    print(f"✅ Found {total_threads} unique users (threads)")
    
    # Process each thread with progress tracking
    all_thread_objects = []
    processed_threads = 0
    processed_conversations = 0
    processed_validations = 0
    
    print(f"\n🔄 Processing {total_threads} threads...")
    print("-" * 80)
    
    for idx, (thread_id, conversations) in enumerate(organized_data.items(), 1):
        # Progress indicator every 10 threads
        if idx % 10 == 0 or idx == 1:
            elapsed = time.time() - start_time
            rate = idx / elapsed if elapsed > 0 else 0
            eta = (total_threads - idx) / rate if rate > 0 else 0
            print(f"Progress: {idx}/{total_threads} threads | "
                  f"Rate: {rate:.1f} threads/sec | "
                  f"ETA: {eta:.0f}s")
        
        thread_conversations = []
        thread_messages = []
        
        for conv_id, messages in conversations.items():
            try:
                conversation_obj = process_conversation_with_validations(
                    messages,
                    scanner=scanner,
                    bot_id=BOT_ID
                )
                
                if conversation_obj:
                    thread_conversations.append(conversation_obj)
                    thread_messages.extend(messages)
                    processed_conversations += 1
                    
                    # Count validations
                    validations = sum(1 for msg in conversation_obj["messages"] if msg.get("validation"))
                    processed_validations += validations
                
            except Exception as e:
                logger.error(f"Error processing conversation {conv_id}: {str(e)}", exc_info=True)
                continue
        
        # Build comprehensive thread object
        if thread_conversations:
            thread_obj = build_comprehensive_thread_object(
                thread_id,
                thread_conversations,
                thread_messages
            )
            
            if thread_obj:
                all_thread_objects.append(thread_obj)
                processed_threads += 1
    
    # Batch insert to MongoDB (much faster than individual inserts)
    print("\n💾 Saving thread objects to MongoDB...")
    if all_thread_objects:
        try:
            # Use bulk write for efficiency
            from pymongo import UpdateOne
            
            bulk_operations = [
                UpdateOne(
                    {"thread_id": obj["thread_id"]},
                    {"$set": obj},
                    upsert=True
                )
                for obj in all_thread_objects
            ]
            
            result = security_logs_collection.bulk_write(bulk_operations, ordered=False)
            print(f"✅ Saved {result.upserted_count + result.modified_count} thread objects")
            
        except Exception as e:
            print(f"❌ Error in bulk save: {str(e)}")
            logger.error(f"Bulk save error: {str(e)}", exc_info=True)
    
    # Final summary
    elapsed_time = time.time() - start_time
    
    # Get totals from security_logs collection
    total_thread_objects = security_logs_collection.count_documents({"thread_id": {"$exists": True}})
    
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"✅ Thread Objects Stored in security_logs: {total_thread_objects}")
    print(f"✅ Threads Processed: {processed_threads}")
    print(f"✅ Conversations Processed: {processed_conversations}")
    print(f"✅ Validations Performed: {processed_validations}")
    print(f"✅ Total Messages: {len(all_messages)}")
    print(f"⏱️  Total Time: {elapsed_time:.2f}s")
    print(f"📊 Average Speed: {processed_threads/elapsed_time:.2f} threads/sec")
    if processed_conversations > 0:
        print(f"📊 Average: {elapsed_time/processed_conversations:.2f}s per conversation")
    print("="*80)
    
    # Save complete output to JSON file for inspection
    output_file = f"thread_objects_{BOT_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_thread_objects, f, indent=2, default=str)
        print(f"\n💾 Complete thread objects saved to: {output_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save JSON file: {str(e)}")
    
    print("\n📊 Sample Thread Object Structure:")
    if all_thread_objects:
        sample = all_thread_objects[0]
        print(f"   Thread ID: {sample['thread_id']}")
        print(f"   Conversations: {len(sample['conversations'])}")
        if sample['conversations']:
            conv = sample['conversations'][0]
            print(f"   └─ Conversation ID: {conv['conversation_id']}")
            print(f"      └─ Messages: {len(conv['messages'])}")
            if conv['messages']:
                msg = conv['messages'][0]
                print(f"         └─ Role: {msg['role']}")
                print(f"            Has Validation: {msg['validation'] is not None}")
    
    client.close()


if __name__ == "__main__":
    print("\n🚀 Starting Comprehensive Security Log Processor\n")
    process_all_conversations()