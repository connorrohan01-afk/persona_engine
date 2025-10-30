# Orchestration Engine Documentation

## Overview

The orchestration engine enables "build by prompting" through the `/api/v1/brain` endpoint. It executes sequences of actions across multiple services with intelligent fallbacks when API keys are missing.

## Endpoint

**POST `/api/v1/brain`**

Execute a plan consisting of one or more actions in sequence.

## Request Schema

```json
{
  "actions": [
    {
      "id": "optional_action_id",
      "type": "action.type",
      "params": {
        "param1": "value1",
        "param2": "value2"
      },
      "continue_on_error": false
    }
  ],
  "metadata": {
    "trace_id": "optional_trace_id"
  }
}
```

## Response Schema

```json
{
  "ok": true,
  "trace_id": "trace_1234567890_abcd1234",
  "results": [
    {
      "id": "action_id",
      "type": "action.type",
      "status": "ok|mock|error",
      "output": {},
      "ms": 123.45,
      "error": "error_code",
      "details": "error description"
    }
  ],
  "metadata": {
    "total_actions": 3,
    "completed_actions": 3,
    "total_ms": 456.78
  }
}
```

## Supported Actions

### Orchestration Engine Action Types

The orchestration engine now supports both direct service calls and HTTP endpoint calls, giving you flexibility in how you compose workflows.

#### Direct Service Actions

### 1. chat.generate
Generate text content using AI models.

**Parameters:**
- `prompt` (required): Text prompt for generation
- `max_tokens` (optional): Maximum tokens to generate (default: 150)

**Example:**
```json
{
  "id": "generate_tweet",
  "type": "chat.generate",
  "params": {
    "prompt": "Write a engaging tweet about AI automation",
    "max_tokens": 100
  }
}
```

### 2. image.generate
Generate images using AI models.

**Parameters:**
- `prompt` (required): Image description prompt
- `style` (optional): Style modifier
- `size` (optional): Image size in "WIDTHxHEIGHT" format (default: "1024x1024")

**Example:**
```json
{
  "id": "create_hero_image",
  "type": "image.generate",
  "params": {
    "prompt": "Professional workspace with laptop and coffee",
    "style": "photorealistic",
    "size": "1024x1024"
  }
}
```

### 3. poster.publish
Publish content to social platforms (stub implementation).

**Parameters:**
- `platform` (optional): Target platform name
- `content` (required): Content to publish

**Example:**
```json
{
  "id": "post_to_twitter",
  "type": "poster.publish",
  "params": {
    "platform": "twitter",
    "content": "Check out our new feature!"
  }
}
```

### 4. vault.store
Store key-value data with persistence.

**Parameters:**
- `key` (required): Storage key
- `value` (required): Data to store (any JSON-serializable type)

**Example:**
```json
{
  "id": "save_config",
  "type": "vault.store",
  "params": {
    "key": "user_preferences",
    "value": {"theme": "dark", "notifications": true}
  }
}
```

### 5. vault.get
Retrieve stored data by key.

**Parameters:**
- `key` (required): Storage key to retrieve
- `default` (optional): Default value if key not found

**Example:**
```json
{
  "id": "load_config",
  "type": "vault.get",
  "params": {
    "key": "user_preferences",
    "default": {"theme": "light"}
  }
}
```

### 6. telegram.send
Send messages via Telegram Bot API.

**Parameters:**
- `text` (required): Message text to send
- `chat_id` (optional): Override default chat ID

**Example:**
```json
{
  "id": "notify_completion",
  "type": "telegram.send",
  "params": {
    "text": "Task completed successfully! ✅",
    "chat_id": "-1001234567890"
  }
}
```

### 7. qdrant.upsert
Insert or update vector data in Qdrant database.

**Parameters:**
- `collection` (optional): Collection name (default: from QDRANT_COLLECTION or "brain")
- `id` (optional): Point ID (auto-generated if not provided)
- `vector` (optional): Vector data (mock vector generated if not provided)
- `payload` (optional): Associated metadata

**Example:**
```json
{
  "id": "store_embedding",
  "type": "qdrant.upsert",
  "params": {
    "collection": "documents",
    "id": "doc_123",
    "vector": [0.1, 0.2, 0.3, ...],
    "payload": {"title": "Important Document", "category": "research"}
  }
}
```

### 8. qdrant.search
Search vectors by similarity in Qdrant database.

**Parameters:**
- `collection` (optional): Collection name (default: from QDRANT_COLLECTION or "brain")
- `vector` (required): Query vector for similarity search
- `limit` (optional): Maximum results to return (default: 3)
- `score_threshold` (optional): Minimum similarity score (default: 0.5)

**Example:**
```json
{
  "id": "find_similar",
  "type": "qdrant.search",
  "params": {
    "collection": "documents",
    "vector": [0.1, 0.2, 0.3, ...],
    "limit": 5,
    "score_threshold": 0.7
  }
}
```

## Environment Variables

### Core Services
- `OPENAI_API_KEY`: OpenAI API key for chat and image generation
- `IMG_PROVIDER`: Image provider ("openai", "stability", "mock") - default: "mock"
- `STABILITY_API_KEY`: Stability AI API key for image generation

### Telegram Integration
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for sending messages
- `TELEGRAM_CHAT_ID`: Default chat ID for telegram.send actions

