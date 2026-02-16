"""
MongoDB Diagnostic Script
Check if conversations exist and are properly configured for batch processing
"""
import sys
from pymongo import MongoClient

def check_mongodb():
    """Diagnose MongoDB setup and conversation data"""
    
    print("="*80)
    print("🔍 MongoDB Diagnostic Report")
    print("="*80)
    
    try:
        # Connect to MongoDB
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        print("✅ MongoDB connection: SUCCESS")
        
    except Exception as e:
        print(f"❌ MongoDB connection: FAILED")
        print(f"   Error: {str(e)}")
        print("\n💡 Fix: Start MongoDB with 'mongod' command")
        return False
    
    try:
        db = client["guardrails_dev"]
        print("✅ Database 'guardrails_dev': EXISTS")
        
        # Check conversations collection
        if "conversations" not in db.list_collection_names():
            print("❌ Collection 'conversations': NOT FOUND")
            print("\n   Your conversations need to be imported to MongoDB first!")
            print("\n💡 Options:")
            print("   1. Import from your current data source:")
            print("      python import_conversations.py")
            print("   2. Or manually import using mongoimport or MongoDB Compass")
            return False
        
        conversations = db["conversations"]
        conv_count = conversations.count_documents({})
        print(f"✅ Collection 'conversations': EXISTS with {conv_count} documents")
        
        if conv_count == 0:
            print("❌ No conversations found in collection")
            print("💡 Import your 21k conversations to this collection first")
            return False
        
        # Check unprocessed conversations
        unprocessed_count = conversations.count_documents({"processed": {"$ne": True}})
        print(f"✅ Unprocessed conversations: {unprocessed_count}")
        
        if unprocessed_count == 0:
            print("❌ All conversations are already marked as processed!")
            print("   To reprocess, run:")
            print("   db.conversations.updateMany({}, {$set: {processed: false}})")
            return False
        
        # Show sample conversation
        sample = conversations.find_one({"processed": {"$ne": True}})
        if sample:
            print("\n📄 Sample unprocessed conversation:")
            print(f"   ID: {sample.get('conversation_id', sample.get('_id'))}")
            print(f"   Message length: {len(sample.get('message', sample.get('prompt', '')))}")
            print(f"   Fields: {list(sample.keys())}")
        
        # Check security_logs collection
        print("\n" + "-"*80)
        if "security_logs" not in db.list_collection_names():
            print("ℹ️  Collection 'security_logs': Will be created on first processing")
        else:
            logs = db["security_logs"]
            log_count = logs.count_documents({})
            print(f"✅ Collection 'security_logs': EXISTS with {log_count} documents")
        
        print("\n" + "="*80)
        print("✅ All checks passed! Ready to process conversations")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        client.close()


if __name__ == "__main__":
    success = check_mongodb()
    sys.exit(0 if success else 1)
