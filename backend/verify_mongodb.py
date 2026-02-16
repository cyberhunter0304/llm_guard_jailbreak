from config import MONGODB_URI, MONGODB_DATABASE
from pymongo import MongoClient

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]

print("📊 Checking MongoDB collections:\n")

# Check security_logs
sec_count = db.security_logs.count_documents({})
print(f"security_logs: {sec_count} documents")

# Check thread_summaries
thread_count = db.thread_summaries.count_documents({})
print(f"thread_summaries: {thread_count} documents")

if thread_count > 0:
    doc = db.thread_summaries.find_one()
    print(f"\n✅ Found thread object in thread_summaries:")
    print(f"   Thread ID: {doc.get('thread_id')}")
    print(f"   Conversations: {len(doc.get('conversations', []))}")
    print(f"   Total Messages: {doc.get('total_messages')}")
    print(f"   PII Detections: {doc.get('pii_detections')}")
elif sec_count > 0:
    print("\n⚠️  Data found in security_logs (old location)")
else:
    print("\n❌ No thread objects found in either collection")

client.close()

