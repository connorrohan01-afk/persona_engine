import { z } from 'zod';

export const RegistryUpsertSchema = z.object({
  serviceId: z.string().min(1),
  baseUrl: z.string().url(),
  token: z.string().optional(),
  headers: z.record(z.string()).optional(),
  meta: z.record(z.any()).optional()
});

export const RouteRequestSchema = z.object({
  tool: z.enum(['persona','scheduler','vault','intake','notify','raw']).default('raw'),
  action: z.string().min(1),
  payload: z.record(z.any()).default({}),
  options: z.object({
    serviceId: z.string().optional(), // override default mapping
    retry: z.object({
      attempts: z.number().int().min(0).max(5).default(2),
      baseMs: z.number().int().min(50).max(2000).default(200),
      timeoutMs: z.number().int().min(500).max(15000).default(5000)
    }).default({})
  }).default({})
});

export const IdParamSchema = z.object({ id: z.string().min(1) });

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}