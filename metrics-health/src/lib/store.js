import { nanoid } from 'nanoid';

const services = new Map(); // serviceId -> record
const events = []; // recent status change events

export function upsertService(data) {
  const now = new Date().toISOString();
  const prev = services.get(data.serviceId);
  const rec = {
    id: data.serviceId,
    displayName: data.displayName || data.serviceId,
    group: data.group || 'default',
    url: data.url || null,
    ttlMs: data.ttlMs ?? 120000,
    status: prev?.status || 'stale', // unknown until first heartbeat or manual mark
    lastBeatAt: prev?.lastBeatAt || null,
    meta: { ...(prev?.meta || {}), ...(data.meta || {}) },
    createdAt: prev?.createdAt || now,
    updatedAt: now
  };
  services.set(data.serviceId, rec);
  return rec;
}

export function recordHeartbeat(serviceId, atIso) {
  const rec = services.get(serviceId);
  const nowIso = atIso || new Date().toISOString();
  if (!rec) return null;
  const prevStatus = rec.status;
  rec.lastBeatAt = nowIso;
  rec.updatedAt = nowIso;
  // status might flip to up here
  const nextStatus = 'up';
  if (prevStatus !== nextStatus) pushEvent(serviceId, prevStatus, nextStatus);
  rec.status = nextStatus;
  services.set(serviceId, rec);
  return rec;
}

export function evaluateStaleness() {
  const now = Date.now();
  for (const rec of services.values()) {
    if (!rec.lastBeatAt) continue;
    const age = now - new Date(rec.lastBeatAt).getTime();
    const prev = rec.status;
    const next = age > rec.ttlMs ? 'stale' : 'up';
    if (prev !== next) {
      pushEvent(rec.id, prev, next);
      rec.status = next;
      rec.updatedAt = new Date().toISOString();
      services.set(rec.id, rec);
    }
  }
}

export function manualStatus(serviceId, next) {
  const rec = services.get(serviceId);
  if (!rec) return null;
  const prev = rec.status;
  if (prev !== next) pushEvent(serviceId, prev, next);
  rec.status = next;
  rec.updatedAt = new Date().toISOString();
  services.set(serviceId, rec);
  return rec;
}

export function listServices(filter = {}) {
  evaluateStaleness();
  let arr = Array.from(services.values());
  if (filter.group) arr = arr.filter(s => s.group === filter.group);
  if (filter.status) arr = arr.filter(s => s.status === filter.status);
  return arr;
}

export function getService(id) {
  evaluateStaleness();
  return services.get(id) || null;
}

export function deleteService(id) {
  return services.delete(id);
}

export function pushEvent(serviceId, prev, next) {
  events.unshift({ id: nanoid(), serviceId, prev, next, at: new Date().toISOString() });
  if (events.length > 500) events.pop();
  return events[0];
}

export function listEvents(limit = 50) {
  return events.slice(0, limit);
}