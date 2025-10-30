import { Router } from 'express';
import axios from 'axios';
import { parse, ServiceUpsertSchema, HeartbeatSchema, PingRequestSchema, PatchStatusSchema } from '../lib/validators.js';
import { upsertService, recordHeartbeat, getService, manualStatus, pushEvent } from '../lib/store.js';
import { requireBearer } from '../lib/auth.js';
import { notifyStatusChange } from '../lib/notify.js';

const r = Router();

// Upsert/register a service (auth)
r.post('/register', requireBearer, async (req, res) => {
  const v = parse(ServiceUpsertSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const rec = upsertService(v.data);
  return res.json({ ok: true, data: rec });
});

// Heartbeat (auth)
r.post('/heartbeat', requireBearer, async (req, res) => {
  const v = parse(HeartbeatSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const rec = recordHeartbeat(v.data.serviceId, v.data.at);
  if (!rec) return res.status(404).json({ ok: false, error: { message: 'service_not_found' } });
  return res.json({ ok: true, data: rec });
});

// Manual status patch (auth)
r.patch('/status/:serviceId', requireBearer, async (req, res) => {
  const v = parse(PatchStatusSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const before = getService(req.params.serviceId);
  if (!before) return res.status(404).json({ ok: false, error: { message: 'service_not_found' } });
  const updated = manualStatus(req.params.serviceId, v.data.status || before.status);
  if (!updated) return res.status(500).json({ ok: false, error: { message: 'update_failed' } });

  // optional webhook notify
  if (before.status !== updated.status) {
    const snapshot = { id: updated.id, status: updated.status, group: updated.group, lastBeatAt: updated.lastBeatAt };
    await notifyStatusChange({ serviceId: updated.id, prev: before.status, next: updated.status, at: updated.updatedAt, snapshot });
  }
  return res.json({ ok: true, data: updated });
});

// On-demand ping (auth)
r.post('/ping', requireBearer, async (req, res) => {
  const v = parse(PingRequestSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  try {
    const t0 = Date.now();
    const fn = v.data.method === 'HEAD' ? axios.head : axios.get;
    const rres = await fn(v.data.url, { timeout: v.data.timeoutMs, validateStatus: () => true });
    const ms = Date.now() - t0;
    const up = rres.status >= 200 && rres.status < 400;
    return res.json({ ok: true, data: { url: v.data.url, method: v.data.method, status: up ? 'up' : 'down', code: rres.status, ms } });
  } catch (e) {
    return res.json({ ok: true, data: { url: v.data.url, method: v.data.method, status: 'down', code: 0, ms: null, error: e.message?.slice(0,160) || 'error' } });
  }
});

export default r;