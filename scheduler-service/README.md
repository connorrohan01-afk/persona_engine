# scheduler-service

Queues and simulates job execution using BullMQ. No external posting.

## Env
- AUTH_BEARER_TOKEN (default `sched_token_123`)
- REDIS_URL (default `redis://localhost:6379`)
- PORT=3000

## Run
npm run dev

## Health
curl -s https://<your-repl>.replit.app/api/v1/health

## Enqueue job
curl -s -X POST https://<your-repl>.replit.app/api/v1/jobs \
  -H "Authorization: Bearer sched_token_123" -H "Content-Type: application/json" \
  -d '{"type":"post","payload":{"msg":"hi"},"delayMs":1000}'

## Check job
curl -s https://<your-repl>.replit.app/api/v1/jobs/<id> \
  -H "Authorization: Bearer sched_token_123"

## List jobs
curl -s https://<your-repl>.replit.app/api/v1/jobs \
  -H "Authorization: Bearer sched_token_123"

## Delete job
curl -s -X DELETE https://<your-repl>.replit.app/api/v1/jobs/<id> \
  -H "Authorization: Bearer sched_token_123"