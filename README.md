# account-intake

Intake/linker for existing accounts. Stores basic profile, optional session artifacts (cookie/token), and links to proxy & vault records. No external automation or logins.

## Env
- AUTH_BEARER_TOKEN (default: `intake_token_123`)
- USE_MOCK_PROXY=true
- USE_MOCK_VAULT=true
- PORT=3000

## Run

npm run dev

## Health (no auth)

curl -s https://.replit.app/api/v1/health

## Auth header
`Authorization: Bearer intake_token_123` (or your secret)

## Quick flow
Create proxy:

curl -s -X POST https://.replit.app/api/v1/proxies 
-H "Authorization: Bearer intake_token_123" -H "Content-Type: application/json" 
-d '{"label":"pA","url":"http://user:pass@host:10000"}'

Create vault (store any blob/string):

curl -s -X POST https://.replit.app/api/v1/vaults 
-H "Authorization: Bearer intake_token_123" -H "Content-Type: application/json" 
-d '{"label":"sess-blob","blob":"cookie=abc; token=xyz"}'

Create account intake:

curl -s -X POST https://.replit.app/api/v1/accounts 
-H "Authorization: Bearer intake_token_123" -H "Content-Type: application/json" 
-d '{
"platform":"reddit",
"username":"u_demo",
"notes":"manual onboarded",
"proxyId":"",
"vaultId":"",
"session": { "cookies":"cookie=abc", "token":"xyz" },
"meta": { "owner":"me" }
}'

Patch account (link new vault/proxy or update status):

curl -s -X PATCH https://.replit.app/api/v1/accounts/ 
-H "Authorization: Bearer intake_token_123" -H "Content-Type: application/json" 
-d '{ "status":"warm", "notes":"warmed 24h" }'

List accounts:

curl -s -H "Authorization: Bearer intake_token_123" 
https://.replit.app/api/v1/accounts?limit=50

## n8n Integration

Create n8n workflow:

curl -s -X POST https://.replit.app/api/v1/n8n/create \
-H "Authorization: Bearer intake_token_123" -H "Content-Type: application/json" \
-d '{"name":"Test Workflow","payload":{"nodes":[],"connections":{}}}'

Activate n8n workflow:

curl -s -X POST https://.replit.app/api/v1/n8n/activate/<WORKFLOW_ID> \
-H "Authorization: Bearer intake_token_123"

Get n8n workflow:

curl -s -H "Authorization: Bearer intake_token_123" \
https://.replit.app/api/v1/n8n/get/<WORKFLOW_ID>