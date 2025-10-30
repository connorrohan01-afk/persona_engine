import { z } from 'zod';

export const JobCreateSchema = z.object({
  type: z.string().min(1),
  payload: z.record(z.any()).optional(),
  delayMs: z.number().int().min(0).max(86400000).optional()
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}