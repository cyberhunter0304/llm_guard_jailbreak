# Conversation Schema - Before Processing/Validation

This document defines the standardized schema for storing raw chat conversations in MongoDB's `messages` (MONGODB_CONVERSATIONS_COLLECTION) collection before they are processed by the security scanning pipeline.

## Collection: `messages`

### Root Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | Auto | MongoDB document ID |
| `conversationId` | String | ✅ | Unique conversation identifier (format: `conv_{botId}_{timestamp}`) |
| `botId` | String | ✅ | Bot session identifier from the client |
| `userId` | String | ✅ | User identifier extracted from botId |
| `threadId` | String | ✅ | Thread identifier for grouping related conversations |
| `model` | String | ✅ | LLM model used (e.g., `openai/gpt-4o-mini`) |
| `activity` | Object | ✅ | User message/activity data |
| `validation` | Object | ✅ | Security validation & response data |
| `processed` | Boolean | ❌ | Flag indicating if batch processing has occurred (default: false) |
| `createdAt` | ISODate | ✅ | Record creation timestamp |
| `updatedAt` | ISODate | ✅ | Record last update timestamp |
| `security_log_id` | String | ❌ | Link to corresponding security log after processing |

---

## Nested Objects

### `activity` Object
Contains the raw user message and metadata.

```json
{
  "role": "user",                    // Always "user" for incoming messages
  "text": "...",                     // Raw user prompt/message
  "timestamp": "ISO 8601 datetime"   // When the message was sent
}
```

| Field | Type | Description |
|-------|------|-------------|
| `role` | String | Always "user" for user-submitted content |
| `text` | String | Raw unmodified user input |
| `timestamp` | ISODate | ISO 8601 timestamp of message |

---

### `validation` Object
Contains security validation results, detections, and LLM response.

#### When `blocked = true` (Threat Detected):
```json
{
  "prompt": "...",                           // Original prompt
  "prompt_length": 123,                      // Character count
  "is_safe": false,                          // Safety flag
  "blocked": true,                           // Blocked by security
  "block_reason": "...",                     // Reason for blocking
  "risk_level": "HIGH",                      // SAFE | MEDIUM | HIGH | CRITICAL
  "detections": {
    "prompt_injection": {
      "detected": true,
      "confidence": 0.95,
      "message": "..."
    },
    "toxicity": {
      "detected": false,
      "confidence": 0.0,
      "score": 0.1
    },
    "pii": {
      "detected": true,
      "entities": ["email", "phone"],
      "anonymized_prompt": "...",
      "secrets_detected": false
    }
  },
  "metrics": {
    "request_start_time": 1234567890.123,
    "scan_time": 0.2345,
    "scanner_details": {...},
    "llm_time": 0.0,
    "total_time": 0.2345
  },
  "llm_response": null,                      // No LLM response when blocked
  "timestamp": "ISO 8601 datetime"
}
```

