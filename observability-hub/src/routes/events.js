import { Router } from 'express';
import { parse, EventIngestSchema } from '../lib/validators.js';
import { addEvent } from '../lib/store.js';

const r = Router();

// POST /events -> ingest one or many events
r.post('/', (req, res) => {
  const body = Array.isArray(req.body) ? req.body : [req.body || {}];
  const accepted = [];
  const errors = [];

  for (const item of body) {
    const v = parse(EventIngestSchema, item);
    if (!v.ok) {
      errors.push(v.error);
      continue;
    }
    const saved = addEvent(v.data);
    accepted.push(saved);
  }
  if (accepted.length === 0) return res.status(400).json({ ok: false, error: { message: 'no_valid_events', errors } });
  res.json({ ok: true, data: { accepted, errors } });
});

export default r;