### Vector Database (Qdrant)
- `QDRANT_URL`: Qdrant server URL
- `QDRANT_API_KEY`: Qdrant API key (if required)
- `QDRANT_COLLECTION`: Default collection name (default: "brain")

## Context Passing

Actions can reference outputs from previous actions using `{{action_id}}` syntax in their parameters. You can also navigate to specific fields using dot notation:

```json
{
  "actions": [
    {
      "id": "generate_content",
      "type": "chat.generate",
      "params": {
        "prompt": "Write a tweet about automation"
      }
    },
    {
      "id": "create_image",
      "type": "image.generate",
      "params": {
        "prompt": "Create an image for: {{generate_content.output.content}}",
        "size": "1024x1024"
      }
    },
    {
      "id": "publish_post",
      "type": "auto.post",
      "params": {
        "platform": "twitter",
        "content": "{{generate_content.output.content}}",
        "media": "{{create_image.output.file_url}}"
      }
    }
  ]
}
```

### Advanced Context References

- `{{action_id}}` - References the entire output object
- `{{action_id.output}}` - References the output field specifically
- `{{action_id.output.field}}` - References a specific field in the output
- `{{action_id.status}}` - References the action status
- `{{action_id.output.response.data}}` - Deep navigation for endpoint calls

## Error Handling

- By default, execution stops on first error
- Set `continue_on_error: true` on individual actions to continue on failure
- HTTP status codes:
  - `200`: All actions succeeded
  - `207`: Partial success (some actions failed but execution continued)
  - `400`: Invalid request schema
  - `500`: Server error

## Mock Fallbacks

When API keys are missing, services gracefully fall back to mock implementations:

- **chat.generate**: Returns mock text responses
- **image.generate**: Creates placeholder images with Pillow
- **telegram.send**: Logs messages instead of sending
- **qdrant.upsert/search**: Uses local JSON file persistence

Mock responses are marked with `"status": "mock"` in results.

#### HTTP Endpoint Actions

### 9. endpoint.call
Make generic HTTP requests to internal API endpoints.

**Parameters:**
- `endpoint` (required): API endpoint path (e.g., "/api/v1/reddit-scraper")
- `method` (optional): HTTP method (default: "POST")
- `payload` (optional): Request payload/parameters

**Example:**
```json
{
  "id": "call_custom_endpoint",
  "type": "endpoint.call",
  "params": {
    "endpoint": "/api/v1/custom-service",
    "method": "POST",
    "payload": {"data": "example"}
  }
}
```

### 10. reddit.scrape
Call the Reddit scraper endpoint.

**Parameters:**
- Any parameters supported by the `/api/v1/reddit-scraper` endpoint

**Example:**
```json
{
  "id": "scrape_subreddit",
  "type": "reddit.scrape",
  "params": {
    "subreddit": "technology",
    "limit": 10,
    "sort": "hot"
  }
}
```

### 11. auto.post
Call the auto poster endpoint for publishing content.

**Parameters:**
- Any parameters supported by the `/api/v1/auto-poster` endpoint

**Example:**
```json
{
  "id": "publish_content",
  "type": "auto.post",
  "params": {
    "platform": "twitter",
    "content": "Check out this cool automation!",
    "schedule": "immediate"
  }
}
```

### 12. vault.manage
Call the vault manager endpoint for advanced storage operations.

**Parameters:**
- Any parameters supported by the `/api/v1/vault-manager` endpoint

**Example:**
```json
{
  "id": "manage_vault",
  "type": "vault.manage",
  "params": {
    "operation": "backup",
    "target": "s3://my-bucket/vault-backup"
  }
}
```

### 13. chatbot.chat
Call the chatbot engine endpoint for conversational AI.

**Parameters:**
- `user_id` (required): User identifier
- `message` (required): Message text
- `context` (optional): Conversation context

**Example:**
```json
{
  "id": "chat_response",
  "type": "chatbot.chat",
  "params": {
    "user_id": "user_123",
    "message": "What's the weather like?",
    "context": {"location": "San Francisco"}
  }
}
```

### 14. telegram.webhook
Call the Telegram webhook endpoint to simulate incoming messages.

**Parameters:**
- Telegram webhook payload structure

**Example:**
```json
{
  "id": "simulate_telegram",
  "type": "telegram.webhook",
  "params": {
    "message": {
      "chat": {"id": 12345},
      "text": "Hello from orchestration!"
    }
  }
}
```

## Logging

All actions are logged with:
- Action execution start/completion
- Timing information (milliseconds)
- Parameters (secrets filtered out)
- Success/failure status
- Overall trace completion

Example log output:
```
INFO - brain.execute: action_id=generate_tweet, type=chat.generate, params={"prompt": "Write a tweet"}
INFO - brain.completed: ✅ generate_tweet (chat.generate) - ok in 234.5ms
INFO - brain.finished: trace_id=trace_1234567890_abcd1234, success=true, actions=2/2, total_ms=456.7
```

## File Persistence

Mock data is persisted in the `data/` directory:
- `data/vault.json`: Key-value storage for vault actions
- `data/qdrant_mock.json`: Mock vector database collections
- `static/images/`: Generated images from image.generate actions
- `data/images/`: Image metadata JSON files