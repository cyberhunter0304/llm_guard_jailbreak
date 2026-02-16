#!/usr/bin/env python
"""Debug message structure"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "chatbot_db")
BOT_ID = os.getenv("BOT_ID")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
conversations_collection = db["conversations"]

print(f"Checking message structure for BOT_ID: {BOT_ID}\n")

# Get one user message
user_msg = conversations_collection.find_one({
    "botId": BOT_ID,
    "from.role": "user"
})

if user_msg:
    print("Sample USER message structure:")
    print(f"  _id: {user_msg.get('_id')}")
    print(f"  from: {user_msg.get('from')}")
    print(f"  activity: {user_msg.get('activity')}")
    print(f"  threadId: {user_msg.get('threadId')}")
    print(f"  conversationId: {user_msg.get('conversationId')}")
    print(f"  botId: {user_msg.get('botId')}")
else:
    print("❌ No user messages found!")

# Get one bot message
bot_msg = conversations_collection.find_one({
    "botId": BOT_ID,
    "from.role": "bot"
})

if bot_msg:
    print("\nSample BOT message structure:")
    print(f"  _id: {bot_msg.get('_id')}")
    print(f"  from: {bot_msg.get('from')}")
    print(f"  activity: {bot_msg.get('activity')}")
    print(f"  threadId: {bot_msg.get('threadId')}")
    print(f"  conversationId: {bot_msg.get('conversationId')}")
    print(f"  botId: {bot_msg.get('botId')}")
else:
    print("\n❌ No bot messages found!")

# Count messages
user_count = conversations_collection.count_documents({
    "botId": BOT_ID,
    "from.role": "user"
})
bot_count = conversations_collection.count_documents({
    "botId": BOT_ID,
    "from.role": "bot"
})

print(f"\nMessage counts for BOT_ID '{BOT_ID}':")
print(f"  User messages: {user_count}")
print(f"  Bot messages: {bot_count}")
print(f"  Total: {user_count + bot_count}")

client.close()
