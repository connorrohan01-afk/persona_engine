import { Router } from 'express';
import { parse, ReportQuerySchema } from '../lib/validators.js';
import { aggregateWindow, personaSnapshot, listEvents, getMetrics } from '../lib/store.js';

const r = Router();

function windowMs(win) {
  return ({
    '1h': 3600e3,
    '6h': 21600e3,
    '24h': 86400e3,
    '7d': 604800e3,
    '30d': 2592000e3
  })[win] || 86400e3;
}

// GET /report?window=24h&personaId=xyz
r.get('/', (req, res) => {
  const v = parse(ReportQuerySchema, { window: req.query.window, personaId: req.query.personaId });
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });

  const agg = aggregateWindow(windowMs(v.data.window), v.data.personaId);
  const persona = v.data.personaId ? personaSnapshot(v.data.personaId) : null;
  const metrics = getMetrics();
  res.json({ ok: true, data: { window: v.data.window, totals: agg.totals, persona, metrics } });
});

// GET /report/events?since=ISO
r.get('/events', (req, res) => {
  const since = req.query.since;
  const evts = listEvents({ since });
  res.json({ ok: true, data: { count: evts.length, items: evts } });
});

export default r;