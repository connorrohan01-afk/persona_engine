import { nanoid } from 'nanoid';

const templates = new Map();
const personas = new Map();
const plans = new Map();
const history = new Map(); // id -> { id, planId?, output, createdAt }

export const db = { templates, personas, plans, history };

export function createOne(map, obj) {
  const id = nanoid();
  const now = new Date().toISOString();
  const rec = { id, createdAt: now, updatedAt: now, ...obj };
  map.set(id, rec);
  return rec;
}
export function patchOne(map, id, patch) {
  const cur = map.get(id);
  if (!cur) return null;
  const rec = { ...cur, ...patch, updatedAt: new Date().toISOString() };
  map.set(id, rec);
  return rec;
}
export function getOne(map, id) { return map.get(id) || null; }
export function deleteOne(map, id) { return map.delete(id); }
export function listMap(map, { offset=0, limit=50 }={}) {
  const all = Array.from(map.values());
  return { total: all.length, items: all.slice(offset, offset+limit) };
}

export function appendHistory(payload) {
  return createOne(history, payload);
}