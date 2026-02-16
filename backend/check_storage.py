#!/usr/bin/env python
"""Quick diagnostic to see what's actually being stored"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "chatbot_db")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
security_logs = db["security_logs"]

print(f"Connected to {MONGODB_DATABASE}\n")

# Count documents by type
total_docs = security_logs.count_documents({})
thread_summaries = security_logs.count_documents({"type": "thread_summary"})
security_events = security_logs.count_documents({"type": {"$ne": "thread_summary"}})

print(f"Total documents in security_logs: {total_docs}")
print(f"  - Thread summaries: {thread_summaries}")
print(f"  - Security events (prompts): {security_events}")

# Show sample thread summary
if thread_summaries > 0:
    sample_thread = security_logs.find_one({"type": "thread_summary"})
    print(f"\nSample thread summary:")
    print(f"  thread_id: {sample_thread.get('thread_id')}")
    print(f"  total_conversations: {sample_thread.get('total_conversations')}")
    print(f"  total_prompts: {sample_thread.get('total_prompts')}")
    print(f"  total_events_stored: {sample_thread.get('total_events_stored')}")

# Show sample security event
if security_events > 0:
    sample_event = security_logs.find_one({"type": {"$ne": "thread_summary"}})
    print(f"\nSample security event:")
    print(f"  prompt: {sample_event.get('prompt', 'N/A')[:50]}")
    print(f"  risk_level: {sample_event.get('risk_level')}")
    print(f"  is_safe: {sample_event.get('is_safe')}")
else:
    print(f"\n⚠️  No security events (prompts) stored yet")

client.close()
