import { Router } from 'express';

const r = Router();

// Small helper: fetch with timeout
async function doFetch(url, opts = {}, ms = 10000) {
  const ctrl = new AbortController();
  const to = setTimeout(() => ctrl.abort(), ms);
  try {
    const res = await fetch(url, { ...opts, signal: ctrl.signal });
    const text = await res.text();
    let json;
    try { json = JSON.parse(text); } catch { json = { raw: text }; }
    if (!res.ok) {
      const msg = (json?.error?.message) || json?.message || `HTTP ${res.status}`;
      return { ok: false, status: res.status, error: { message: msg, body: json } };
    }
    return { ok: true, status: res.status, data: json };
  } catch (err) {
    return { ok: false, error: { message: err.name === 'AbortError' ? 'timeout' : String(err) } };
  } finally {
    clearTimeout(to);
  }
}

// Normalize incoming body into a workflow payload
function normalizePayload(body = {}) {
  // Accept shapes:
  //  A) { name, spec }  -> wrap into minimal workflow
  //  B) { payload: { workflow: {...} } } or { workflow: {...} }
  //  C) direct { name, settings, nodes, connections }
  const out = { name: 'Generated Workflow', settings: { timezone: 'UTC' }, nodes: [], connections: {} };

  // Try explicit workflow wrapper first
  const wf = body?.payload?.workflow || body?.workflow;
  if (wf && typeof wf === 'object') {
    return {
      name: String(wf.name || out.name),
      settings: typeof wf.settings === 'object' ? wf.settings : out.settings,
      nodes: Array.isArray(wf.nodes) ? wf.nodes : out.nodes,
      connections: typeof wf.connections === 'object' ? wf.connections : out.connections
    };
  }

  // Try direct workflow-ish shape
  if (typeof body?.settings === 'object' || Array.isArray(body?.nodes) || typeof body?.connections === 'object') {
    return {
      name: String(body.name || out.name),
      settings: typeof body.settings === 'object' ? body.settings : out.settings,
      nodes: Array.isArray(body.nodes) ? body.nodes : out.nodes,
      connections: typeof body.connections === 'object' ? body.connections : out.connections
    };
  }

  // Fallback: turn {name,spec} into a trivial scheduled workflow
  const name = String(body.name || out.name);
  const spec = String(body.spec || '').trim(); // informational only; not parsed here
  return {
    name,
    settings: out.settings,
    nodes: [
      {
        id: 'Sched',
        name: 'Schedule Trigger',
        type: 'n8n-nodes-base.scheduleTrigger',
        typeVersion: 1.1,
        position: [200, 300],
        parameters: { triggerTimes: { item: [ { mode: 'everyX', unit: 'minutes', value: 30 } ] } }
      }
    ],
    connections: {}
  };
}

r.post('/build', async (req, res) => {
  try {
    const bearer = process.env.BUILDER_BEARER || 'builder_token_123';
    const port = process.env.PORT || 3000;
    // Always use localhost for internal calls to the same service
    const base = `http://127.0.0.1:${port}`;

    // Accept either { payload: {...} } or a direct workflow-ish body
    const body = (req.body && typeof req.body === 'object') ? req.body : {};
    const workflowPayload = normalizePayload(body);

    // 1) create
    const createResp = await doFetch(`${base}/api/v1/n8n/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${bearer}`
      },
      body: JSON.stringify(workflowPayload)
    }, 15000);

    if (!createResp.ok) {
      return res.status(502).json({ ok: false, error: { message: 'create_failed', detail: createResp.error || createResp.data } });
    }

    // Expect id in data
    const created = createResp.data?.data || createResp.data;
    const workflow_id = created?.id || created?.workflow_id || null;
    const name = created?.name || workflowPayload.name;

    if (!workflow_id) {
      return res.status(502).json({ ok: false, error: { message: 'missing_workflow_id', detail: created } });
    }

    // 2) activate (best-effort; do not block overall success if it fails)
    const activateResp = await doFetch(`${base}/api/v1/n8n/activate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${bearer}`
      },
      body: JSON.stringify({ id: workflow_id })
    }, 10000);

    const activated = !!(activateResp.ok);

    return res.json({
      ok: true,
      data: {
        workflow_id,
        name,
        activated,
        created: created || null
      }
    });
  } catch (err) {
    return res.status(500).json({ ok: false, error: { message: String(err) } });
  }
});

export default r;