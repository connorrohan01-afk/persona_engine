# n8n-glue-templates

Ready-to-import JSON snippets and templates to wire n8n with your Replit services. These contain ONLY first-party HTTP calls to your services - no third-party automation.

## Usage

These JSON node exports can be pasted into n8n:
1. In n8n, click "Add node" 
2. Select "JSON" 
3. Paste the template content
4. Replace `${VAR}` placeholders or set them as environment variables in n8n

## Required Environment Variables in n8n

Set these in your n8n environment/credentials:

```
N8N_HOST=https://your-n8n-host
N8N_API_TOKEN=your-api-token
ROUTER_URL=https://your-telegram-router.replit.app
INTAKE_URL=https://your-intake.replit.app
INTAKE_TOKEN=intake_token_123
POSTER_URL=https://your-poster.replit.app
POSTER_TOKEN=poster_token_123
SCHEDULER_URL=https://your-scheduler.replit.app
SCHEDULER_TOKEN=scheduler_token_123
VAULTS_URL=https://your-vaults.replit.app
VAULTS_TOKEN=vaults_token_123
```

## Step-by-Step Examples

### 1. Ping Status Check
Import `telegram_build_status_get.json`, set your N8N_HOST and N8N_API_TOKEN, then Execute. Should return a workflows array from your n8n instance.

### 2. Create Intake Account
Import `account_intake_examples.json`, set your INTAKE_URL and INTAKE_TOKEN Bearer token, then run the nodes in order:
1. Create Proxy → returns proxy ID
2. Create Vault → returns vault ID  
3. Create Account → uses the IDs from previous steps

### 3. Queue a Post
Import `post_queue_example.json`, set your POSTER_URL and POSTER_TOKEN, update the accountId/subreddit/text, then Execute. Should return 200 with a queue ID.

### 4. Schedule Recurring Posts
Import `scheduler_job_example.json`, set your SCHEDULER_URL and SCHEDULER_TOKEN, configure "every 30 minutes" timing, then Execute. Returns a job ID for the scheduled task.

### 5. Vault Storage
Import `vault_put_get_example.json`, set your VAULTS_URL and VAULTS_TOKEN. The workflow will:
1. PUT a blob to vault storage
2. GET the same blob back using the returned ID
3. Verify content matches

## Template Files

- `telegram_build_status_get.json` - Test n8n API connectivity
- `replit_build_webhook.json` - Mock Telegram webhook calls  
- `tool_router_webhook.json` - Webhook receiver with JSON response
- `account_intake_examples.json` - Account creation workflow (proxy → vault → account)
- `post_queue_example.json` - Simple post queueing
- `scheduler_job_example.json` - Scheduled post creation
- `vault_put_get_example.json` - Vault storage operations

## Security Notes

- All templates use Bearer token authentication for your internal services
- No templates include third-party API calls or automation
- Environment variables keep sensitive tokens out of workflow definitions
- All HTTP calls target your own Replit-hosted microservices only