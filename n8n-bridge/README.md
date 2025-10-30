# n8n-bridge
Proxy endpoints to call your n8n Cloud API.

## Env
- BUILDER_TOKEN (default: builder_token_123)
- N8N_HOST (e.g. https://ai-persona-engine.app.n8n.cloud)
- N8N_API_TOKEN (from n8n → Settings → Personal access tokens)
- PORT (optional, default 3000)

## Quick test
curl -s https://<your-repl>.replit.app/api/v1/health

# Create
curl -s -X POST https://<your-repl>.replit.app/api/v1/n8n/create \
  -H "Authorization: Bearer builder_token_123" -H "content-type: application/json" \
  -d '{"name":"Generated Workflow","settings":{"timezone":"UTC"},"nodes":[],"connections":{}}'

# Activate
curl -s -X POST "https://<your-repl>.replit.app/api/v1/n8n/activate" \
  -H "Authorization: Bearer builder_token_123" -H "content-type: application/json" \
  -d '{"id":"<WORKFLOW_ID>"}'

# Get
curl -s "https://<your-repl>.replit.app/api/v1/n8n/get?id=<WORKFLOW_ID>" \
  -H "Authorization: Bearer builder_token_123"