"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const config_1 = require("./config");
const log_1 = require("./log");
const personas_1 = require("./personas");
const orchestrator_1 = require("./orchestrator");
const vault_1 = require("./vault");
const notify_1 = require("./notify");
const llm_client_1 = require("./adapters/llm_client");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const schemas_1 = require("./schemas");
const vault_context_1 = require("./vault_context");
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const swagger_ui_express_1 = __importDefault(require("swagger-ui-express"));
const uuid_1 = require("uuid");
const openapi_1 = require("./openapi");
const app = (0, express_1.default)();
const PORT = process.env.PORT || 8000;
const systemState = {};
// Request ID middleware for logging
app.use((req, res, next) => {
    req.request_id = (0, uuid_1.v4)();
    req.start_time = Date.now();
    next();
});
// Rate limiting middleware for protected routes
const apiRateLimit = (0, express_rate_limit_1.default)({
    windowMs: 60 * 1000, // 1 minute
    max: 30, // limit each IP to 30 requests per windowMs
    message: {
        ok: false,
        error: 'Rate limit exceeded. Maximum 30 requests per minute.'
    },
    standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
    legacyHeaders: false, // Disable the `X-RateLimit-*` headers
});
// Middleware
app.use(express_1.default.json());
app.use(express_1.default.urlencoded({ extended: true }));
// Enhanced request logging helper
function logRequest(req, route, mode, persona_id, job_id) {
    const duration = Date.now() - req.start_time;
    log_1.logger.info('API Request', {
        request_id: req.request_id,
        route,
        mode,
        persona_id: persona_id || null,
        job_id: job_id || null,
        ms: duration
    });
}
// Health check endpoint - comprehensive system status
app.get('/api/v1/health', (req, res) => {
    const llmClient = (0, llm_client_1.getLLMClient)();
    res.json({
        ok: true,
        mode_img: config_1.cfg.MODE,
        mode_llm: llmClient.isLive() ? "live" : "fake",
        have: {
            IMG_API_KEY: !!config_1.cfg.IMG_API_KEY,
            ANTHROPIC_API_KEY: !!process.env.ANTHROPIC_API_KEY,
            HMAC_SECRET: !!config_1.cfg.HMAC_SECRET
        },
        routes: [
            "persona.new",
            "gen",
            "gen.more",
            "vault.open",
            "brain.ask",
            "upsell.suggest",
            "status",
            "ping",
            "build"
        ],
        last_upsell: systemState.lastUpsell || null,
        timestamp: new Date().toISOString()
    });
});
// Status endpoint - latest activity summary
app.get('/api/v1/status', (req, res) => {
    res.json({
        ok: true,
        last_job: systemState.lastJob || null,
        last_upsell: systemState.lastUpsell || null
    });
});
// Ping endpoint - simple connectivity test
app.get('/api/v1/ping', (req, res) => {
    res.json({
        ok: true,
        text: "pong"
    });
});
// OpenAPI documentation endpoint
app.use('/docs', swagger_ui_express_1.default.serve, swagger_ui_express_1.default.setup(openapi_1.openApiSpec, {
    customSiteTitle: 'PersonaEngine API Documentation',
    customCss: '.swagger-ui .topbar { display: none }',
    swaggerOptions: {
        persistAuthorization: true,
        displayRequestDuration: true,
        tryItOutEnabled: true
    }
}));
// 1. POST /persona.new - Create new persona
app.post('/api/v1/persona.new', async (req, res) => {
    try {
        const { name, traits, refs } = req.body;
        if (!name || !traits || !Array.isArray(traits)) {
            return res.status(400).json({
                ok: false,
                error: 'Missing required fields: name (string), traits (array)'
            });
        }
        const persona = await (0, personas_1.createPersona)({ name, traits, refs });
        log_1.logger.info(`✅ Created persona via API: ${persona.id}`);
        res.json({
            ok: true,
            persona
        });
    }
    catch (error) {
        log_1.logger.error('❌ Failed to create persona:', error);
        res.status(500).json({
            ok: false,
            error: 'Failed to create persona'
        });
    }
});
// 2. POST /gen - Generate images
app.post('/api/v1/gen', async (req, res) => {
    try {
        const { persona_id, style, count, slots, tone, seed } = req.body;
        // Validate required fields
        if (!persona_id || !style || !count) {
            return res.status(400).json({
                ok: false,
                error: 'Missing required fields: persona_id, style, count'
            });
        }
        // Guard: count 1-50
        if (count < 1 || count > 50) {
            return res.status(400).json({
                ok: false,
                error: 'Count must be between 1 and 50'
            });
        }
        const genRequest = {
            persona_id,
            style,
            count,
            slots,
            tone,
            seed
        };
        // Call orchestrator
        const result = await (0, orchestrator_1.runGen)(genRequest);
        // Update system state for status tracking
        systemState.lastJob = {
            persona: persona_id,
            job: result.jobId,
            style,
            count,
            timestamp: new Date().toISOString()
        };
        // Send notification
        await (0, notify_1.send)({
            job_id: result.jobId,
            persona_id,
            style,
            images: result.images,
            status: 'ok'
        });
        log_1.logger.info(`✅ Generation completed via API: ${result.jobId}`);
        res.json({
            ok: true,
            job_id: result.jobId,
            persona_id,
            style,
            images: result.images
        });
    }
    catch (error) {
        log_1.logger.error('❌ Generation failed via API:', error);
        res.status(500).json({
            ok: false,
            error: 'Generation failed'
        });
    }
});
// 3. GET /vault.open - Get vault link
app.get('/api/v1/vault.open', async (req, res) => {
    try {
        const { persona_id, job_id, style } = req.query;
        if (!persona_id || !job_id || !style) {
            return res.status(400).json({
                ok: false,
                error: 'Missing required query parameters: persona_id, job_id, style'
            });
        }
        const link = (0, vault_1.getVaultLink)(persona_id, job_id, style);
        res.json({
            ok: true,
            link
        });
    }
    catch (error) {
        log_1.logger.error('❌ Failed to get vault link:', error);
        res.status(500).json({
            ok: false,
            error: 'Failed to get vault link'
        });
    }
});
// 3. POST /gen.more - Add more images to existing job
app.post('/api/v1/gen.more', async (req, res) => {
    try {
        const { persona_id, job_id, count } = req.body;
        // Validate required fields
        if (!persona_id || !job_id || !count) {
            return res.status(400).json({
                ok: false,
                error: 'Missing required fields: persona_id, job_id, count'
            });
        }
        // Guard: count 1-50
        if (count < 1 || count > 50) {
            return res.status(400).json({
                ok: false,
                error: 'Count must be between 1 and 50'
            });
        }
        // TODO: Implement gen.more functionality
        // For now, return a placeholder response
        log_1.logger.warn(`⚠️ gen.more not fully implemented yet for job ${job_id}`);
        res.status(501).json({
            ok: false,
            error: 'gen.more functionality not yet implemented'
        });
    }
    catch (error) {
        log_1.logger.error('❌ gen.more failed:', error);
        res.status(500).json({
            ok: false,
            error: 'Failed to append images'
        });
    }
});
// 4. POST /notify - Internal notification endpoint
app.post('/api/v1/notify', async (req, res) => {
    try {
        const payload = req.body;
        await (0, notify_1.send)(payload);
        res.json({ ok: true });
    }
    catch (error) {
        log_1.logger.error('❌ Notification failed:', error);
        res.json({ ok: true }); // Always respond ok: true as specified
    }
});
// Helper function to load persona data
async function loadPersonaData(persona_id) {
    try {
        const personaPath = path.join(process.cwd(), 'vault', 'dev', 'personas', `${persona_id}.json`);
        if (fs.existsSync(personaPath)) {
            const data = JSON.parse(fs.readFileSync(personaPath, 'utf8'));
            return { traits: data.traits || [] };
        }
        // Check system personas
        const systemPersonaPath = path.join(process.cwd(), 'vault', 'dev', 'personas', 'system', `${persona_id}.json`);
        if (fs.existsSync(systemPersonaPath)) {
            const data = JSON.parse(fs.readFileSync(systemPersonaPath, 'utf8'));
            return { traits: data.traits || [] };
        }
        // Also check src/data/personas.json for personas created via API
        const apiPersonaPath = path.join(process.cwd(), 'src', 'data', 'personas.json');
        if (fs.existsSync(apiPersonaPath)) {
            const data = JSON.parse(fs.readFileSync(apiPersonaPath, 'utf8'));
            const persona = data.personas?.find((p) => p.id === persona_id);
            if (persona) {
                return { traits: persona.traits || [] };
            }
        }
        return null;
    }
    catch (error) {
        log_1.logger.warn(`Failed to load persona data for ${persona_id}:`, error);
        return null;
    }
}
// Helper function to save system persona
async function saveSystemPersona(personaData) {
    const systemPersonaPath = path.join(process.cwd(), 'vault', 'dev', 'personas', 'system', `${personaData.id}.json`);
    const dataToSave = {
        ...personaData,
        created_at: new Date().toISOString(),
        system: true
    };
    fs.writeFileSync(systemPersonaPath, JSON.stringify(dataToSave, null, 2));
}
// Helper function to load job manifest from vault
async function loadJobManifest(persona_id, job_id, style) {
    try {
        const manifestPath = path.join(process.cwd(), 'vault', 'dev', persona_id, job_id, style, 'manifest_job.json');
        if (fs.existsSync(manifestPath)) {
            return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        }
        return null;
    }
    catch (error) {
        log_1.logger.warn(`Failed to load job manifest for ${persona_id}/${job_id}/${style}:`, error);
        return null;
    }
}
// Generate deterministic upsell suggestions for fake mode
function generateFakeUpsellSuggestions(context) {
    const { persona_id, job_id, style, intent, tone, jobManifest } = context;
    const imageCount = jobManifest?.count || 6;
    const currentStyle = style || jobManifest?.style || 'studio';
    const suggestions = [];
    if (intent === 'prints' || !intent) {
        suggestions.push({
            title: "Premium Print Package",
            copy: `Transform your ${imageCount} ${currentStyle} shots into professional prints. Perfect for portfolios, gifts, or wall art.`,
            cta: "Order Prints Now",
            price_hint: "$49-89",
            assets: [`${imageCount} high-resolution files`, "Multiple size options", "Premium paper choices"]
        });
    }
    if (intent === 'social' || !intent) {
        suggestions.push({
            title: "Social Media Bundle",
            copy: `Get ${imageCount} images optimized for Instagram, TikTok, and Facebook. Includes multiple aspect ratios and engagement-focused edits.`,
            cta: "Download Social Pack",
            price_hint: "$29-49",
            assets: ["Square crops", "Story formats", "Hashtag suggestions"]
        });
    }
    if (intent === 'followup' || !intent) {
        const moreCount = Math.min(4, Math.max(2, Math.floor(imageCount / 2)));
        suggestions.push({
            title: `Add ${moreCount} More Shots`,
            copy: `Extend your ${currentStyle} session with ${moreCount} additional images. Same style, same quality, more variety.`,
            cta: "Book Extension",
            price_hint: `$${moreCount * 15}-${moreCount * 25}`,
            assets: [`${moreCount} new images`, "Same session style", "48-hour delivery"]
        });
    }
    // Limit to 3 suggestions
    return suggestions.slice(0, 3);
}
// 5. POST /brain.ask - Claude AI brain with persona context
app.post('/api/v1/brain.ask', apiRateLimit, async (req, res) => {
    try {
        // Authentication check
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json((0, schemas_1.buildAuthError)());
        }
        const token = authHeader.substring(7); // Remove 'Bearer '
        if (token !== 'builder_token_123') {
            return res.status(401).json((0, schemas_1.buildAuthError)('Invalid authorization token'));
        }
        // Validate request body
        const parseResult = (0, schemas_1.parseBrainAskReq)(req.body);
        if (!parseResult.success) {
            return res.status(400).json((0, schemas_1.buildValidationError)(parseResult.error));
        }
        const { persona_id, question, context } = parseResult.data;
        // Build vault context including persona and manifest data
        const vaultContext = (0, vault_context_1.buildVaultContext)(persona_id);
        // Load persona data if persona_id provided
        let persona_traits;
        if (vaultContext.persona) {
            persona_traits = vaultContext.persona.traits;
        }
        else if (persona_id) {
            // Fallback to existing persona system
            const personaData = await loadPersonaData(persona_id);
            persona_traits = personaData?.traits;
            if (!personaData) {
                log_1.logger.warn(`Persona ${persona_id} not found, proceeding without persona context`);
            }
        }
        // Build enhanced context for brain query
        let enhancedContext = context || {};
        if (vaultContext.manifest_summary) {
            enhancedContext.manifest_summary = vaultContext.manifest_summary;
        }
        // Get LLM client and ask question with enhanced context
        const llmClient = (0, llm_client_1.getLLMClient)();
        const response = await llmClient.ask({
            question,
            persona_traits,
            context: enhancedContext,
            max_tokens: parseInt(process.env.LLM_MAXTOKENS || "512")
        });
        const mode = llmClient.isLive() ? 'live' : 'fake';
        // Log request with timing and context
        logRequest(req, '/brain.ask', mode, persona_id);
        log_1.logger.info(`🧠 Brain query completed: ${mode} mode`);
        res.json(response);
    }
    catch (error) {
        log_1.logger.error('❌ Brain query failed:', error);
        res.status(500).json({
            ok: false,
            error: 'Brain query failed',
            mode: process.env.LLM_PROVIDER === 'claude' ? 'live' : 'fake'
        });
    }
});
// 6. POST /persona.add_system - Register system-only personas
app.post('/api/v1/persona.add_system', apiRateLimit, async (req, res) => {
    try {
        // Authentication check
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json((0, schemas_1.buildAuthError)());
        }
        const token = authHeader.substring(7);
        if (token !== 'builder_token_123') {
            return res.status(401).json((0, schemas_1.buildAuthError)('Invalid authorization token'));
        }
        // Validate request body
        const parseResult = (0, schemas_1.parsePersonaAddSystemReq)(req.body);
        if (!parseResult.success) {
            return res.status(400).json((0, schemas_1.buildValidationError)(parseResult.error));
        }
        const { id, name, role, traits } = parseResult.data;
        const systemPersona = { id, name, role, traits };
        await saveSystemPersona(systemPersona);
        // Log request with timing and context
        logRequest(req, '/persona.add_system', 'system', id);
        log_1.logger.info(`✅ Created system persona: ${id}`);
        res.json({
            ok: true,
            system_persona: {
                ...systemPersona,
                created_at: new Date().toISOString(),
                system: true
            }
        });
    }
    catch (error) {
        log_1.logger.error('❌ Failed to create system persona:', error);
        res.status(500).json({
            ok: false,
            error: 'Failed to create system persona'
        });
    }
});
// 7. POST /upsell.suggest - Generate upsell suggestions with vault context
app.post('/api/v1/upsell.suggest', apiRateLimit, async (req, res) => {
    try {
        // Authentication check
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json((0, schemas_1.buildAuthError)());
        }
        const token = authHeader.substring(7);
        if (token !== 'builder_token_123') {
            return res.status(401).json((0, schemas_1.buildAuthError)('Invalid authorization token'));
        }
        // Validate request body
        const parseResult = (0, schemas_1.parseUpsellSuggestReq)(req.body);
        if (!parseResult.success) {
            return res.status(400).json((0, schemas_1.buildValidationError)(parseResult.error));
        }
        const { user_id, persona_id, job_id, style, intent, tone } = parseResult.data;
        // Build vault context including persona and manifest data
        const vaultContext = (0, vault_context_1.buildVaultContext)(persona_id, job_id, style);
        // Load persona data for user_id (could be system persona like GBT)
        const userData = await loadPersonaData(user_id);
        // Use vault context manifest summary or fallback to legacy system
        let manifestSummary = vaultContext.manifest_summary;
        if (!manifestSummary && persona_id && job_id && style) {
            // Fallback to existing job manifest loading
            const jobManifest = await loadJobManifest(persona_id, job_id, style);
            if (jobManifest) {
                manifestSummary = {
                    style: jobManifest.style || style,
                    count: jobManifest.count || 0,
                    seeds: [],
                    created_at: jobManifest.created_at || '',
                    files: []
                };
            }
        }
        // Get LLM client
        const llmClient = (0, llm_client_1.getLLMClient)();
        let suggestions = [];
        if (llmClient.isLive()) {
            // Live mode: Use LLM for suggestions
            try {
                // Build upsell brief with manifest summary
                let brief = `Generate 3 concise upsell suggestions for a photo studio customer.

Context:
- User: ${user_id}
- Persona: ${persona_id || 'unknown'}
- Intent: ${intent || 'general'}
- Tone: ${tone || 'friendly'}`;
                if (manifestSummary) {
                    brief += `
- Job completed: ${manifestSummary.count} ${manifestSummary.style} images
- Created: ${manifestSummary.created_at}
- Files: ${manifestSummary.files.slice(0, 3).join(', ')}${manifestSummary.files.length > 3 ? '...' : ''}`;
                }
                brief += `

Return exactly 3 tailored offers. Each should have:
- Title (max 6 words)
- Copy (1 sentence)
- CTA (action verb)
- Price hint (optional)

Focus on: prints, social media, licensing, or followup shoots based on intent.`;
                const response = await llmClient.ask({
                    question: brief,
                    persona_traits: userData?.traits,
                    max_tokens: 400
                });
                if (response.ok) {
                    // Parse LLM response into structured suggestions
                    // For now, use a simple parsing approach
                    const lines = response.answer.split('\n').filter(line => line.trim());
                    let currentSuggestion = null;
                    for (const line of lines) {
                        if (line.match(/^\d+\./)) {
                            if (currentSuggestion)
                                suggestions.push(currentSuggestion);
                            currentSuggestion = { title: '', copy: '', cta: '', price_hint: '' };
                        }
                        if (line.includes('Title:')) {
                            if (currentSuggestion)
                                currentSuggestion.title = line.split('Title:')[1]?.trim() || '';
                        }
                        else if (line.includes('Copy:')) {
                            if (currentSuggestion)
                                currentSuggestion.copy = line.split('Copy:')[1]?.trim() || '';
                        }
                        else if (line.includes('CTA:')) {
                            if (currentSuggestion)
                                currentSuggestion.cta = line.split('CTA:')[1]?.trim() || '';
                        }
                        else if (line.includes('Price:')) {
                            if (currentSuggestion)
                                currentSuggestion.price_hint = line.split('Price:')[1]?.trim() || '';
                        }
                    }
                    if (currentSuggestion)
                        suggestions.push(currentSuggestion);
                }
            }
            catch (error) {
                log_1.logger.error('LLM upsell generation failed, falling back to templates:', error);
            }
        }
        // Fallback to deterministic templates if no LLM suggestions
        if (suggestions.length === 0) {
            suggestions = generateFakeUpsellSuggestions({
                persona_id, job_id, style, intent, tone, manifest: manifestSummary
            });
        }
        const finalSuggestions = suggestions.slice(0, 3); // Always limit to 3
        const mode = llmClient.isLive() ? 'live' : 'fake';
        // Update system state for status tracking
        systemState.lastUpsell = {
            suggestions_count: finalSuggestions.length,
            mode,
            timestamp: new Date().toISOString()
        };
        // Log request with timing and context
        logRequest(req, '/upsell.suggest', mode, persona_id, job_id);
        log_1.logger.info(`💰 Upsell suggestions generated: ${mode} mode`);
        res.json({
            ok: true,
            suggestions: finalSuggestions,
            mode,
            context: {
                user_id,
                persona_id,
                job_id,
                style,
                intent,
                images_count: manifestSummary?.count
            }
        });
    }
    catch (error) {
        log_1.logger.error('❌ Upsell suggestion failed:', error);
        res.status(500).json({
            ok: false,
            error: 'Failed to generate upsell suggestions'
        });
    }
});
// Legacy build endpoint for backward compatibility
app.post('/api/v1/build', (req, res) => {
    log_1.logger.warn('⚠️ Legacy /build endpoint accessed - deprecated');
    res.status(410).json({
        ok: false,
        message: "This endpoint is deprecated. Use /api/v1/gen for image generation or /api/v1/persona.new for persona creation.",
        deprecated: true,
        use_instead: {
            persona_creation: "/api/v1/persona.new",
            image_generation: "/api/v1/gen",
            vault_access: "/api/v1/vault.open"
        }
    });
});
// Start server
if (require.main === module) {
    app.listen(PORT, () => {
        log_1.logger.info(`Server running on port ${PORT}`);
        log_1.logger.info(`Mode: ${config_1.cfg.MODE}`);
        log_1.logger.info(`Health check: http://localhost:${PORT}/api/v1/health`);
    });
}
exports.default = app;
//# sourceMappingURL=server.js.map