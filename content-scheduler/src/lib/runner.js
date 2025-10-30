import cron from 'node-cron';
import axios from 'axios';
import { pushLog, listSchedules, getSchedule } from './store.js';

const tasks = new Map(); // scheduleId -> cancel function

function jitter(ms) {
  const delta = Math.floor(Math.random() * Math.min(500, Math.max(50, ms * 0.1)));
  return ms + delta;
}

async function fireOnce(schedule) {
  const start = Date.now();
  const headers = { 'Content-Type': 'application/json' };
  if (schedule.secret) headers['X-Webhook-Secret'] = schedule.secret;

  let attempt = 0;
  let lastErr = null;

  while (attempt < 3) {
    attempt++;
    try {
      const res = await axios.post(schedule.webhookUrl, {
        personaId: schedule.personaId,
        channel: schedule.channel,
        payload: schedule.payload,
        scheduleId: schedule.id,
        firedAt: new Date().toISOString(),
        attempt
      }, { headers, timeout: 10_000 });

      pushLog(schedule.id, {
        status: 'ok',
        code: res.status,
        ms: Date.now() - start,
        attempt,
        note: 'delivered'
      });
      return;
    } catch (e) {
      lastErr = e;
      pushLog(schedule.id, {
        status: 'fail',
        code: e.response?.status || 0,
        ms: Date.now() - start,
        attempt,
        note: e.message?.slice(0, 120) || 'error'
      });
      // backoff with jitter
      const backoff = jitter(300 * attempt);
      await new Promise(r => setTimeout(r, backoff));
    }
  }
  // After retries
  const code = lastErr?.response?.status || 0;
  pushLog(schedule.id, { status: 'drop', code, ms: Date.now() - start, attempt: 3, note: 'exhausted retries' });
}

function startCron(schedule) {
  // Stop any existing runner
  stopCron(schedule.id);

  if (!schedule.enabled) return;

  if (schedule.cadence.kind === 'cron') {
    const task = cron.schedule(schedule.cadence.expr, () => fireOnce(schedule), { timezone: 'UTC' });
    tasks.set(schedule.id, () => task.stop());
    return;
  }

  if (schedule.cadence.kind === 'every') {
    const everyMs = schedule.cadence.unit === 'minutes'
      ? schedule.cadence.value * 60_000
      : schedule.cadence.value * 3_600_000;

    const startAt = schedule.cadence.startAt ? new Date(schedule.cadence.startAt).getTime() : Date.now();
    const now = Date.now();
    const initialDelay = Math.max(0, startAt - now);

    let timer = setTimeout(function kick() {
      fireOnce(getSchedule(schedule.id) || schedule);
      timer = setInterval(() => fireOnce(getSchedule(schedule.id) || schedule), everyMs);
      tasks.set(schedule.id, () => { clearInterval(timer); });
    }, initialDelay);

    tasks.set(schedule.id, () => { clearTimeout(timer); clearInterval(timer); });
    return;
  }
}

export function refreshRunners() {
  // restart all
  for (const cancel of tasks.values()) try { cancel(); } catch {}
  tasks.clear();
  const all = listSchedules();
  all.forEach(startCron);
}

export function startRunnerFor(schedule) {
  startCron(schedule);
}

export function stopCron(id) {
  const cancel = tasks.get(id);
  if (cancel) { try { cancel(); } catch {} tasks.delete(id); }
}