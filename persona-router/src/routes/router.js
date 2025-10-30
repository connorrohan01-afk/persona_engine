import { Router } from 'express';
import { parse, RouteRequestSchema } from '../lib/validators.js';
import { resolveServiceId, getService } from '../lib/registry.js';
import { forwardJson, routePlan } from '../lib/forward.js';
import { buildHeaders } from '../lib/util.js';

const r = Router();

r.post('/', async (req, res) => {
  const v = parse(RouteRequestSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });

  const { tool, action, payload, options } = v.data;
  const serviceId = resolveServiceId(tool, options?.serviceId);
  const reg = getService(serviceId);
  if (!reg) return res.status(400).json({ ok: false, error: { message: 'service_not_registered', serviceId } });

  // Resolve target path
  let path = `router/${tool}/${action}`;
  let method = 'POST';
  const plan = routePlan(tool, action);
  if (plan) { path = plan.path; method = plan.method; }

  const headers = buildHeaders(reg);
  const result = await forwardJson({
    baseUrl: reg.baseUrl,
    path,
    method,
    body: payload || {},
    headers,
    timeoutMs: options.retry.timeoutMs,
    attempts: options.retry.attempts,
    baseMs: options.retry.baseMs
  });

  if (result.ok) {
    return res.status(result.status || 200).json({
      ok: true,
      data: { serviceId, path, ms: result.ms, status: result.status, response: result.data }
    });
  } else {
    return res.status(502).json({
      ok: false,
      error: { message: 'upstream_failed', serviceId, path, detail: result.error || 'error' }
    });
  }
});

export default r;