/**
 * Shared Request/Response Schemas with Zod Validation
 * Provides type-safe parsing and validation for API endpoints
 */

import { z } from 'zod';

// ============================================================================
// Brain Ask Schemas
// ============================================================================

export const BrainAskReqSchema = z.object({
  persona_id: z.string().optional(),
  question: z.string().min(1, "Question cannot be empty"),
  context: z.record(z.string(), z.any()).optional()
});

export const BrainAskResSchema = z.object({
  ok: z.boolean(),
  mode: z.enum(["live", "fake"]),
  answer: z.string(),
  tokens_used: z.number().optional(),
  error: z.string().optional()
});

export type BrainAskReq = z.infer<typeof BrainAskReqSchema>;
export type BrainAskRes = z.infer<typeof BrainAskResSchema>;

// ============================================================================
// Upsell Suggest Schemas
// ============================================================================

const UpsellSuggestionSchema = z.object({
  title: z.string(),
  copy: z.string(),
  cta: z.string(),
  price_hint: z.string().optional(),
  assets: z.array(z.string()).optional()
});

export const UpsellSuggestReqSchema = z.object({
  user_id: z.string().min(1, "User ID is required"),
  persona_id: z.string().optional(),
  job_id: z.string().optional(),
  style: z.string().optional(),
  intent: z.enum(["prints", "social", "licensing", "followup"]).optional(),
  tone: z.enum(["friendly", "assertive"]).optional()
});

export const UpsellSuggestResSchema = z.object({
  ok: z.boolean(),
  mode: z.enum(["live", "fake"]),
  suggestions: z.array(UpsellSuggestionSchema),
  error: z.string().optional()
});

export type UpsellSuggestReq = z.infer<typeof UpsellSuggestReqSchema>;
export type UpsellSuggestRes = z.infer<typeof UpsellSuggestResSchema>;

// ============================================================================
// Persona Add System Schemas
// ============================================================================

export const PersonaAddSystemReqSchema = z.object({
  id: z.string().min(1, "ID is required").regex(/^U\d+$/, "System persona IDs must start with 'U' followed by numbers (e.g., U0001)"),
  name: z.string().min(1, "Name is required"),
  role: z.enum(["upsell", "system"]),
  traits: z.array(z.string()).optional().default([])
});

export const PersonaAddSystemResSchema = z.object({
  ok: z.boolean(),
  system_persona: z.object({
    id: z.string(),
    name: z.string(),
    role: z.string(),
    traits: z.array(z.string()),
    created_at: z.string(),
    system: z.boolean()
  }).optional(),
  error: z.string().optional()
});

export type PersonaAddSystemReq = z.infer<typeof PersonaAddSystemReqSchema>;
export type PersonaAddSystemRes = z.infer<typeof PersonaAddSystemResSchema>;

// ============================================================================
// Parse Helpers
// ============================================================================

export interface ParseResult<T> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Safely parse and validate request data using Zod schema
 */
export function parseRequest<T>(schema: z.ZodSchema<T>, data: unknown): ParseResult<T> {
  try {
    const result = schema.safeParse(data);
    
    if (result.success) {
      return {
        success: true,
        data: result.data
      };
    } else {
      // Extract first validation error message
      const firstError = result.error.issues[0];
      return {
        success: false,
        error: firstError.message
      };
    }
  } catch (error) {
    return {
      success: false,
      error: 'Invalid request format'
    };
  }
}

/**
 * Parse BrainAsk request body
 */
export function parseBrainAskReq(data: unknown): ParseResult<BrainAskReq> {
  return parseRequest(BrainAskReqSchema, data);
}

/**
 * Parse UpsellSuggest request body
 */
export function parseUpsellSuggestReq(data: unknown): ParseResult<UpsellSuggestReq> {
  return parseRequest(UpsellSuggestReqSchema, data);
}

/**
 * Parse PersonaAddSystem request body
 */
export function parsePersonaAddSystemReq(data: unknown): ParseResult<PersonaAddSystemReq> {
  return parseRequest(PersonaAddSystemReqSchema, data);
}

// ============================================================================
// Response Builders
// ============================================================================

/**
 * Build standardized 400 error response
 */
export function buildValidationError(error: string) {
  return {
    ok: false,
    error
  };
}

/**
 * Build standardized 401 error response
 */
export function buildAuthError(message: string = 'Missing or malformed Authorization header') {
  return {
    ok: false,
    error: message
  };
}