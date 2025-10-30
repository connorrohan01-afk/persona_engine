import { Router } from 'express';
import { parse, LimitSchema } from '../lib/validators.js';
import { setLimit, getEffectiveLimit, stats } from '../lib/store.js';

const r = Router();

// PUT /limits  — upsert a limit (global or persona-specific)
r.put('/', (req, res) => {
  const v = parse(LimitSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const saved = setLimit(v.data);
  res.json({ ok: true, data: saved });
});

// GET /limits/effective?personaId=&action=
r.get('/effective', (req, res) => {
  const { personaId = '', action = '' } = req.query;
  const eff = getEffectiveLimit(personaId, action);
  if (!eff) return res.status(404).json({ ok: false, error: { message: 'no_limit' } });
  res.json({ ok: true, data: eff });
});

// GET /limits/stats
r.get('/stats', (req, res) => {
  res.json({ ok: true, data: stats() });
});

export default r;