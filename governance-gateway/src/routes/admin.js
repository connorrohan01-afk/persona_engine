import { Router } from 'express';
import { parse, StrikeSchema } from '../lib/validators.js';
import { recordStrike, stats, clearBackoff } from '../lib/store.js';

const r = Router();

// POST /admin/strike  — apply a strike (escalates backoff)
r.post('/strike', (req, res) => {
  const v = parse(StrikeSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const backoffRec = recordStrike(v.data);
  res.json({ ok: true, data: { strike: v.data, backoff: backoffRec } });
});

// DELETE /admin/backoff?personaId=&action=  — clear backoff for persona+action
r.delete('/backoff', (req, res) => {
  const { personaId, action } = req.query;
  if (!personaId || !action) {
    return res.status(400).json({ ok: false, error: { message: 'missing_persona_or_action' } });
  }
  clearBackoff(personaId, action);
  res.json({ ok: true, data: { personaId, action, cleared: true } });
});

// GET /admin/stats  — system stats
r.get('/stats', (req, res) => {
  res.json({ ok: true, data: stats() });
});

export default r;