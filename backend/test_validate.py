#!/usr/bin/env python
"""Quick test to see if validation is working"""
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from pymongo import MongoClient
from security_scanner import ConcurrentSecurityScanner

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "chatbot_db")

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
conversations_collection = db["conversations"]
security_logs_collection = db["security_logs"]

print(f"Connected to MongoDB: {MONGODB_DATABASE}")

# Initialize scanner
print("\nInitializing scanner...")
scanner = ConcurrentSecurityScanner()
print("✅ Scanner initialized")

# Fetch ONE prompt
print("\nFetching one sample prompt...")
bot_id = os.getenv("BOT_ID", "test-bot")
sample = conversations_collection.find_one({
    "botId": bot_id,
    "from.role": "user",
    "activity.text": {"$ne": "N/A", "$ne": ""}
})

if not sample:
    print("❌ No sample prompt found")
else:
    prompt_text = sample.get("activity", {}).get("text", "")
    print(f"Sample prompt: {prompt_text[:50]}...")
    
    # Test validation
    print("\nRunning scanner on sample prompt...")
    try:
        result = scanner.scan_prompt_parallel(prompt_text, bot_id)
        print(f"✅ Scan completed!")
        print(f"   Type: {type(result)}")
        print(f"   is_safe: {result.is_safe}")
        print(f"   risk_level: {result.risk_level}")
        print(f"   detections: {result.detections}")
        print(f"   scan_duration: {result.scan_duration}s")
        
        # Try storing
        print("\nTrying to store to MongoDB...")
        doc = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt_text,
            "is_safe": result.is_safe,
            "risk_level": result.risk_level,
            "detections": result.detections,
            "scan_duration": result.scan_duration,
            "message": result.message,
            "type": "test"
        }
        inserted = security_logs_collection.insert_one(doc)
        print(f"✅ Stored! ID: {inserted.inserted_id}")
        
        # Verify
        found = security_logs_collection.find_one({"_id": inserted.inserted_id})
        print(f"✅ Verified! Found document: {found is not None}")
        
        # Cleanup
        security_logs_collection.delete_one({"_id": inserted.inserted_id})
        print(f"✅ Cleaned up test document")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

client.close()
print("\nTest complete!")