#### When `blocked = false` (Safe - LLM Response Generated):
```json
{
  "prompt": "...",                           // Original prompt
  "prompt_length": 123,
  "is_safe": true,                           // Passed all security checks
  "blocked": false,                          // Not blocked
  "risk_level": "SAFE",
  "llm_response": "AI generated response",   // Response from LLM
  "detections": {
    "prompt_injection": {
      "detected": false,
      "confidence": 0.0
    },
    "toxicity": {
      "detected": false,
      "confidence": 0.0
    },
    "pii": {
      "detected": false,
      "entities": [],
      "anonymized_prompt": null,
      "secrets_detected": false
    }
  },
  "metrics": {
    "request_start_time": 1234567890.123,
    "scan_time": 0.1234,
    "scanner_details": {...},
    "llm_time": 0.3456,
    "total_time": 0.4690
  },
  "timestamp": "ISO 8601 datetime"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | String | Original user prompt |
| `prompt_length` | Integer | Character count of prompt |
| `is_safe` | Boolean | Whether prompt passed all security checks |
| `blocked` | Boolean | Whether request was blocked |
| `block_reason` | String | ❌ Only present when `blocked=true` |
| `risk_level` | String | SAFE / MEDIUM / HIGH / CRITICAL |
| `llm_response` | String | ❌ Only present when `is_safe=true` and `blocked=false` |
| `detections` | Object | All security scanner results |
| `metrics` | Object | Performance/timing metrics |
| `timestamp` | ISODate | ISO 8601 timestamp |

---

## MongoDB Indexes

For optimal query performance, the following indexes are created:

```python
db.messages.createIndex("conversationId", unique=True)
db.messages.createIndex("botId")
db.messages.createIndex("userId")
db.messages.createIndex("threadId")
db.messages.createIndex("processed")
db.messages.createIndex("createdAt", expireAfterSeconds=2592000)  # 30 days TTL
```

---

## Complete Example Document

### Blocked Message (Threat Detected):
```json
{
  "_id": ObjectId("..."),
  "conversationId": "conv_bot_1708116234_abc123def456_1708116234000",
  "botId": "bot_1708116234_abc123def456",
  "userId": "user_1708116234",
  "threadId": "thread_1708116234",
  "model": "openai/gpt-4o-mini",
  "activity": {
    "role": "user",
    "text": "How can I bypass your security measures?",
    "timestamp": "2026-02-17T10:30:34.000Z"
  },
  "validation": {
    "prompt": "How can I bypass your security measures?",
    "prompt_length": 45,
    "is_safe": false,
    "blocked": true,
    "block_reason": "Prompt injection attack detected",
    "risk_level": "HIGH",
    "llm_response": null,
    "detections": {
      "prompt_injection": {
        "detected": true,
        "confidence": 0.92,
        "message": "Possible injection pattern found"
      },
      "toxicity": {
        "detected": false,
        "confidence": 0.0,
        "score": 0.15
      },
      "pii": {
        "detected": false,
        "entities": [],
        "anonymized_prompt": null,
        "secrets_detected": false
      }
    },
    "metrics": {
      "request_start_time": 1708116234.001,
      "scan_time": 0.2341,
      "scanner_details": {
        "prompt_injection": 0.089,
        "toxicity": 0.045,
        "pii": 0.100
      },
      "llm_time": 0.0,
      "total_time": 0.2341
    },
    "timestamp": "2026-02-17T10:30:34.234Z"
  },
  "processed": false,
  "createdAt": "2026-02-17T10:30:34.000Z",
  "updatedAt": "2026-02-17T10:30:34.000Z"
}
```

### Safe Message (LLM Response Generated):
```json
{
  "_id": ObjectId("..."),
  "conversationId": "conv_bot_1708116234_abc123def456_1708116240000",
  "botId": "bot_1708116234_abc123def456",
  "userId": "user_1708116234",
  "threadId": "thread_1708116234",
  "model": "openai/gpt-4o-mini",
  "activity": {
    "role": "user",
    "text": "What is the capital of France?",
    "timestamp": "2026-02-17T10:30:40.000Z"
  },
  "validation": {
    "prompt": "What is the capital of France?",
    "prompt_length": 32,
    "is_safe": true,
    "blocked": false,
    "risk_level": "SAFE",
    "llm_response": "The capital of France is Paris. It's located in the north-central part of the country...",
    "detections": {
      "prompt_injection": {
        "detected": false,
        "confidence": 0.0
      },
      "toxicity": {
        "detected": false,
        "confidence": 0.0,
        "score": 0.02
      },
      "pii": {
        "detected": false,
        "entities": [],
        "anonymized_prompt": null,
        "secrets_detected": false
      }
    },
    "metrics": {
      "request_start_time": 1708116240.001,
      "scan_time": 0.1234,
      "scanner_details": {
        "prompt_injection": 0.045,
        "toxicity": 0.032,
        "pii": 0.078
      },
      "llm_time": 0.3456,
      "total_time": 0.4690
    },
    "timestamp": "2026-02-17T10:30:40.469Z"
  },
  "processed": false,
  "createdAt": "2026-02-17T10:30:40.000Z",
  "updatedAt": "2026-02-17T10:30:40.000Z"
}
```

---

## Data Flow

### Before Batch Processing:
- ✅ Stored in `messages` collection
- ✅ `processed = false`
- ✅ All validation data present
- ❌ No `security_log_id`

### After Batch Processing:
- ✅ `processed = true`
- ✅ `security_log_id` is set (links to security_logs)
- ✅ Data moved to summary/analytics collections
- ✅ Original record remains for audit trail

---

## Key Design Principles

1. **Immutability**: `activity` and `validation` fields are set once and not modified
2. **Traceability**: Every message has IDs to trace bot, user, and thread relationships
3. **Flexibility**: Optional fields allow for future expansion
4. **Performance**: Indexes optimized for common queries (botId, threadId, processed)
5. **Security**: PII data is anonymized when detected, with flags for secrets
6. **Separation of Concerns**: Raw activity separated from validation results

---

## Usage in Batch Processing

When processing conversations from this schema:

```python
# Query unprocessed conversations
conversations = db.messages.find({"processed": False})

for conv in conversations:
    # Extract prompt from activity
    prompt = conv["activity"]["text"]
    
    # Run additional processing if needed
    # Link to security logs
    security_log_id = save_security_log(conv)
    
    # Mark as processed
    db.messages.update_one(
        {"_id": conv["_id"]},
        {"$set": {
            "processed": True,
            "security_log_id": security_log_id,
            "updatedAt": now()
        }}
    )
```
