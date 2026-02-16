"""
Show sample conversation document structure
"""
import json
from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    db = client["guardrails_dev"]
    conversations = db["conversations"]
    
    print("="*80)
    print("📄 Sample Conversation Document")
    print("="*80 + "\n")
    
    sample = conversations.find_one()
    
    if sample:
        # Pretty print with proper formatting
        print(json.dumps(sample, indent=2, default=str))
    else:
        print("No conversations found!")
    
    client.close()
    
except Exception as e:
    print(f"Error: {e}")
