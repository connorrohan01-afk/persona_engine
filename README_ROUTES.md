# PersonaEngine API Routes Documentation

## Authentication
All routes (except `/health`, `/version`, and `/telegram/webhook`) require Bearer token authentication:
```
Authorization: Bearer <AUTH_BEARER_TOKEN>
```

## Global Parameters
- `tenant_id`: Tenant identifier (defaults to "owner")
- `dry`: Query parameter or `X-Dry-Run: 1` header for mock mode

## System Routes

### GET /api/v1/health
**Description**: Health check endpoint
**Auth**: None required
**Response**:
```json
{
  "ok": true,
  "db": "ok", 
  "time": "2024-01-01T00:00:00.000000"
}
```

### GET /api/v1/version
**Description**: Version information
**Auth**: None required
**Response**:
```json
{
  "name": "PersonaEngine",
  "version": "0.1.0"
}
```

### POST /api/v1/system/tick
**Description**: Trigger job processing
**Auth**: Required
**Response**:
```json
{
  "ok": true,
  "message": "Job processing triggered"
}
```

## Account Routes

### POST /api/v1/accounts/create
**Description**: Create a new account
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "username": "user123",
  "provider": "reddit"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "account_id": 12345,
  "username": "user123",
  "status": "created"
}
```

### POST /api/v1/accounts/warm
**Description**: Warm up an account
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 12345
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "account_id": 12345,
  "status": "warmed"
}
```

## Reddit Routes

### POST /api/v1/reddit/post
**Description**: Create a Reddit post
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 12345,
  "subreddit": "technology",
  "title": "Post title",
  "body": "Post content",
  "url": "https://example.com"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "post_id": "t3_mock123",
  "status": "posted"
}
```

### POST /api/v1/reddit/comment
**Description**: Create a Reddit comment
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 12345,
  "post_id": "t3_abc123",
  "body": "Comment text"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock", 
  "comment_id": "t1_mock456",
  "status": "commented"
}
```

### POST /api/v1/reddit/upvote
**Description**: Upvote a Reddit post
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 12345,
  "post_id": "t3_abc123"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "status": "upvoted"
}
```

## Scraper Routes

### POST /api/v1/scraper/run
**Description**: Run content scraper
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "target": "reddit",
  "subreddit": "technology",
  "limit": 10
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "items": [
    {
      "title": "Interesting Post About Technology",
      "url": "https://reddit.com/r/technology/comments/abc123",
      "subreddit": "technology", 
      "score": 1250
    }
  ]
}
```

## Image Routes

### POST /api/v1/image/generate
**Description**: Generate an image using AI
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "prompt": "A futuristic city",
  "style": "realistic",
  "size": "1024x1024"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "url": "https://example.com/generated/image123.jpg"
}
```

### POST /api/v1/image/upload
**Description**: Upload an image file
**Auth**: Required
**Request**: Multipart form with file
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "url": "https://example.com/uploads/mock_filename.jpg"
}
```

## Vault Storage Routes

### POST /api/v1/vaults/items
**Description**: Upload file to secure vault storage
**Auth**: Required
**Request**: Multipart form-data
- `file`: File upload (required)
- `name`: Custom filename (optional)
- `description`: Item description (optional) 
- `kind`: Item type - "file", "image", "video", "document" (default: "file")
- `public`: Make publicly accessible (default: false)
- `nsfw`: Mark as NSFW content (default: false)

**Response**:
```json
{
  "success": true,
  "item_id": "123",
  "name": "image.jpg",
  "size_bytes": 1024000,
  "storage_key": "owner/abc123.jpg",
  "existing": false
}
```

### POST /api/v1/vaults/items/base64
**Description**: Upload base64 content to vault storage
**Auth**: Required
**Request**: Form-data
- `content`: Base64-encoded file content (required)
- `name`: Filename (required)
- `mime_type`: MIME type (required)
- `description`: Item description (optional)
- `kind`: Item type (default: "file")
- `public`: Public access (default: false)
- `nsfw`: NSFW content (default: false)

**Response**: Same as file upload

### GET /api/v1/vaults/items
**Description**: List vault items for authenticated tenant
**Auth**: Required
**Query Parameters**:
- `kind`: Filter by item type
- `public_only`: Show only public items (default: false)
- `include_nsfw`: Include NSFW content (default: false)
- `limit`: Items per page (default: 50, max: 100)
- `offset`: Skip items (default: 0)

