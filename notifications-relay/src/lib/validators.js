import { z } from 'zod';

export const ChannelRef = z.object({
  channel: z.enum(['mock','telegram','email']),
  to: z.union([z.string().min(1), z.number()]) // chat_id/email etc.
});

export const NotifyTestSchema = z.object({
  channel: z.enum(['mock','telegram','email']),
  to: z.union([z.string().min(1), z.number()]),
  message: z.string().min(1).max(1000)
});

export const NotifyEventSchema = z.object({
  type: z.string().min(1),
  severity: z.enum(['info','warn','error']).optional(),
  message: z.string().min(1).max(1000),
  meta: z.record(z.any()).optional(),
  channels: z.array(ChannelRef).min(1).max(50)
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok: false, error: r.error.flatten() };
  return { ok: true, data: r.data };
}