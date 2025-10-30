import { z } from 'zod';

export const EventIngestSchema = z.object({
  type: z.string().min(1),             // e.g. "post_success","post_fail","warm_tick","click","signup"
  personaId: z.string().optional(),
  accountId: z.string().optional(),
  platform: z.string().optional(),     // e.g. "reddit"
  meta: z.record(z.any()).optional(),
  at: z.string().datetime().optional() // ISO timestamp; if missing, server fills
});

export const CounterSchema = z.object({
  key: z.string().min(1),              // e.g. "posts.success","posts.fail","clicks"
  delta: z.number().int().default(1)
});

export const GaugeSchema = z.object({
  key: z.string().min(1),              // e.g. "queue.depth","poster.lag_ms"
  value: z.number()
});

export const ReportQuerySchema = z.object({
  window: z.enum(['1h','6h','24h','7d','30d']).default('24h'),
  personaId: z.string().optional()
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}