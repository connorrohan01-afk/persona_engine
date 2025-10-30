# metrics-health

Central heartbeat, ping, and status-change notifier for your internal microservices. No external automation — pure observability.

## Env
- AUTH_BEARER_TOKEN (default: `metrics_token_123`)
- WEBHOOK_URL (optional; receives POST on status changes)
- PORT (default 3000)

## Run
npm run dev

## Health (no auth)
curl -s https://<your-repl>.replit.app/api/v1/health | jq .

## Register a service
curl -s -X POST https://<your-repl>.replit.app/api/v1/signals/register \
  -H "Authorization: Bearer metrics_token_123" -H "Content-Type: application/json" \
  -d '{"serviceId":"content-scheduler","displayName":"Content Scheduler","group":"core","url":"https://<sched>/api/v1/health","ttlMs":120000}'

## Send heartbeat
curl -s -X POST https://<your-repl>.replit.app/api/v1/signals/heartbeat \
  -H "Authorization: Bearer metrics_token_123" -H "Content-Type: application/json" \
  -d '{"serviceId":"content-scheduler"}'

## On-demand ping
curl -s -X POST https://<your-repl>.replit.app/api/v1/signals/ping \
  -H "Authorization: Bearer metrics_token_123" -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/","method":"HEAD","timeoutMs":5000}'

## Summary (public)
curl -s https://<your-repl>.replit.app/api/v1/metrics/summary | jq .

## Recent events (public)
curl -s https://<your-repl>.replit.app/api/v1/metrics/events | jq .