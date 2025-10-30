import { z } from 'zod';

export const CadenceCron = z.object({
  kind: z.literal('cron'),
  expr: z.string().min(1) // e.g. "*/30 * * * *"
});

export const CadenceEvery = z.object({
  kind: z.literal('every'),
  startAt: z.string().datetime().optional(), // ISO
  unit: z.enum(['minutes','hours']),
  value: z.number().int().positive()
});

export const ScheduleCreateSchema = z.object({
  personaId: z.string().min(1),
  channel: z.enum(['reddit','telegram','twitter','generic']).default('generic'),
  webhookUrl: z.string().url(),
  secret: z.string().optional(), // optional shared secret for target
  payload: z.record(z.any()).default({}),
  cadence: z.union([CadenceCron, CadenceEvery]),
  enabled: z.boolean().default(true),
  meta: z.record(z.any()).optional()
});

export const SchedulePatchSchema = z.object({
  webhookUrl: z.string().url().optional(),
  secret: z.string().optional(),
  payload: z.record(z.any()).optional(),
  cadence: z.union([CadenceCron, CadenceEvery]).optional(),
  enabled: z.boolean().optional(),
  meta: z.record(z.any()).optional()
});

export const QueryListSchema = z.object({
  personaId: z.string().optional(),
  enabled: z.string().optional(), // "true"|"false"
  channel: z.string().optional()
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}