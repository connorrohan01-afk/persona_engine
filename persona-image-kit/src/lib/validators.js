import { z } from 'zod';

export const AvatarSchema = z.object({
  initials: z.string().min(1).max(4),
  size: z.number().int().min(64).max(1024).default(512),
  bg: z.string().regex(/^#?[0-9a-fA-F]{6}$/).default('#111827'),
  fg: z.string().regex(/^#?[0-9a-fA-F]{6}$/).default('#F9FAFB')
});

export const OverlaySchema = z.object({
  text: z.string().min(1),
  width: z.number().int().min(64).max(2048),
  height: z.number().int().min(64).max(2048),
  bg: z.string().regex(/^#?[0-9a-fA-F]{6}$/).default('#0B1020'),
  fg: z.string().regex(/^#?[0-9a-fA-F]{6}$/).default('#E5E7EB'),
  fontSize: z.number().int().min(8).max(256).default(42)
});

export const TransformSchema = z.object({
  imageBase64: z.string().min(20), // "data:image/png;base64,…" or raw base64
  ops: z.array(z.object({
    type: z.enum(['resize','crop']),
    w: z.number().int().optional(),
    h: z.number().int().optional(),
    x: z.number().int().optional(),
    y: z.number().int().optional()
  })).min(1),
  output: z.enum(['base64','file']).default('file')
});

export const MemeSchema = z.object({
  topText: z.string().optional(),
  bottomText: z.string().optional(),
  width: z.number().int().min(128).max(2048).default(800),
  height: z.number().int().min(128).max(2048).default(800),
  bg: z.string().regex(/^#?[0-9a-fA-F]{6}$/).default('#000000'),
  fg: z.string().regex(/^#?[0-9a-fA-F]{6}$/).default('#FFFFFF')
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) return { ok:false, error:r.error.flatten() };
  return { ok:true, data:r.data };
}