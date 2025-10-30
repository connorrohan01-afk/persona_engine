# cluster-orchestrator

Coordinates clusters of personas/accounts/jobs across internal services. Does not automate external sites.

## Env
- AUTH_BEARER_TOKEN (default `orchestrator_token_123`)
- PORT (default 3000)

## Run
npm run dev

## Example
Create cluster:
curl -s -X POST https://<your-repl>.replit.app/api/v1/clusters \
  -H "Authorization: Bearer orchestrator_token_123" -H "Content-Type: application/json" \
  -d '{"label":"clusterA","personaIds":["p1"],"accountIds":["a1"],"meta":{"topic":"test"}}'

List clusters:
curl -s -H "Authorization: Bearer orchestrator_token_123" https://<your-repl>.replit.app/api/v1/clusters

Activate:
curl -s -X POST https://<your-repl>.replit.app/api/v1/clusters/<id>/activate \
  -H "Authorization: Bearer orchestrator_token_123"