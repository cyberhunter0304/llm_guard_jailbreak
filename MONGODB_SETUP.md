# MongoDB Integration - Setup Guide

## ✅ Changes Made

Your backend has been updated to use MongoDB for storing security logs instead of local JSON files. Here's what was changed:

### 1. **Configuration Updates** ([config.py](config.py))
- Added MongoDB connection settings
- Added database and collection names configuration

### 2. **New MongoDB Storage Module** ([mongodb_storage.py](mongodb_storage.py))
- Created `mongodb_storage.py` with full MongoDB integration
- Replaces file-based JSON storage
- Thread-safe operations with MongoDB
- Functions:
  - `connect_mongodb()` - Initialize connection
  - `load_bot_security_log()` - Fetch security logs
  - `save_bot_security_log()` - Store security logs
  - `get_unprocessed_conversations()` - Batch processing
  - `mark_conversation_processed()` - Track progress
  - `get_processing_stats()` - View statistics

### 3. **Updated Main API** ([main.py](main.py))
- Changed imports from `storage` to `mongodb_storage`
- Added MongoDB connection on startup
- Added MongoDB cleanup on shutdown
- Added 3 new batch processing endpoints

### 4. **Dependencies** ([requirements.txt](requirements.txt))
- Added `pymongo==4.6.1`

---

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
cd d:\iNextLabs\Projects\Guardrails\LLM_Guard
pip install -r requirements.txt
```

### 2. Configure MongoDB Connection
Create or update `.env` file in the project root:

```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=llm_guard

# Existing configs...
OPENROUTER_API_KEY=your_api_key_here
```

**For MongoDB Atlas (Cloud)** instead of localhost:
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=llm_guard
```

### 3. Start MongoDB
**Option A: Local MongoDB**
```bash
# Windows
mongod

# Or with Homebrew (Mac)
brew services start mongodb-community
```

**Option B: MongoDB Atlas** (Cloud - no setup needed, just update MONGODB_URI)

---

## 📊 New Batch Processing Endpoints

Your API now has 3 endpoints for processing 21k conversations one-by-one:

### 1. **Process Next Conversation** (Recommended for real-time UI)
```
POST /api/batch/process-next
```

Processes ONE conversation, saves it to MongoDB, returns results immediately.

**Response Example:**
```json
{
  "success": true,
  "processed": true,
  "conversation_id": "conv_123",
  "security_log_id": "batch_processing_conv_123",
  "scan_results": {
    "is_safe": true,
    "risk_level": "SAFE",
    "pii_detected": false,
    "threat_detected": false,
    "scan_duration": 2.345
  },
  "processing_stats": {
    "total_conversations": 21000,
    "processed_conversations": 145,
    "pending_conversations": 20855,
    "processing_percentage": 0.69
  }
}
```

### 2. **Get Processing Status**
```
GET /api/batch/status
```

Returns statistics about batch processing progress.

**Response Example:**
```json
{
  "success": true,
  "stats": {
    "total_conversations": 21000,
    "processed_conversations": 150,
    "pending_conversations": 20850,
    "processing_percentage": 0.71,
    "total_security_logs": 150,
    "total_security_events": 150
  }
}
```

### 3. **Bulk Process Conversations** (For faster processing)
```
POST /api/batch/process-bulk?count=100
```

Processes multiple conversations (default 10, max as needed).

---

## 📱 Frontend Integration Example

The frontend can poll the `/api/batch/process-next` endpoint continuously:

```javascript
async function processBatch() {
  while (true) {
    const response = await fetch('http://localhost:8000/api/batch/process-next', {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (!data.processed) {
      console.log('✅ All conversations processed!');
      break;
    }
    
    // Update UI with progress
    console.log(`Progress: ${data.processing_stats.processing_percentage}%`);
    console.log(`Processed: ${data.processing_stats.processed_conversations}/${data.processing_stats.total_conversations}`);
    
    // Optional: Add small delay to avoid overwhelming
    await new Promise(r => setTimeout(r, 100));
  }
}
```

---

## 🗄️ MongoDB Collections

Your MongoDB will have these collections:

### **security_logs**
Stores security scan results for each processed conversation:
```
{
  "bot_id": "batch_processing_conv_123",
  "conversation_id": "conv_123",
  "created_at": "2026-01-30T10:00:00",
  "security_events": [...],
  "total_prompts": 1,
  "pii_detections": 0,
  "blocked_prompts": 0,
  "jailbreak_attempts": 0,
  "toxicity_detections": 0,
  "last_updated": "2026-01-30T10:00:00"
}
```

### **conversations**
Original conversations from your database:
```
{
  "conversation_id": "conv_123",
  "message": "The conversation text",
  "processed": true,
  "processed_at": "2026-01-30T10:00:00",
  "security_log_id": "batch_processing_conv_123"
}
```

---

## ⚙️ How It Works

1. **Process One**: Call `/api/batch/process-next`
2. **Fetch Conversation**: Gets one unprocessed conversation from `conversations` collection
3. **Scan**: Runs security scanners (PII, toxicity, injection, etc.)
4. **Store**: Saves security log to `security_logs` collection
5. **Mark**: Updates conversation as `processed: true`
6. **Return**: Sends results + progress stats to frontend
7. **Repeat**: Frontend calls endpoint again for next conversation

This ensures:
- ✅ Zero data loss (each scan is immediately saved)
- ✅ Real-time progress tracking (stats with each response)
- ✅ Can stop/restart anytime
- ✅ Frontend stays responsive (processes one at a time)
- ✅ Scalable (works for 21k+ conversations)

---

## 🔍 Existing Endpoints Still Work

All your existing API endpoints work as before but now use MongoDB:
- `POST /api/chat` - Chat with bot (saves to MongoDB)
- `GET /api/security/{bot_id}` - Retrieve security logs from MongoDB
- `GET /api/security` - List all bot sessions from MongoDB
- `DELETE /api/security/{bot_id}` - Delete security logs from MongoDB
- `GET /api/stats` - API statistics

---

## 🐛 Troubleshooting

**Issue: MongoDB connection failed**
```
Solution: Ensure MongoDB is running and MONGODB_URI is correct in .env
```

**Issue: "No more conversations to process"**
```
Solution: Check if conversations collection exists and has documents with `processed: false`
```

**Issue: Slow processing**
```
Solution: Check MongoDB performance, ensure indexes are created
```

---

## ✨ Next Steps

1. **Install pymongo**: `pip install -r requirements.txt`
2. **Set up MongoDB** (local or Atlas)
3. **Update .env** with MongoDB connection string
4. **Start backend**: `python main.py`
5. **Call `/api/batch/process-next`** to start processing!

Good luck with processing your 21k conversations! 🚀
