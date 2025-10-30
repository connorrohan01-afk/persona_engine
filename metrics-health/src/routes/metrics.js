import { Router } from 'express';
import { parse, QueryListSchema } from '../lib/validators.js';
import { listServices, getService, deleteService, listEvents } from '../lib/store.js';
import { requireBearer } from '../lib/auth.js';

const r = Router();

// Summary (public read)
r.get('/summary', (req, res) => {
  const all = listServices();
  const counts = all.reduce((acc, s) => {
    acc[s.status] = (acc[s.status] || 0) + 1;
    return acc;
  }, {});
  res.json({ ok: true, data: { totals: { all: all.length, ...counts }, services: all } });
});

// List with filters (public read)
r.get('/services', (req, res) => {
  const q = parse(QueryListSchema, req.query || {});
  if (!q.ok) return res.status(400).json({ ok: false, error: q.error });
  res.json({ ok: true, data: listServices(q.data) });
});

// Get one (public read)
r.get('/services/:id', (req, res) => {
  const s = getService(req.params.id);
  if (!s) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: s });
});

// Delete (auth)
r.delete('/services/:id', requireBearer, (req, res) => {
  const ok = deleteService(req.params.id);
  if (!ok) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: { id: req.params.id, deleted: true } });
});

// Recent events (public read)
r.get('/events', (req, res) => {
  const limit = Math.min(Number(req.query.limit || 50) || 50, 200);
  res.json({ ok: true, data: { items: listEvents(limit) } });
});

export default r;