**Response**:
```json
[
  {
    "id": "123",
    "name": "image.jpg", 
    "kind": "image",
    "mime": "image/jpeg",
    "size_bytes": 1024000,
    "nsfw": false,
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### GET /api/v1/vaults/items/{item_id}
**Description**: Get vault item details
**Auth**: Required
**Response**:
```json
{
  "id": "123",
  "tenant_id": "owner",
  "persona_id": null,
  "name": "image.jpg",
  "kind": "image",
  "mime": "image/jpeg",
  "size_bytes": 1024000,
  "sha256": "abc123...",
  "storage_key": "owner/abc123.jpg",
  "public_url": "https://storage.example.com/...",
  "nsfw": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### DELETE /api/v1/vaults/items/{item_id}
**Description**: Delete a vault item from database (storage cleanup handled separately)
**Auth**: Required
**Example**:
```bash
curl -X DELETE http://localhost:8000/api/v1/vaults/items/123 \
  -H "Authorization: Bearer $TOKEN"
```
**Response**:
```json
{
  "success": true,
  "message": "Vault item deleted"
}
```

### POST /api/v1/vaults/items/{item_id}/links
**Description**: Create claim link for vault item
**Auth**: Required
**Request**: Form-data
- `ttl_s`: Link expiration in seconds (default: 3600)
- `max_uses`: Maximum uses before expiry (default: 1)

**Response**:
```json
{
  "success": true,
  "link_id": "456",
  "claim_code": "abc123def456...",
  "claim_url": "http://localhost:8000/api/v1/vaults/claim/abc123def456...",
  "expires_at": "2024-01-01T13:00:00Z",
  "max_uses": 1
}
```

### GET /api/v1/vaults/links
**Description**: List vault links for authenticated tenant
**Auth**: Required
**Query Parameters**:
- `active_only`: Show only active links (default: true)
- `limit`: Links per page (default: 50)
- `offset`: Skip links (default: 0)

**Response**:
```json
[
  {
    "id": "456",
    "vault_item_id": "123",
    "claim_code": "abc123def456...",
    "expires_at": "2024-01-01T13:00:00Z",
    "max_uses": 1,
    "used_count": 0,
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### DELETE /api/v1/vaults/links/{link_id}
**Description**: Delete/deactivate a vault link
**Auth**: Required
**Response**:
```json
{
  "success": true,
  "message": "Vault link deleted"
}
```

### GET /api/v1/vaults/sign/{item_id}
**Description**: Generate signed URL for direct vault item access
**Auth**: Required
**Query Parameters**:
- `expires_in`: URL expiration in seconds (default: 3600)

**Response**:
```json
{
  "signed_url": "https://storage.example.com/signed/abc123...",
  "expires_at": "2024-01-01T13:00:00Z"
}
```

### GET /api/v1/vaults/deliver/{item_id}
**Description**: Deliver vault content in different formats
**Auth**: Required
**Query Parameters**:
- `format`: Delivery format - "url", "json", "telegram" (default: "url")

**URL Format Response**:
```json
{
  "name": "image.jpg",
  "mime": "image/jpeg",
  "size_bytes": 1024000,
  "nsfw": false,
  "created_at": "2024-01-01T12:00:00Z",
  "signed_url": "https://storage.example.com/signed/..."
}
```

**Telegram Format Response**:
```json
{
  "name": "image.jpg",
  "mime": "image/jpeg", 
  "size_bytes": 1024000,
  "nsfw": false,
  "send_as_file": false,
  "signed_url": "https://storage.example.com/signed/...",
  "telegram_type": "photo"
}
```

### GET /api/v1/vaults/claim/{claim_code}
**Description**: Claim vault content using public claim link
**Auth**: None required
**Response**: Redirects to signed URL or returns JSON based on Accept header

### GET /api/v1/vaults/stats
**Description**: Get vault storage statistics for authenticated tenant
**Auth**: Required
**Response**:
```json
{
  "tenant_id": "owner",
  "storage_usage": {
    "total_size_bytes": 10240000,
    "total_items": 50,
    "by_kind": {
      "image": {"count": 30, "size": 8000000},
      "document": {"count": 20, "size": 2240000}
    }
  },
  "active_links": 5,
  "total_items": 50
}
```

### GET /api/v1/vaults/access-logs/{item_id}
**Description**: Get access logs for a vault item
**Auth**: Required
**Query Parameters**:
- `limit`: Log entries per page (default: 50)
- `offset`: Skip entries (default: 0)

**Response**:
```json
[
  {
    "id": "789",
    "vault_link_id": "456",
    "channel": "web",
    "action": "download", 
    "user_agent": "Mozilla/5.0...",
    "timestamp": "2024-01-01T12:30:00Z"
  }
]
```

### POST /api/v1/vaults/cleanup/expired
**Description**: Clean up expired vault links for authenticated tenant
**Auth**: Required
**Response**:
```json
{
  "success": true,
  "cleaned_links": 3,
  "message": "Cleaned up 3 expired links"
}
```

## Vault Security & Features

### Security Model
- **Tenant Isolation**: All vault operations scoped to authenticated tenant
- **Secure Claims**: Cryptographically secure claim codes (256-bit entropy)
- **Access Logging**: Comprehensive tracking of all vault access
- **Content Validation**: File type, size, and NSFW detection

### Storage Features
- **Multi-Backend**: Supports S3, Cloudflare R2, and local storage
- **Deduplication**: Automatic content-based deduplication by SHA256
- **Signed URLs**: Time-limited secure access without exposing storage keys
- **Public Claims**: Shareable links with expiration and usage limits

### Content Types
- **Images**: JPG, PNG, GIF, WebP with automatic NSFW detection
- **Documents**: PDF, DOC, TXT with content validation
- **Videos**: MP4, WebM with size and duration limits
- **Files**: General file storage with MIME type validation

## Link Routes

### POST /api/v1/link/shorten
**Description**: Shorten a URL
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "url": "https://example.com/long-url",
  "custom_slug": "my-link"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "link_id": "my-link",
  "short_url": "https://short.ly/my-link"
}
```

### POST /api/v1/link/click
**Description**: Track a link click
**Auth**: None required
**Query Params**: `link_id`, `tenant_id`, `persona_id`, `account_id`, `ref`
**Response**:
```json
{
  "ok": true,
  "redirect_url": "https://example.com/original-url",
  "tracked": true
}
```

## Telegram Routes

### POST /api/v1/telegram/deploy
**Description**: Deploy a Telegram bot
**Auth**: Required
**Request**:
```json
{
  "tenant_id": "owner",
  "bot_token": "bot_token_here",
  "webhook_url": "https://example.com/webhook"
}
```
**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "bot_username": "mock_bot",
  "webhook_url": "https://example.com/webhook"
}
```

### POST /api/v1/telegram/webhook
**Description**: Handle Telegram webhook
**Auth**: None required
**Request**: Telegram webhook payload
**Response**:
```json
{
  "ok": true
}
```

## Tool Routes

### POST /api/v1/build
**Description**: Generic build tool endpoint
**Auth**: Required
**Request**: Any JSON payload
**Response**:
```json
{
  "ok": true,
  "received": {...}
}
```

## Reddit Routes

### POST /api/v1/reddit/post
**Description**: Submit a post to Reddit with pre-flight validation and optional scheduling
**Auth**: Required (Bearer token)
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 123,
  "subreddit": "test",
  "kind": "self",
  "title": "My first Reddit post",
  "body": "This is the post content",
  "nsfw": false,
  "spoiler": false,
  "dry": false,
  "schedule": "2025-01-20T15:30:00Z"
}
```

