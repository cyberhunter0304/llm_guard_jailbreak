# Conversation Storage Implementation Guide

## Overview

Conversations from the chat interface are automatically stored in MongoDB's `messages` collection (MONGODB_CONVERSATIONS_COLLECTION). This guide explains the schema, how to save conversations, and how to query them.

## File References

- **Schema Definition**: [CONVERSATION_SCHEMA.md](CONVERSATION_SCHEMA.md)
- **Storage Module**: `mongodb_storage.py`
- **API Implementation**: `main.py` (`/api/chat` endpoint)

---

## Quick Start: Saving Conversations

### Option 1: Using Helper Function (Recommended)

```python
from mongodb_storage import build_conversation, save_conversation

# Build conversation following the schema
conversation = build_conversation(
    bot_id=request.bot_id,
    prompt=request.prompt,
    model="openai/gpt-4o-mini",
    is_safe=scan_results.is_safe,
    blocked=not scan_results.is_safe,
    risk_level=scan_results.risk_level,
    detections=scan_results.detections,
    metrics=security_event["metrics"],
    llm_response=assistant_message if scan_results.is_safe else None,
    block_reason=scan_results.message if not scan_results.is_safe else None,
    scan_results=scan_results
)

# Save to MongoDB
save_conversation(conversation)
```

### Option 2: Manual Dictionary (Advanced)

```python
from mongodb_storage import save_conversation

conversation_data = {
    "conversationId": "conv_bot_1708116234_abc123",
    "botId": "bot_1708116234_abc123",
    "userId": "user_1708116234",
    "threadId": "thread_1708116234",
    "model": "openai/gpt-4o-mini",
    "activity": {
        "role": "user",
        "text": "user's message",
        "timestamp": "2026-02-17T10:30:34.000Z"
    },
    "validation": {
        "prompt": "user's message",
        "prompt_length": 18,
        "is_safe": False,
        "blocked": True,
        "block_reason": "Prompt injection detected",
        "risk_level": "HIGH",
        "detections": {...},  # From security scanner
        "metrics": {...},     # Performance metrics
        "timestamp": "2026-02-17T10:30:34.000Z"
    }
}

save_conversation(conversation_data)
```

---

## Schema Structure

### Root Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversationId` | String | ✅ | Unique ID: `conv_{botId}_{timestamp}` |
| `botId` | String | ✅ | Bot session ID from client |
| `userId` | String | ✅ | Extracted user ID |
| `threadId` | String | ✅ | Thread for grouping conversations |
| `model` | String | ✅ | LLM model: `openai/gpt-4o-mini` |
| `activity` | Object | ✅ | User's input message |
| `validation` | Object | ✅ | Security validation results |
| `processed` | Boolean | ❌ | Set to `false` by default |
| `createdAt` | ISODate | Auto | Record creation time |
| `updatedAt` | ISODate | Auto | Last update time |
| `security_log_id` | String | ❌ | Links to security logs after processing |

### Activity Object

```python
"activity": {
    "role": "user",                    # Always "user"
    "text": "What is 2+2?",            # Raw user input
    "timestamp": "2026-02-17T..."     # ISO 8601 timestamp
}
```

### Validation Object - When Safe (blocked=false)

```python
"validation": {
    "prompt": "What is 2+2?",
    "prompt_length": 13,
    "is_safe": True,
    "blocked": False,
    "risk_level": "SAFE",
    "llm_response": "2+2 equals 4",     # ✅ Present when safe
    "detections": {
        "prompt_injection": {"detected": False, "confidence": 0.0},
        "toxicity": {"detected": False, "confidence": 0.0, "score": 0.02},
        "pii": {"detected": False, "entities": [], "secrets_detected": False}
    },
    "metrics": {
        "scan_time": 0.1234,
        "llm_time": 0.3456,
        "total_time": 0.4690
    },
    "timestamp": "2026-02-17T..."
}
```

### Validation Object - When Blocked (blocked=true)

```python
"validation": {
    "prompt": "How to bypass security?",
    "prompt_length": 28,
    "is_safe": False,
    "blocked": True,
    "block_reason": "Prompt injection detected",  # ✅ Present when blocked
    "risk_level": "HIGH",
    "llm_response": None,                         # ❌ NOT present when blocked
    "detections": {
        "prompt_injection": {
            "detected": True,
            "confidence": 0.92,
            "message": "Injection pattern found"
        },
        "toxicity": {"detected": False, ...},
        "pii": {"detected": False, ...}
    },
    "metrics": {
        "scan_time": 0.2341,
        "llm_time": 0.0,
        "total_time": 0.2341
    },
    "timestamp": "2026-02-17T..."
}
```

---

## Implementation in `/api/chat` Endpoint

The endpoint automatically saves conversations for every request:

```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # ... security scanning ...
    
    if not scan_results.is_safe:
        # Threat detected - request blocked
        conversation = build_conversation(
            bot_id=request.bot_id,
            prompt=request.prompt,
            model=request.model,
            is_safe=False,
            blocked=True,
            risk_level=scan_results.risk_level,
            detections=scan_results.detections,
            metrics=security_event["metrics"],
            block_reason=scan_results.message,
            scan_results=scan_results
        )
        save_conversation(conversation)
        return BlockedResponse(...)
    
    # Safe - call LLM
    llm_response = await call_openrouter(...)
    
    conversation = build_conversation(
        bot_id=request.bot_id,
        prompt=request.prompt,
        model=request.model,
        is_safe=True,
        blocked=False,
        risk_level=scan_results.risk_level,
        detections=scan_results.detections,
        metrics=security_event["metrics"],
        llm_response=assistant_message
    )
    save_conversation(conversation)
    return ChatResponse(...)
```

