# telegram-command-router

Telegram bot webhook handler that routes commands to internal microservices. This service DOES NOT automate third-party sites directly; it only validates/routes commands and calls internal HTTP services with Bearer token authentication.

## Environment Variables

### Required
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token from BotFather

### Optional Service Configuration  
- `TELEGRAM_BOT_USERNAME` - Bot username (improves command parsing)
- `AUTH_BEARER_TOKEN` - Token for internal service calls (default: `tg_router_token_123`)
- `CONTENT_URL` - Content generation service base URL
- `INTAKE_URL` - Account intake service base URL  
- `POSTER_URL` - Posting service base URL
- `SCHEDULER_URL` - Job scheduler service base URL
- `VAULTS_URL` - Vault storage service base URL

### Rate Limiting
- `RATE_LIMIT_WINDOW_MS=30000` - Rate limit window in milliseconds
- `RATE_LIMIT_MAX=20` - Max requests per window per chat
- `PORT=3000` - Server port

## Setup Telegram Webhook

Set your bot's webhook to point to this service:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-router.replit.app/api/v1/telegram/webhook"}'
```

## Supported Commands

### Basic Commands
- `/ping` → responds "pong" 
- `/status` → health check of downstream services
- `/help` → list all available commands

### Account Management  
- `/link <accountId>` → associate chat with account ID

### Content Operations
- `/post <accountId> <subreddit> :: <text>` → queue a post
- `/schedule <accountId> every <N> <unit> :: <subreddit> :: <text>` → schedule recurring posts
- `/media <accountId> :: <prompt or url>` → generate/post media content

## Example Usage

### Link Account
```
/link acc_reddit_demo
```

### Queue Post
```  
/post acc_reddit_demo r/pics :: Check out this amazing sunset!
```

### Schedule Posts
```
/schedule acc_reddit_demo every 30 minutes :: r/technology :: Daily tech update
```

### Media Generation
```
/media acc_reddit_demo :: A beautiful landscape with mountains and lakes
```

## Health Check

```bash
curl -s https://your-router.replit.app/api/v1/health
```

## Internal Service Calls

All downstream calls include `Authorization: Bearer ${AUTH_BEARER_TOKEN}` header.

Example calls made by the router:
- POST `${POSTER_URL}/api/v1/queue` - Queue posts
- POST `${SCHEDULER_URL}/api/v1/jobs` - Schedule jobs  
- POST `${CONTENT_URL}/api/v1/images` - Generate images
- GET `${SERVICE_URL}/api/v1/health` - Health checks

## Command Logging

Every command execution is logged as JSON:
```json
{
  "ts": "2025-09-19T14:30:45.123Z",
  "chatId": 12345,
  "user": "john_doe", 
  "cmd": "post",
  "args": ["acc_123", "r/pics", "hello world"],
  "ok": true
}
```

## Security Features

- Per-chat rate limiting using chat ID
- Bearer token authentication for all internal service calls
- Input validation and command parsing
- No direct third-party site automation
- Webhook signature validation support (via node-telegram-bot-api utilities)