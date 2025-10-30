import { z } from 'zod';

export const TemplateCreateSchema = z.object({
  name: z.string().min(1),
  body: z.string().min(1),
  variables: z.array(z.string()).default([])
});
export const TemplatePatchSchema = z.object({
  name: z.string().optional(),
  body: z.string().optional(),
  variables: z.array(z.string()).optional()
});

export const PersonaCreateSchema = z.object({
  name: z.string().min(1),
  voice: z.string().default('neutral'),
  tone: z.string().default('informative'),
  rules: z.array(z.string()).optional()
});
export const PersonaPatchSchema = z.object({
  name: z.string().optional(),
  voice: z.string().optional(),
  tone: z.string().optional(),
  rules: z.array(z.string()).optional()
});

export const PlanCreateSchema = z.object({
  accountId: z.string().min(1),
  templateId: z.string().min(1),
  personaId: z.string().optional(),
  variables: z.record(z.any()).default({})
});
export const PlanPatchSchema = z.object({
  templateId: z.string().optional(),
  personaId: z.string().optional(),
  variables: z.record(z.any()).optional()
});

export const PreviewSchema = z.object({
  // Either planId OR (template/body + variables) is required
  planId: z.string().optional(),
  templateId: z.string().optional(),
  body: z.string().optional(),
  variables: z.record(z.any()).default({}),
  personaId: z.string().optional(),
  personaName: z.string().optional(),
  voice: z.string().optional(),
  tone: z.string().optional()
});

export function parse(schema, body) {
  const r = schema.safeParse(body);
  if (!r.success) {
    return { ok: false, error: r.error.flatten() };
  }
  return { ok: true, data: r.data };
}