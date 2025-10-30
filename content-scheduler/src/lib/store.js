import { nanoid } from 'nanoid';

const schedules = new Map(); // id -> schedule
const logs = new Map();      // scheduleId -> [{id, ts, status, code, ms, attempt, note}]

export function createSchedule(data) {
  const id = nanoid();
  const now = new Date().toISOString();
  const rec = { id, createdAt: now, updatedAt: now, ...data };
  schedules.set(id, rec);
  return rec;
}

export function patchSchedule(id, patch) {
  const cur = schedules.get(id);
  if (!cur) return null;
  const updated = { ...cur, ...patch, updatedAt: new Date().toISOString() };
  schedules.set(id, updated);
  return updated;
}

export function getSchedule(id) { return schedules.get(id) || null; }

export function listSchedules(filter = {}) {
  let arr = Array.from(schedules.values());
  if (filter.personaId) arr = arr.filter(s => s.personaId === filter.personaId);
  if (filter.channel) arr = arr.filter(s => s.channel === filter.channel);
  if (filter.enabled !== undefined) {
    const want = String(filter.enabled).toLowerCase() === 'true';
    arr = arr.filter(s => s.enabled === want);
  }
  return arr;
}

export function deleteSchedule(id) { return schedules.delete(id); }

export function pushLog(scheduleId, entry) {
  const l = logs.get(scheduleId) || [];
  l.unshift({ id: nanoid(), ts: new Date().toISOString(), ...entry });
  logs.set(scheduleId, l.slice(0, 200)); // cap per schedule
  return l[0];
}

export function getLogs(scheduleId, limit = 50) {
  const l = logs.get(scheduleId) || [];
  return l.slice(0, limit);
}