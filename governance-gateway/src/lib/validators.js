import { z } from 'zod';

export const LimitSchema = z.object({
  action: z.string().min(1),     // e.g., "post", "comment", "warm_tick"
  max: z.number().int().positive(),
  windowMs: z.number().int().positive(),
  cost: z.number().int().positive().default(1),
  dedupeTtlMs: z.number().int().nonnegative().default(0),
  personaId: z.string().optional()  // if absent, applies globally as default
});

export const DecideSchema = z.object({
  personaId: z.string().min(1),
  accountId: z.string().optional(),
  action: z.string().min(1),
  cost: z.number().int().positive().default(1),
  dedupeKey: z.string().optional(),
  meta: z.record(z.any()).optional()
});

export const StrikeSchema = z.object({
  personaId: z.string().min(1),
  action: z.string().min(1),
  reason: z.string().min(1),
  weight: z.number().int().positive().default(1)
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}