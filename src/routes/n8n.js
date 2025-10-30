import { Router } from 'express';

const r = Router();

// Simple bearer check (you can swap to your shared bearerAuth later)
function auth(req, res, next) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  const allow = process.env.AUTH_BEARER_TOKEN || 'builder_token_123';
  if (!token || token !== allow) {
    return res.status(401).json({ ok: false, error: { message: 'unauthorized' } });
  }
  next();
}

r.use(auth);

// POST /api/v1/n8n/create  -> mock-create a workflow and return an id
r.post('/create', (req, res) => {
  const body = req.body || {};
  const id = `wf_${Math.random().toString(36).slice(2, 10)}`;
  res.json({ ok: true, data: { id, created: true, workflow: body } });
});

// POST /api/v1/n8n/activate and POST /api/v1/n8n/activate/:id
r.post('/activate', (req, res) => {
  const id = String(req.body?.id || '').trim();
  if (!id) return res.status(400).json({ ok: false, error: { message: 'id_required' } });
  res.json({ ok: true, data: { id, activated: true } });
});
r.post('/activate/:id', (req, res) => {
  res.json({ ok: true, data: { id: req.params.id, activated: true } });
});

// GET /api/v1/n8n/get and GET /api/v1/n8n/get/:id
r.get('/get', (req, res) => {
  const id = String(req.query.id || '').trim();
  if (!id) return res.status(400).json({ ok: false, error: { message: 'id_required' } });
  res.json({ ok: true, data: { id, name: 'Generated Workflow', settings: { timezone: 'UTC' }, nodes: [], connections: {} } });
});
r.get('/get/:id', (req, res) => {
  res.json({ ok: true, data: { id: req.params.id, name: 'Generated Workflow', settings: { timezone: 'UTC' }, nodes: [], connections: {} } });
});

export default r;