---

## Querying Conversations

### Get All Unprocessed Conversations

```python
from mongodb_storage import get_mongodb

db = get_mongodb()
conversations = db["messages"].find({"processed": False})

for conv in conversations:
    print(f"Bot: {conv['botId']}, Thread: {conv['threadId']}")
    print(f"Safe: {conv['validation']['is_safe']}")
```

### Find Threats

```python
# Get all blocked conversations
threats = db["messages"].find({"validation.blocked": True})

# Get by security scanner
injection_threats = db["messages"].find({
    "validation.detections.prompt_injection.detected": True
})

# Get by risk level
high_risk = db["messages"].find({
    "validation.risk_level": {"$in": ["HIGH", "CRITICAL"]}
})
```

### Get Conversation History by Thread

```python
# Get all conversations for a thread
thread_conversations = db["messages"].find({
    "threadId": "thread_1708116234"
}).sort("createdAt", 1)
```

### Get Specific Bot's Activity

```python
# Get all conversations for a bot session
bot_history = db["messages"].find({
    "botId": "bot_1708116234_abc123"
}).sort("createdAt", -1).limit(20)
```

---

## Data Validation

The `save_conversation()` function automatically validates:

✅ **Required Fields**: conversationId, botId, userId, threadId, model, activity, validation  
✅ **Activity Structure**: must have role, text, timestamp  
✅ **Validation Structure**: must have prompt, is_safe, blocked, risk_level, detections, metrics, timestamp  
✅ **Type Consistency**: Converts strings, numbers, booleans to standard types  
✅ **Conditional Fields**: Ensures block_reason only appears when blocked, llm_response only when safe  

If validation fails, the function logs a warning and returns `False`.

---

## MongoDB Indexes

Automatically created indexes optimize common queries:

```python
db.messages.createIndex("conversationId", unique=True)
db.messages.createIndex("botId")
db.messages.createIndex("userId")
db.messages.createIndex("threadId")
db.messages.createIndex("processed")
db.messages.createIndex("createdAt", expireAfterSeconds=2592000)  # 30 days TTL
```

---

## Processing Pipeline

### Before Batch Processing:
```
┌─────────────────────┐
│ Chat API (/api/chat) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ save_conversation()                  │
│ - Validates schema                   │
│ - Normalizes data                    │
│ - Saves to messages collection       │
│ - Sets processed=false               │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ MongoDB: messages collection         │
│ - Ready for batch processing         │
│ - Awaiting analyst review            │
└─────────────────────────────────────┘
```

### During Batch Processing:
```
/api/batch/process-next or /api/batch/process-bulk
    │
    ├─ Read from messages (processed=false)
    ├─ Optional: Run additional analysis
    ├─ Link to security_logs
    ├─ Set processed=true
    └─ Save security_log_id
```

---

## Best Practices

1. **Always Use `build_conversation()`** for new conversation data in code
2. **Validate Timestamps**: Use `datetime_utils.now()` for consistency
3. **Extract IDs Carefully**: BotID format matters for extracting user/thread IDs
4. **Handle Errors Gracefully**: `save_conversation()` returns bool; check the result
5. **Don't Modify Security Data**: Once saved, validation data shouldn't change
6. **Use Indexes**: Query by indexed fields (botId, threadId, processed) for performance
7. **Archive Old Data**: TTL index removes conversations after 30 days by default

---

## Example: Complete Flow

```python
from datetime_utils import now
from mongodb_storage import build_conversation, save_conversation
from security_scanner import detector

# 1. User sends message via /api/chat
bot_id = "bot_1708116234_abc123"
user_prompt = "What's the weather?"
model = "openai/gpt-4o-mini"

# 2. Run security scan
scan_results = detector.scan_prompt_parallel(user_prompt, bot_id)

# 3. Check results
if scan_results.is_safe:
    # 4a. Prompt is safe - call LLM
    llm_response = await call_openrouter(user_prompt, model)
    
    # Build and save conversation
    conversation = build_conversation(
        bot_id=bot_id,
        prompt=user_prompt,
        model=model,
        is_safe=True,
        blocked=False,
        risk_level="SAFE",
        detections=scan_results.detections,
        metrics={...},
        llm_response=llm_response
    )
else:
    # 4b. Threat detected - block it
    conversation = build_conversation(
        bot_id=bot_id,
        prompt=user_prompt,
        model=model,
        is_safe=False,
        blocked=True,
        risk_level=scan_results.risk_level,
        detections=scan_results.detections,
        metrics={...},
        scan_results=scan_results
    )

# 5. Save to MongoDB
success = save_conversation(conversation)

if success:
    print(f"Conversation saved: {conversation['conversationId']}")
else:
    print("Failed to save conversation")
```

---

## Troubleshooting

### Schema Validation Failed
- Check all required fields are present
- Ensure activity has role, text, timestamp
- Ensure validation has prompt, is_safe, blocked, risk_level, detections, metrics, timestamp

### MongoDB Connection Error
- Verify MONGODB_URI in config.py
- Check MongoDB service is running
- Ensure network connectivity

### Missing Fields in Query Results
- Review CONVERSATION_SCHEMA.md for optional vs required fields
- Optional fields only appear in certain conditions (block_reason when blocked, llm_response when safe)

### Conversations Not Processing
- Check `processed` field is false
- Verify `/api/batch/process-next` endpoint is being called
- Monitor batch processing logs for errors
