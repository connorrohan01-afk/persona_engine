import { Router } from 'express';
import { parse, CounterSchema, GaugeSchema } from '../lib/validators.js';
import { incCounter, setGauge, getMetrics } from '../lib/store.js';

const r = Router();

r.get('/', (req, res) => {
  res.json({ ok: true, data: getMetrics() });
});

r.post('/counter', (req, res) => {
  const v = parse(CounterSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const out = incCounter(v.data.key, v.data.delta ?? 1);
  res.json({ ok: true, data: out });
});

r.post('/gauge', (req, res) => {
  const v = parse(GaugeSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const out = setGauge(v.data.key, v.data.value);
  res.json({ ok: true, data: out });
});

export default r;