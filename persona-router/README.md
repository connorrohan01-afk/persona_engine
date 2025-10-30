# persona-router

Tiny adapter that forwards "tool/action/payload" calls to your internal services. No external automation.

## Env
- AUTH_BEARER_TOKEN (default `router_token_123`)
- PORT (default 3000)

## Run
npm run dev

## Health (no auth)
curl -s https://<your-repl>.replit.app/api/v1/health | jq .

## Register services (auth)
curl -s -X POST https://<your-repl>.replit.app/api/v1/registry \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"serviceId":"persona-core","baseUrl":"https://persona-core-<user>.replit.app","token":"core_token"}'

curl -s -X POST https://<your-repl>.replit.app/api/v1/registry \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"serviceId":"content-scheduler","baseUrl":"https://content-scheduler-<user>.replit.app","token":"sched_token"}'

curl -s -X POST https://<your-repl>.replit.app/api/v1/registry \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"serviceId":"vaults","baseUrl":"https://vaults-<user>.replit.app","token":"vaults_token"}'

curl -s -X POST https://<your-repl>.replit.app/api/v1/registry \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"serviceId":"account-intake","baseUrl":"https://account-intake-<user>.replit.app","token":"intake_token"}'

## Route calls (auth)
### Build a persona
curl -s -X POST https://<your-repl>.replit.app/api/v1/router \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"tool":"persona","action":"build","payload":{"name":"mybot","bio":"helpful","topics":["news","pics"]}}'

### Schedule content
curl -s -X POST https://<your-repl>.replit.app/api/v1/router \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"tool":"scheduler","action":"schedule","payload":{"accountId":"acc_123","cron":"*/30 * * * *","plan":[{"type":"text","text":"hi"}]}}'

### Put/get vault blob
curl -s -X POST https://<your-repl>.replit.app/api/v1/router \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"tool":"vault","action":"put","payload":{"label":"cookie_xyz","blob":"cookie=abc;token=xyz"}}'

curl -s -X POST https://<your-repl>.replit.app/api/v1/router \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"tool":"vault","action":"get","payload":{"label":"cookie_xyz"}}'

### Intake link/update
curl -s -X POST https://<your-repl>.replit.app/api/v1/router \
  -H "Authorization: Bearer router_token_123" -H "Content-Type: application/json" \
  -d '{"tool":"intake","action":"create","payload":{"platform":"reddit","username":"u_demo","notes":"manual","session":{"cookies":"c=1"},"meta":{"owner":"me"}}}'