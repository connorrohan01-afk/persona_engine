import { nanoid } from 'nanoid';

const events = [];                 // [{ id, type, personaId, accountId, platform, meta, at }]
const counters = new Map();        // key -> number
const gauges = new Map();          // key -> number
const personas = new Map();        // personaId -> { postsOk, postsFail, clicks, warms, lastAt, accounts: Set }

function nowISO() { return new Date().toISOString(); }

export function addEvent(evt) {
  const id = nanoid();
  const at = evt.at || nowISO();
  const rec = { id, ...evt, at };
  events.push(rec);

  // roll up persona stats
  if (evt.personaId) {
    if (!personas.has(evt.personaId)) {
      personas.set(evt.personaId, { postsOk:0, postsFail:0, clicks:0, warms:0, lastAt:null, accounts:new Set() });
    }
    const p = personas.get(evt.personaId);
    if (evt.type === 'post_success') p.postsOk++;
    if (evt.type === 'post_fail')    p.postsFail++;
    if (evt.type === 'click')        p.clicks++;
    if (evt.type === 'warm_tick')    p.warms++;
    if (evt.accountId) p.accounts.add(evt.accountId);
    p.lastAt = at;
  }

  return rec;
}

export function incCounter(key, delta = 1) {
  counters.set(key, (counters.get(key) || 0) + delta);
  return { key, value: counters.get(key) };
}

export function setGauge(key, value) {
  gauges.set(key, value);
  return { key, value };
}

export function getMetrics() {
  const countersObj = Object.fromEntries(counters.entries());
  const gaugesObj = Object.fromEntries(gauges.entries());
  return { counters: countersObj, gauges: gaugesObj };
}

export function listEvents({ since } = {}) {
  if (!since) return events.slice(-500); // last 500
  const sinceTs = new Date(since).getTime();
  return events.filter(e => new Date(e.at).getTime() >= sinceTs).slice(-2000);
}

export function personaSnapshot(personaId) {
  if (!personaId) return null;
  const p = personas.get(personaId);
  if (!p) return null;
  return {
    postsOk: p.postsOk,
    postsFail: p.postsFail,
    clicks: p.clicks,
    warms: p.warms,
    accounts: p.accounts.size,
    lastAt: p.lastAt
  };
}

export function aggregateWindow(msWindow, personaId) {
  const cutoff = Date.now() - msWindow;
  const evts = events.filter(e => new Date(e.at).getTime() >= cutoff && (!personaId || e.personaId === personaId));
  const totals = { post_success:0, post_fail:0, click:0, warm_tick:0 };
  for (const e of evts) {
    if (totals[e.type] !== undefined) totals[e.type]++;
  }
  return { totals, count: evts.length, since: new Date(cutoff).toISOString() };
}