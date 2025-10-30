"use strict";
/**
 * Shared Request/Response Schemas with Zod Validation
 * Provides type-safe parsing and validation for API endpoints
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PersonaAddSystemResSchema = exports.PersonaAddSystemReqSchema = exports.UpsellSuggestResSchema = exports.UpsellSuggestReqSchema = exports.BrainAskResSchema = exports.BrainAskReqSchema = void 0;
exports.parseRequest = parseRequest;
exports.parseBrainAskReq = parseBrainAskReq;
exports.parseUpsellSuggestReq = parseUpsellSuggestReq;
exports.parsePersonaAddSystemReq = parsePersonaAddSystemReq;
exports.buildValidationError = buildValidationError;
exports.buildAuthError = buildAuthError;
const zod_1 = require("zod");
// ============================================================================
// Brain Ask Schemas
// ============================================================================
exports.BrainAskReqSchema = zod_1.z.object({
    persona_id: zod_1.z.string().optional(),
    question: zod_1.z.string().min(1, "Question cannot be empty"),
    context: zod_1.z.record(zod_1.z.string(), zod_1.z.any()).optional()
});
exports.BrainAskResSchema = zod_1.z.object({
    ok: zod_1.z.boolean(),
    mode: zod_1.z.enum(["live", "fake"]),
    answer: zod_1.z.string(),
    tokens_used: zod_1.z.number().optional(),
    error: zod_1.z.string().optional()
});
// ============================================================================
// Upsell Suggest Schemas
// ============================================================================
const UpsellSuggestionSchema = zod_1.z.object({
    title: zod_1.z.string(),
    copy: zod_1.z.string(),
    cta: zod_1.z.string(),
    price_hint: zod_1.z.string().optional(),
    assets: zod_1.z.array(zod_1.z.string()).optional()
});
exports.UpsellSuggestReqSchema = zod_1.z.object({
    user_id: zod_1.z.string().min(1, "User ID is required"),
    persona_id: zod_1.z.string().optional(),
    job_id: zod_1.z.string().optional(),
    style: zod_1.z.string().optional(),
    intent: zod_1.z.enum(["prints", "social", "licensing", "followup"]).optional(),
    tone: zod_1.z.enum(["friendly", "assertive"]).optional()
});
exports.UpsellSuggestResSchema = zod_1.z.object({
    ok: zod_1.z.boolean(),
    mode: zod_1.z.enum(["live", "fake"]),
    suggestions: zod_1.z.array(UpsellSuggestionSchema),
    error: zod_1.z.string().optional()
});
// ============================================================================
// Persona Add System Schemas
// ============================================================================
exports.PersonaAddSystemReqSchema = zod_1.z.object({
    id: zod_1.z.string().min(1, "ID is required").regex(/^U\d+$/, "System persona IDs must start with 'U' followed by numbers (e.g., U0001)"),
    name: zod_1.z.string().min(1, "Name is required"),
    role: zod_1.z.enum(["upsell", "system"]),
    traits: zod_1.z.array(zod_1.z.string()).optional().default([])
});
exports.PersonaAddSystemResSchema = zod_1.z.object({
    ok: zod_1.z.boolean(),
    system_persona: zod_1.z.object({
        id: zod_1.z.string(),
        name: zod_1.z.string(),
        role: zod_1.z.string(),
        traits: zod_1.z.array(zod_1.z.string()),
        created_at: zod_1.z.string(),
        system: zod_1.z.boolean()
    }).optional(),
    error: zod_1.z.string().optional()
});
/**
 * Safely parse and validate request data using Zod schema
 */
function parseRequest(schema, data) {
    try {
        const result = schema.safeParse(data);
        if (result.success) {
            return {
                success: true,
                data: result.data
            };
        }
        else {
            // Extract first validation error message
            const firstError = result.error.issues[0];
            return {
                success: false,
                error: firstError.message
            };
        }
    }
    catch (error) {
        return {
            success: false,
            error: 'Invalid request format'
        };
    }
}
/**
 * Parse BrainAsk request body
 */
function parseBrainAskReq(data) {
    return parseRequest(exports.BrainAskReqSchema, data);
}
/**
 * Parse UpsellSuggest request body
 */
function parseUpsellSuggestReq(data) {
    return parseRequest(exports.UpsellSuggestReqSchema, data);
}
/**
 * Parse PersonaAddSystem request body
 */
function parsePersonaAddSystemReq(data) {
    return parseRequest(exports.PersonaAddSystemReqSchema, data);
}
// ============================================================================
// Response Builders
// ============================================================================
/**
 * Build standardized 400 error response
 */
function buildValidationError(error) {
    return {
        ok: false,
        error
    };
}
/**
 * Build standardized 401 error response
 */
function buildAuthError(message = 'Missing or malformed Authorization header') {
    return {
        ok: false,
        error: message
    };
}
//# sourceMappingURL=schemas.js.map