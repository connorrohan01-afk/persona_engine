import { Router } from 'express';
import { z } from 'zod';
import { n8nGet, n8nPost } from '../lib/n8n.js';

const r = Router();

// Schemas
const CreateSchema = z.object({
  name: z.string().min(1).default('Generated Workflow'),
  settings: z.object({ timezone: z.string().default('UTC') }).default({ timezone: 'UTC' }),
  nodes: z.array(z.any()).default([]),
  connections: z.record(z.any()).default({})
});

const ActivateSchema = z.object({
  workflow_id: z.string().min(1)
});

// POST /api/v1/n8n/create
r.post('/create', async (req, res) => {
  try {
    const parsed = CreateSchema.safeParse(req.body || {});
    if (!parsed.success) return res.status(400).json({ ok: false, error: parsed.error.flatten() });
    const created = await n8nPost('/api/v1/workflows', parsed.data);
    res.json({ ok: true, data: created });
  } catch (e) {
    res.status(502).json({ ok: false, error: { message: String(e.message || e) } });
  }
});

// POST /api/v1/n8n/activate
r.post('/activate', async (req, res) => {
  try {
    const parsed = ActivateSchema.safeParse(req.body || {});
    if (!parsed.success) return res.status(400).json({ ok: false, error: parsed.error.flatten() });
    const id = parsed.data.workflow_id;
    const out = await n8nPost(`/api/v1/workflows/${id}/activate`, {});
    res.json({ ok: true, data: out ?? { activated: true, id } });
  } catch (e) {
    res.status(502).json({ ok: false, error: { message: String(e.message || e) } });
  }
});

// GET /api/v1/n8n/workflows/:id
r.get('/workflows/:id', async (req, res) => {
  try {
    const id = req.params.id;
    const wf = await n8nGet(`/api/v1/workflows/${id}`);
    res.json({ ok: true, data: wf });
  } catch (e) {
    res.status(502).json({ ok: false, error: { message: String(e.message || e) } });
  }
});

export default r;