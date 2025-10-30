import { z } from 'zod';

export const AccountCreateSchema = z.object({
  platform: z.string().min(2),                 // e.g., "reddit" (label only; no external calls)
  username: z.string().min(1),
  notes: z.string().optional(),
  proxyId: z.string().optional(),
  vaultId: z.string().optional(),
  session: z.object({
    cookies: z.string().optional(),            // raw cookie string (stored as provided)
    token: z.string().optional(),              // bearer or csrf token blob
    meta: z.record(z.any()).optional()
  }).optional(),
  meta: z.record(z.any()).optional()
});

export const AccountPatchSchema = z.object({
  username: z.string().optional(),
  notes: z.string().optional(),
  proxyId: z.string().nullable().optional(),
  vaultId: z.string().nullable().optional(),
  session: z.object({
    cookies: z.string().nullable().optional(),
    token: z.string().nullable().optional(),
    meta: z.record(z.any()).optional()
  }).optional(),
  meta: z.record(z.any()).optional(),
  status: z.enum(['intake','warm','active','disabled']).optional()
});

export const ProxySchema = z.object({
  label: z.string().min(1),
  url: z.string().url(), // stored only; no connectivity
  meta: z.record(z.any()).optional()
});

export const VaultCreateSchema = z.object({
  label: z.string().min(1),
  blob: z.string().min(1), // base64 or string content
  meta: z.record(z.any()).optional()
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) {
    return { ok: false, error: r.error.flatten() };
  }
  return { ok: true, data: r.data };
}