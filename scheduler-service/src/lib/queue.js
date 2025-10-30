import { Queue, Worker, QueueEvents } from 'bullmq';
import IORedis from 'ioredis';
import { nanoid } from 'nanoid';

const url = process.env.REDIS_URL || 'redis://localhost:6379';
const conn = new IORedis(url, {
  maxRetriesPerRequest: null,
  enableReadyCheck: false,
  lazyConnect: true
});

export const q = new Queue('jobs', { connection: conn });
export const events = new QueueEvents('jobs', { connection: conn });

export function addJob({ type, payload, delayMs }) {
  return q.add(type, payload || {}, { jobId: nanoid(), delay: delayMs || 0 });
}

export function worker() {
  return new Worker('jobs', async (job) => {
    console.log('[JOB start]', job.id, job.name);
    await new Promise(r => setTimeout(r, job.opts.delay || 500));
    return { simulated: true, payload: job.data };
  }, { connection: conn });
}

export function listenEvents() {
  events.on('completed', (e) => console.log('[JOB completed]', e.jobId));
  events.on('failed', (e) => console.log('[JOB failed]', e.jobId, e.failedReason));
  events.on('active', (e) => console.log('[JOB active]', e.jobId));
}

worker();
listenEvents();