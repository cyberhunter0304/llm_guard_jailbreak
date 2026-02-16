"""
Import Conversations to MongoDB
Script to import your existing conversations to MongoDB for batch processing
"""
import json
import sys
from pathlib import Path
from pymongo import MongoClient
from datetime import datetime

def import_conversations_from_json(json_file_path):
    """Import conversations from JSON file to MongoDB"""
    
    print("="*80)
    print("📥 Importing Conversations to MongoDB")
    print("="*80)
    
    # Connect to MongoDB
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {str(e)}")
        print("💡 Make sure MongoDB is running: mongod")
        return False
    
    try:
        db = client["guardrails_dev"]
        conversations = db["conversations"]
        
        # Load JSON file
        json_path = Path(json_file_path)
        if not json_path.exists():
            print(f"❌ File not found: {json_file_path}")
            return False
        
        print(f"📖 Reading: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, dict) and "conversations" in data:
            conversation_list = data["conversations"]
        elif isinstance(data, list):
            conversation_list = data
        else:
            print("❌ JSON format not recognized")
            print("   Expected: {\"conversations\": [...]} or [...]")
            return False
        
        if not conversation_list:
            print("❌ No conversations found in JSON")
            return False
        
        print(f"📊 Found {len(conversation_list)} conversations to import")
        
        # Prepare documents for insertion
        docs_to_insert = []
        for i, conv in enumerate(conversation_list):
            # Ensure required fields exist
            if isinstance(conv, str):
                # If it's just a string, convert it
                doc = {
                    "conversation_id": f"conv_{i}",
                    "message": conv,
                    "processed": False,
                    "created_at": datetime.utcnow().isoformat()
                }
            elif isinstance(conv, dict):
                doc = conv.copy()
                # Ensure required fields
                if "conversation_id" not in doc:
                    doc["conversation_id"] = f"conv_{i}"
                if "message" not in doc and "prompt" in doc:
                    doc["message"] = doc["prompt"]
                if "message" not in doc and "text" in doc:
                    doc["message"] = doc["text"]
                if "message" not in doc:
                    doc["message"] = str(doc)
                if "processed" not in doc:
                    doc["processed"] = False
                if "created_at" not in doc:
                    doc["created_at"] = datetime.utcnow().isoformat()
            else:
                continue
            
            docs_to_insert.append(doc)
        
        if not docs_to_insert:
            print("❌ No valid documents to insert")
            return False
        
        # Drop existing collection to avoid duplicates
        print("🗑️  Clearing existing conversations...")
        conversations.drop()
        
        # Insert documents
        print(f"💾 Inserting {len(docs_to_insert)} conversations...")
        result = conversations.insert_many(docs_to_insert)
        
        # Create index
        conversations.create_index("conversation_id", unique=True)
        conversations.create_index("processed")
        
        print("\n" + "="*80)
        print(f"✅ Successfully imported {len(result.inserted_ids)} conversations")
        print(f"✅ Created indexes for fast queries")
        print("="*80)
        
        print("\n📊 Summary:")
        print(f"   Total: {conversations.count_documents({})}")
        print(f"   Unprocessed: {conversations.count_documents({'processed': {'$ne': True}})}")
        print(f"   Processed: {conversations.count_documents({'processed': True})}")
        
        print("\n✨ Ready to start batch processing!")
        print("   Run: python process_conversations.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        client.close()


def import_from_sql_backup():
    """Import from SQL backup or database export"""
    print("🔍 Looking for conversation data...")
    print("\nSupported formats:")
    print("  1. JSON file: conversations.json")
    print("  2. JSON file: data.json")
    print("  3. JSONL file: conversations.jsonl")
    
    # Try to find a JSON file in current directory
    for pattern in ["conversations.json", "data.json", "chats.json"]:
        path = Path(pattern)
        if path.exists():
            print(f"\n✅ Found: {path}")
            return import_conversations_from_json(str(path))
    
    print("\n❌ No conversation file found")
    print("\n💡 Steps:")
    print("  1. Export your conversations to conversations.json")
    print("  2. Format should be:")
    print('     {"conversations": [{"message": "...", "id": "..."}, ...]}')
    print("  3. Place it in the backend folder")
    print("  4. Run this script again")
    
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Import from specific file
        file_path = sys.argv[1]
        success = import_conversations_from_json(file_path)
    else:
        # Auto-detect
        success = import_from_sql_backup()
    
    sys.exit(0 if success else 1)
