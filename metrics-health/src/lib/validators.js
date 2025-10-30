import { z } from 'zod';

export const ServiceUpsertSchema = z.object({
  serviceId: z.string().min(1),
  displayName: z.string().min(1).optional(),
  group: z.string().optional(), // e.g., "core", "edge", "bots"
  url: z.string().url().optional(), // optional health URL
  ttlMs: z.number().int().positive().default(120000), // 2 min default
  meta: z.record(z.any()).optional()
});

export const HeartbeatSchema = z.object({
  serviceId: z.string().min(1),
  at: z.string().datetime().optional() // ISO, default now
});

export const PingRequestSchema = z.object({
  url: z.string().url(),
  method: z.enum(['HEAD','GET']).default('HEAD'),
  timeoutMs: z.number().int().positive().max(15000).default(5000)
});

export const PatchStatusSchema = z.object({
  status: z.enum(['up','down','stale']).optional(),
  meta: z.record(z.any()).optional()
});

export const QueryListSchema = z.object({
  group: z.string().optional(),
  status: z.enum(['up','down','stale']).optional()
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}