**Request Fields**:
- `tenant_id`: Tenant identifier
- `account_id`: Reddit account ID
- `subreddit`: Target subreddit name (without r/ prefix)
- `kind`: Post type - "self", "link", or "image"
- `title`: Post title (max length varies by subreddit, typically 300 chars)
- `body`: Post body text (for self posts)
- `url`: URL for link posts
- `image_url`: Image URL for image posts
- `flair_text`: Optional flair text to match
- `nsfw`: Mark as NSFW (default: false)
- `spoiler`: Mark as spoiler (default: false)
- `dry`: Force dry-run mode (default: false)
- `schedule`: Optional ISO datetime for scheduled posting

**Immediate Post Response**:
```json
{
  "ok": true,
  "mode": "live",
  "post_id": "t3_abc123",
  "status": "posted",
  "subreddit": "test"
}
```

**Scheduled Post Response**:
```json
{
  "ok": true,
  "mode": "live",
  "status": "queued",
  "job_id": 456,
  "run_after": "2025-01-20T15:30:00Z",
  "subreddit": "test"
}
```

**Error Responses**:
- **429 Rate Limit**: `{"ok": false, "error_code": "ratelimit", "message": "Rate limit exceeded", "retry_after": 3600}`
- **400 Rules Violation**: `{"ok": false, "error_code": "rules", "message": "Title validation failed: too long"}`
- **400 Banned Word**: `{"ok": false, "error_code": "rules", "message": "Content contains banned word: spam"}`
- **404 Account**: `{"ok": false, "message": "Account not found"}`

