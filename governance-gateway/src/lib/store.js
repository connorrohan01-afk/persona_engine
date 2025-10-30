import { nanoid } from 'nanoid';
import { now, sweep } from './window.js';

// In-memory stores
const globalLimits = new Map(); // action -> { max, windowMs, cost, dedupeTtlMs }
const personaLimits = new Map(); // personaId -> Map(action -> limit)
const usage = new Map(); // personaId -> Map(action -> timestamps[])
const tokens = new Map(); // personaId -> Map(action -> remainingTokens:number) [optional if using fixed cost]
const dedupe = new Map(); // dedupeKey -> expiresAt
const backoff = new Map(); // key(personaId|action) -> { level, until }
const strikes = []; // [{ id, personaId, action, reason, at, weight }]

const MAX_BACKOFF_MS = 60 * 60 * 1000; // 1h cap
const BASE_BACKOFF_MS = 60 * 1000;     // 1m base

function keyPA(personaId, action) { return `${personaId}::${action}`; }

export function setLimit(limit) {
  const { action, max, windowMs, cost, dedupeTtlMs, personaId } = limit;
  const clean = { action, max, windowMs, cost, dedupeTtlMs };
  if (personaId) {
    if (!personaLimits.has(personaId)) personaLimits.set(personaId, new Map());
    personaLimits.get(personaId).set(action, clean);
  } else {
    globalLimits.set(action, clean);
  }
  return clean;
}

export function getEffectiveLimit(personaId, action) {
  const per = personaLimits.get(personaId)?.get(action);
  return per || globalLimits.get(action) || null;
}

export function recordStrike({ personaId, action, reason, weight }) {
  const id = nanoid();
  strikes.push({ id, personaId, action, reason, weight, at: new Date().toISOString() });

  const k = keyPA(personaId, action);
  const bo = backoff.get(k) || { level: 0, until: 0 };
  const newLevel = Math.min(bo.level + weight, 20);
  const ms = Math.min(BASE_BACKOFF_MS * (2 ** (newLevel - 1)), MAX_BACKOFF_MS);
  const until = Math.max(Date.now() + ms, bo.until);
  const rec = { level: newLevel, until };
  backoff.set(k, rec);
  return rec;
}

export function clearBackoff(personaId, action) {
  backoff.delete(keyPA(personaId, action));
}

export function getBackoff(personaId, action) {
  return backoff.get(keyPA(personaId, action)) || { level: 0, until: 0 };
}

export function inDedupeWindow(dedupeKey) {
  if (!dedupeKey) return false;
  const exp = dedupe.get(dedupeKey);
  if (!exp) return false;
  if (Date.now() > exp) { dedupe.delete(dedupeKey); return false; }
  return true;
}

export function setDedupe(dedupeKey, ttlMs) {
  if (!dedupeKey || !ttlMs) return;
  dedupe.set(dedupeKey, Date.now() + ttlMs);
}

export function getUsage(personaId, action) {
  if (!usage.has(personaId)) usage.set(personaId, new Map());
  const m = usage.get(personaId);
  if (!m.has(action)) m.set(action, []);
  return m.get(action);
}

export function sweepUsage(personaId, action, windowMs) {
  const arr = getUsage(personaId, action);
  sweep(arr, windowMs);
  return arr;
}

export function addUsage(personaId, action, count = 1) {
  const arr = getUsage(personaId, action);
  for (let i = 0; i < count; i++) arr.push(Date.now());
  return arr.length;
}

export function stats() {
  return {
    globalLimits: Object.fromEntries(globalLimits.entries()),
    personaLimits: Object.fromEntries([...personaLimits.entries()].map(([pid, m]) => [pid, Object.fromEntries(m.entries())])),
    dedupeSize: dedupe.size,
    backoffSize: backoff.size,
    strikesCount: strikes.length
  };
}