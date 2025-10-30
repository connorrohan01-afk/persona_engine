import { Router } from 'express';
import { parse, DecideSchema } from '../lib/validators.js';
import { getEffectiveLimit, sweepUsage, addUsage, inDedupeWindow, setDedupe, getBackoff, clearBackoff } from '../lib/store.js';

const r = Router();

// POST /decide  — evaluate and optionally consume tokens
r.post('/', (req, res) => {
  const v = parse(DecideSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const { personaId, action, cost, dedupeKey } = v.data;

  const eff = getEffectiveLimit(personaId, action);
  if (!eff) {
    return res.json({ ok: true, data: { allow: false, waitForMs: 60_000, reason: 'no_limit_defined' } });
  }

  // Check backoff
  const bo = getBackoff(personaId, action);
  if (Date.now() < bo.until) {
    return res.json({
      ok: true,
      data: {
        allow: false,
        waitForMs: Math.max(bo.until - Date.now(), 1),
        reason: 'backoff_active',
        backoffMs: Math.max(bo.until - Date.now(), 1)
      }
    });
  } else if (bo.level > 0) {
    // backoff elapsed, clear it
    clearBackoff(personaId, action);
  }

  // Dedupe window
  if (dedupeKey && inDedupeWindow(dedupeKey)) {
    return res.json({ ok: true, data: { allow: false, waitForMs: 10_000, reason: 'duplicate_suppressed' } });
  }

  // Rolling window consumption
  const arr = sweepUsage(personaId, action, eff.windowMs);
  const used = arr.length;
  const remaining = Math.max(eff.max - used, 0);

  if (remaining <= 0 || cost > remaining) {
    const windowEndsAt = new Date(arr[0] + eff.windowMs).toISOString();
    const wait = Math.max((arr[0] + eff.windowMs) - Date.now(), 1);
    return res.json({
      ok: true,
      data: {
        allow: false,
        waitForMs: wait,
        reason: 'rate_limited',
        tokensRemaining: remaining,
        windowEndsAt
      }
    });
  }

  // Allow + consume
  addUsage(personaId, action, cost);
  if (dedupeKey && eff.dedupeTtlMs > 0) setDedupe(dedupeKey, eff.dedupeTtlMs);

  const windowEndsAt = arr.length
    ? new Date(arr[0] + eff.windowMs).toISOString()
    : new Date(Date.now() + eff.windowMs).toISOString();

  return res.json({
    ok: true,
    data: {
      allow: true,
      waitForMs: 0,
      reason: 'ok',
      tokensRemaining: Math.max(eff.max - (used + cost), 0),
      nextAllowedAt: new Date().toISOString(),
      windowEndsAt
    }
  });
});

export default r;