### POST /api/v1/reddit/comment
**Description**: Submit a comment on a Reddit post or another comment
**Auth**: Required (Bearer token)
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 123,
  "post_id": "t3_abc123",
  "body": "This is my comment text"
}
```

**Request Fields**:
- `tenant_id`: Tenant identifier
- `account_id`: Reddit account ID
- `post_id`: Reddit thing ID (t3_ for posts, t1_ for comments)
- `body`: Comment text content

**Response**:
```json
{
  "ok": true,
  "mode": "live",
  "comment_id": "t1_def456",
  "status": "posted"
}
```

**Error Responses**:
- **429 Rate Limit**: `{"ok": false, "error_code": "ratelimit", "message": "Comment rate limit exceeded"}`
- **400 Validation**: `{"ok": false, "error_code": "validation", "message": "Invalid thing ID format"}`
- **400 Text Too Long**: `{"ok": false, "error_code": "validation", "message": "Comment text too long (max 10000 chars)"}`

### POST /api/v1/reddit/upvote
**Description**: Upvote a Reddit post or comment
**Auth**: Required (Bearer token)
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 123,
  "post_id": "t3_abc123"
}
```

**Request Fields**:
- `tenant_id`: Tenant identifier  
- `account_id`: Reddit account ID
- `post_id`: Reddit thing ID (t3_ for posts, t1_ for comments)

**Response**:
```json
{
  "ok": true,
  "mode": "live",
  "status": "ok"
}
```

**Error Responses**:
- **429 Rate Limit**: `{"ok": false, "error_code": "ratelimit", "message": "Vote rate limit exceeded"}`
- **400 Validation**: `{"ok": false, "error_code": "validation", "message": "Invalid thing ID format"}`
- **400 Reddit Error**: `{"ok": false, "error_code": "shadowban", "message": "Account may be shadowbanned"}`

## Reddit Rate Limiting

The Reddit endpoints implement comprehensive rate limiting:

### General Limits
- **Posts**: Max 2 per day, 2-4 hours between posts
- **Comments**: Max 5 per day, 15-30 minutes between comments  
- **Votes**: Max 30 per day, 2-5 minutes between votes

### Subreddit-Specific Limits
- **Per-Subreddit Posts**: 24-48 hours between posts to same subreddit
- **Rules Validation**: Pre-flight checks for title length, banned words, allowed post types
- **Automatic Flair Selection**: Matches flair_text to available subreddit flairs

### Cooldown System
- **Rate Limits**: Exponential backoff (10min → 20min → 40min, max 6 hours)
- **Shadowban**: 72-hour cooldown if shadowban suspected
- **Captcha**: 1-hour cooldown if captcha required

### Error Codes
- `ratelimit`: Too many requests, includes retry_after seconds
- `shadowban`: Account may be shadowbanned
- `captcha`: Captcha challenge required
- `rules`: Content violates subreddit rules
- `validation`: Invalid request format or parameters
- `internal`: Server error

## Dry Run Mode

All Reddit endpoints support dry-run mode:
- **Forced**: When Reddit credentials missing or `dry=true` parameter
- **Behavior**: Validates all inputs and rate limits, returns mock responses
- **Mock IDs**: Uses format like `t3_mock_123` for post IDs

## Reddit Extended API Documentation

### POST /api/v1/reddit/scrape
**Description**: Scrape posts from a subreddit for content analysis and discovery
**Auth**: Required (Bearer token)
**Request**:
```json
{
  "tenant_id": "owner",
  "subreddit": "programming",
  "sort": "hot",
  "time_filter": "day",
  "limit": 25,
  "dry": true
}
```

**Request Fields**:
- `tenant_id`: Tenant identifier
- `subreddit`: Target subreddit name (without r/ prefix)
- `sort`: Sort method - "hot", "new", "top", "rising"
- `time_filter`: Time filter for top posts - "hour", "day", "week", "month", "year", "all"
- `limit`: Number of posts to fetch (1-100, default: 25)
- `dry`: Force dry-run mode (default: false)

**Response**:
```json
{
  "ok": true,
  "mode": "mock",
  "job_id": 1,
  "status": "completed",
  "items_found": 5,
  "subreddit": "programming",
  "posts": [
    {
      "id": "abc123",
      "fullname": "t3_abc123",
      "title": "Interesting Programming Article",
      "author": "programmer123",
      "subreddit": "programming",
      "permalink": "/r/programming/comments/abc123/",
      "url": "https://reddit.com/r/programming/comments/abc123/",
      "created_utc": 1640995200.0,
      "score": 150,
      "num_comments": 25,
      "upvote_ratio": 0.92,
      "over_18": false,
      "spoiler": false,
      "selftext": "Article content...",
      "post_hint": "link"
    }
  ]
}
```

