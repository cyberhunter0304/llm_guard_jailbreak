"""
List all MongoDB collections and their document counts
"""
from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    
    db = client["llm_guard"]
    
    print("Database: llm_guard")
    print("Collections:")
    
    collections = db.list_collection_names()
    
    if not collections:
        print("  ❌ No collections found")
    else:
        for coll in collections:
            count = db[coll].count_documents({})
            print(f"  - {coll}: {count} documents")
    
    # Also check other databases
    print("\nAll databases on this MongoDB:")
    admin = client.admin
    for db_name in admin.list_database_names():
        if db_name not in ["admin", "local", "config"]:
            db_obj = client[db_name]
            print(f"  - {db_name}")
            for coll in db_obj.list_collection_names():
                count = db_obj[coll].count_documents({})
                print(f"      • {coll}: {count} documents")
    
    client.close()
    
except Exception as e:
    print(f"Error: {e}")
