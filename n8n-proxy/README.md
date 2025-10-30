# n8n-proxy

Tiny proxy that lets n8n trigger actions without exposing your n8n API token inside workflows.

## Env (Replit → Secrets)
- `AUTH_BEARER_TOKEN`  e.g. `my_proxy_key_123`
- `N8N_API_URL`        e.g. `https://your-subdomain.app.n8n.cloud`
- `N8N_API_TOKEN`      your n8n API key
- `N8N_PROJECT_ID`     optional
- `PORT`               optional (defaults 3000)

## Run
`npm run dev`

## Routes
- `GET  /api/v1/health`
- `POST /api/v1/n8n/create`
- `POST /api/v1/n8n/activate`
- `GET  /api/v1/n8n/workflows/:id`

## Example curl
AUTH="Authorization: Bearer my_proxy_key_123"

# health
curl -s https://<your-repl>.replit.app/api/v1/health

# create
curl -s -X POST https://<your-repl>.replit.app/api/v1/n8n/create \
 -H "$AUTH" -H "content-type: application/json" \
 -d '{"name":"Generated Workflow","settings":{"timezone":"UTC"},"nodes":[],"connections":{}}'

# activate
curl -s -X POST https://<your-repl>.replit.app/api/v1/n8n/activate \
 -H "$AUTH" -H "content-type: application/json" \
 -d '{"workflow_id":"<id-from-create>"}'

# get
curl -s -H "$AUTH" https://<your-repl>.replit.app/api/v1/n8n/workflows/<id>