### POST /api/v1/reddit/queue
**Description**: Queue a post for future submission without immediate posting
**Auth**: Required (Bearer token)
**Request**:
```json
{
  "tenant_id": "owner",
  "account_id": 123,
  "subreddit": "test",
  "kind": "text",
  "title": "Queued Post Title",
  "body": "Post content to be posted later",
  "url": "https://example.com",
  "image_url": "https://example.com/image.jpg",
  "flair_id": "optional_flair_id",
  "nsfw": false,
  "spoiler": false,
  "schedule": "2024-12-25T12:00:00Z"
}
```

**Request Fields**:
- `tenant_id`: Tenant identifier
- `account_id`: Reddit account ID
- `subreddit`: Target subreddit name
- `kind`: Post type - "text", "link", "image"
- `title`: Post title
- `body`: Post content (for text posts)
- `url`: URL (for link posts)
- `image_url`: Image URL (for image posts)
- `flair_id`: Optional flair ID
- `nsfw`: Mark as NSFW
- `spoiler`: Mark as spoiler
- `schedule`: ISO datetime for when to post

**Response**:
```json
{
  "ok": true,
  "mode": "live",
  "status": "queued",
  "queue_id": 456,
  "scheduled_for": "2024-12-25T12:00:00Z",
  "subreddit": "test"
}
```

### GET /api/v1/reddit/posts/{tenant_id}
**Description**: Retrieve Reddit posts for a tenant with filtering
**Auth**: Required (Bearer token)
**Query Parameters**:
- `limit`: Number of posts (1-500, default: 50)
- `offset`: Skip posts (default: 0)
- `subreddit`: Filter by subreddit
- `status`: Filter by status (posted, failed, pending)

**Example**:
```bash
GET /api/v1/reddit/posts/owner?limit=10&subreddit=programming&status=posted
```

**Response**:
```json
{
  "ok": true,
  "mode": "live",
  "posts": [
    {
      "id": 123,
      "subreddit": "programming",
      "kind": "text",
      "title": "My Programming Post",
      "body": "Post content...",
      "url": null,
      "reddit_id": "abc123",
      "permalink": "/r/programming/comments/abc123/",
      "status": "posted",
      "score": 42,
      "num_comments": 5,
      "submitted_at": "2024-01-01T12:00:00Z",
      "created_at": "2024-01-01T11:30:00Z"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 10
}
```

### GET /api/v1/reddit/queue/{tenant_id}
**Description**: Retrieve queued Reddit posts for a tenant
**Auth**: Required (Bearer token)
**Query Parameters**:
- `limit`: Number of items (1-500, default: 50)
- `offset`: Skip items (default: 0)
- `status`: Filter by status (queued, processing, posted, failed, cancelled)

**Example**:
```bash
GET /api/v1/reddit/queue/owner?status=queued
```

**Response**:
```json
{
  "ok": true,
  "mode": "live",
  "queue_items": [
    {
      "id": 456,
      "subreddit": "test",
      "kind": "text",
      "title": "Queued Post",
      "body": "Content to be posted",
      "url": null,
      "schedule": "2024-12-25T12:00:00Z",
      "status": "queued",
      "attempts": 0,
      "post_id": null,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 1,
  "offset": 0,
  "limit": 50
}
```

### DELETE /api/v1/reddit/queue/{queue_id}
**Description**: Cancel a queued Reddit post before posting
**Auth**: Required (Bearer token)

**Example**:
```bash
DELETE /api/v1/reddit/queue/456
```

**Response**:
```json
{
  "ok": true,
  "mode": "live",
  "status": "cancelled",
  "queue_id": 456
}
```

## Reddit Configuration

For live Reddit functionality, configure these environment variables:

```bash
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT="YourApp/1.0 by YourUsername"
REDDIT_TIMEOUT_S=30
REDDIT_MAX_RETRIES=3
REDDIT_RATE_BURST=30
REDDIT_RATE_WINDOW_S=60
```

Without credentials, all Reddit operations use mock provider automatically.

## Reddit Database Models

### RedditPost
Tracks submitted Reddit posts with full metadata including Reddit IDs, permalinks, scores, and status.

### RedditQueueItem  
Manages scheduled Reddit posts with timing, retry logic, and linking to posted items.

### RedditScrapeJob
Records subreddit scraping operations with results, status tracking, and JSON storage.

### RedditRateWindow
Handles rate limiting per account and endpoint with burst control and reset timing.