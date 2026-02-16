#!/usr/bin/env python
"""Test to see one actual message structure"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "chatbot_db")
BOT_ID = os.getenv("BOT_ID", "bot-yahavarshini")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
conversations_collection = db["conversations"]

print(f"Checking message structure for BOT_ID: {BOT_ID}\n")

# Get one user message  
user_msg = conversations_collection.find_one({
    "botId": BOT_ID,
    "$or": [
        {"from.role": "user"},
        {"role": "user"},
        {"sender": "user"}
    ]
})

if user_msg:
    print("✅ Found a user message. Full structure:")
    print(json.dumps(user_msg, indent=2, default=str))
else:
    print("❌ No user message found with standard role fields")
    
    # Try to get any message
    any_msg = conversations_collection.find_one({"botId": BOT_ID})
    if any_msg:
        print("\n📝 Structure of any message:")
        print(json.dumps(any_msg, indent=2, default=str))

client.close()
