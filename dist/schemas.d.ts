/**
 * Shared Request/Response Schemas with Zod Validation
 * Provides type-safe parsing and validation for API endpoints
 */
import { z } from 'zod';
export declare const BrainAskReqSchema: z.ZodObject<{
    persona_id: z.ZodOptional<z.ZodString>;
    question: z.ZodString;
    context: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodAny>>;
}, z.core.$strip>;
export declare const BrainAskResSchema: z.ZodObject<{
    ok: z.ZodBoolean;
    mode: z.ZodEnum<{
        fake: "fake";
        live: "live";
    }>;
    answer: z.ZodString;
    tokens_used: z.ZodOptional<z.ZodNumber>;
    error: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export type BrainAskReq = z.infer<typeof BrainAskReqSchema>;
export type BrainAskRes = z.infer<typeof BrainAskResSchema>;
export declare const UpsellSuggestReqSchema: z.ZodObject<{
    user_id: z.ZodString;
    persona_id: z.ZodOptional<z.ZodString>;
    job_id: z.ZodOptional<z.ZodString>;
    style: z.ZodOptional<z.ZodString>;
    intent: z.ZodOptional<z.ZodEnum<{
        prints: "prints";
        social: "social";
        licensing: "licensing";
        followup: "followup";
    }>>;
    tone: z.ZodOptional<z.ZodEnum<{
        friendly: "friendly";
        assertive: "assertive";
    }>>;
}, z.core.$strip>;
export declare const UpsellSuggestResSchema: z.ZodObject<{
    ok: z.ZodBoolean;
    mode: z.ZodEnum<{
        fake: "fake";
        live: "live";
    }>;
    suggestions: z.ZodArray<z.ZodObject<{
        title: z.ZodString;
        copy: z.ZodString;
        cta: z.ZodString;
        price_hint: z.ZodOptional<z.ZodString>;
        assets: z.ZodOptional<z.ZodArray<z.ZodString>>;
    }, z.core.$strip>>;
    error: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export type UpsellSuggestReq = z.infer<typeof UpsellSuggestReqSchema>;
export type UpsellSuggestRes = z.infer<typeof UpsellSuggestResSchema>;
export declare const PersonaAddSystemReqSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    role: z.ZodEnum<{
        upsell: "upsell";
        system: "system";
    }>;
    traits: z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodString>>>;
}, z.core.$strip>;
export declare const PersonaAddSystemResSchema: z.ZodObject<{
    ok: z.ZodBoolean;
    system_persona: z.ZodOptional<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        role: z.ZodString;
        traits: z.ZodArray<z.ZodString>;
        created_at: z.ZodString;
        system: z.ZodBoolean;
    }, z.core.$strip>>;
    error: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export type PersonaAddSystemReq = z.infer<typeof PersonaAddSystemReqSchema>;
export type PersonaAddSystemRes = z.infer<typeof PersonaAddSystemResSchema>;
export interface ParseResult<T> {
    success: boolean;
    data?: T;
    error?: string;
}
/**
 * Safely parse and validate request data using Zod schema
 */
export declare function parseRequest<T>(schema: z.ZodSchema<T>, data: unknown): ParseResult<T>;
/**
 * Parse BrainAsk request body
 */
export declare function parseBrainAskReq(data: unknown): ParseResult<BrainAskReq>;
/**
 * Parse UpsellSuggest request body
 */
export declare function parseUpsellSuggestReq(data: unknown): ParseResult<UpsellSuggestReq>;
/**
 * Parse PersonaAddSystem request body
 */
export declare function parsePersonaAddSystemReq(data: unknown): ParseResult<PersonaAddSystemReq>;
/**
 * Build standardized 400 error response
 */
export declare function buildValidationError(error: string): {
    ok: boolean;
    error: string;
};
/**
 * Build standardized 401 error response
 */
export declare function buildAuthError(message?: string): {
    ok: boolean;
    error: string;
};
//# sourceMappingURL=schemas.d.ts.map