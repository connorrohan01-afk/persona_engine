import { Router } from 'express';
import { parse, NotifyTestSchema, NotifyEventSchema } from '../lib/validators.js';
import { active as mockOn, sendMock } from '../adapters/mock.js';
import { active as tgOn, sendTelegram } from '../adapters/telegram.js';
import { active as emOn, sendEmail } from '../adapters/email.js';

const r = Router();

function adapterStatus() {
  return {
    mock: mockOn(),
    telegram: tgOn(),
    email: emOn()
  };
}

async function dispatchOne({ channel, to, message, meta }) {
  if (channel === 'mock') return sendMock({ to, message, meta });
  if (channel === 'telegram') return sendTelegram({ to, message, meta });
  if (channel === 'email') return sendEmail({ to, message, meta });
  return { ok: false, error: 'unknown_channel' };
}

r.get('/adapters', (_req, res) => res.json({ ok: true, data: adapterStatus() }));

r.post('/test', async (req, res) => {
  const v = parse(NotifyTestSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const out = await dispatchOne(v.data);
  const code = out.ok ? 200 : 502;
  res.status(code).json({ ok: !!out.ok, data: out.ok ? out : undefined, error: out.ok ? undefined : { message: out.error } });
});

r.post('/event', async (req, res) => {
  const v = parse(NotifyEventSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const results = [];
  for (const ch of v.data.channels) {
    const r = await dispatchOne({ ...ch, message: v.data.message, meta: { type: v.data.type, severity: v.data.severity, ...(v.data.meta||{}) } });
    results.push({ channel: ch.channel, to: ch.to, ok: r.ok, error: r.ok ? null : r.error });
  }
  const anyFail = results.some(x => !x.ok);
  res.status(anyFail ? 207 : 200).json({ ok: !anyFail, data: { results } });
});

export default r;