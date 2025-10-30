import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import fetch from 'node-fetch';
import { z } from 'zod';

const app = express();
const PORT = process.env.PORT || 3000;
const BUILDER_TOKEN = process.env.BUILDER_TOKEN || 'builder_token_123';
const N8N_HOST = (process.env.N8N_HOST || '').replace(/\/+$/,'');
const N8N_API_TOKEN = process.env.N8N_API_TOKEN || '';

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));
app.use(rateLimit({ windowMs: 5*60*1000, max: 300, standardHeaders: true }));

function auth(req, res, next) {
  const hdr = req.headers.authorization || '';
  const tok = hdr.startsWith('Bearer ') ? hdr.slice(7) : '';
  if (!tok || tok !== BUILDER_TOKEN) {
    return res.status(401).json({ ok:false, error:{ message:'unauthorized' }});
  }
  next();
}

function requireEnv(res) {
  if (!N8N_HOST || !N8N_API_TOKEN) {
    res.status(500).json({ ok:false, error:{ message:'missing N8N_HOST or N8N_API_TOKEN env' }});
    return false;
  }
  return true;
}

const CreateSchema = z.object({
  name: z.string().min(1).default('Generated Workflow'),
  settings: z.object({ timezone: z.string().default('UTC')}).default({ timezone:'UTC' }),
  nodes: z.array(z.any()).default([]),
  connections: z.record(z.any()).default({})
}).passthrough();

const IdSchema = z.object({ id: z.string().min(1) });

app.get('/api/v1/health', (_req,res) => res.json({ ok:true, data:{ service:'n8n-bridge', status:'healthy' }}));

app.post('/api/v1/n8n/create', auth, async (req, res) => {
  if (!requireEnv(res)) return;
  const parsed = CreateSchema.safeParse(req.body || {});
  if (!parsed.success) return res.status(400).json({ ok:false, error: parsed.error.flatten() });

  try {
    const r = await fetch(`${N8N_HOST}/api/v1/workflows`, {
      method: 'POST',
      headers: {
        'X-N8N-API-KEY': N8N_API_TOKEN,
        'content-type': 'application/json'
      },
      body: JSON.stringify(parsed.data)
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return res.status(r.status).json({ ok:false, error:{ message:'n8n_create_failed', detail:data }});
    res.json({ ok:true, data });
  } catch (e) {
    res.status(502).json({ ok:false, error:{ message:'upstream_error', detail:String(e) }});
  }
});

app.post('/api/v1/n8n/activate', auth, async (req, res) => {
  if (!requireEnv(res)) return;
  const parsed = IdSchema.safeParse({ id: (req.body?.id ?? req.query?.id ?? '').toString() });
  if (!parsed.success) return res.status(400).json({ ok:false, error:{ message:'missing id' }});

  try {
    const r = await fetch(`${N8N_HOST}/api/v1/workflows/${encodeURIComponent(parsed.data.id)}/activate`, {
      method: 'POST',
      headers: { 'X-N8N-API-KEY': N8N_API_TOKEN }
    });
    if (r.status === 204) return res.json({ ok:true, data:{ id: parsed.data.id, status:'activated' }});
    const data = await r.json().catch(()=> ({}));
    if (!r.ok) return res.status(r.status).json({ ok:false, error:{ message:'n8n_activate_failed', detail:data }});
    res.json({ ok:true, data });
  } catch (e) {
    res.status(502).json({ ok:false, error:{ message:'upstream_error', detail:String(e) }});
  }
});

app.get('/api/v1/n8n/get', auth, async (req, res) => {
  if (!requireEnv(res)) return;
  const parsed = IdSchema.safeParse({ id: (req.query?.id ?? '').toString() });
  if (!parsed.success) return res.status(400).json({ ok:false, error:{ message:'missing id' }});

  try {
    const r = await fetch(`${N8N_HOST}/api/v1/workflows/${encodeURIComponent(parsed.data.id)}`, {
      headers: { 'X-N8N-API-KEY': N8N_API_TOKEN }
    });
    const data = await r.json().catch(()=> ({}));
    if (!r.ok) return res.status(r.status).json({ ok:false, error:{ message:'n8n_get_failed', detail:data }});
    res.json({ ok:true, data });
  } catch (e) {
    res.status(502).json({ ok:false, error:{ message:'upstream_error', detail:String(e) }});
  }
});

// 404
app.use((_req,res) => res.status(404).json({ ok:false, error:{ message:'not_found' }}));

// Print routes on boot
function printRoutes() {
  const lines = [];
  if (app._router && app._router.stack) {
    app._router.stack.forEach(l1 => {
      if (l1.route) {
        const meth = Object.keys(l1.route.methods).map(m => m.toUpperCase()).join(',');
        lines.push(`${meth} ${l1.route.path}`);
      }
    });
  } else {
    // Fallback routes
    lines.push('GET    /api/v1/health');
    lines.push('GET    /api/v1/n8n/get');
    lines.push('POST   /api/v1/n8n/activate');
    lines.push('POST   /api/v1/n8n/create');
  }
  console.log('AVAILABLE_ROUTES');
  lines.sort().forEach(l => console.log(l));
}

app.listen(PORT, () => {
  console.log(`n8n-bridge listening on :${PORT}`);
  printRoutes();
  console.log('BRIDGE READY');
});