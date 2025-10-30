import express from 'express';
import { cfg } from './config';
import { logger } from './log';
import { createPersona, getPersona } from './personas';
import { runGen } from './orchestrator';
import { getVaultLink } from './vault';
import { send as notifySend } from './notify';
import { GenRequest } from './types';
import { getLLMClient } from './adapters/llm_client';
import * as fs from 'fs';
import * as path from 'path';
import { 
  parseBrainAskReq, 
  parseUpsellSuggestReq, 
  parsePersonaAddSystemReq,
  buildValidationError,
  buildAuthError 
} from './schemas';
import { buildVaultContext } from './vault_context';
import rateLimit from 'express-rate-limit';
import swaggerUi from 'swagger-ui-express';
import { v4 as uuidv4 } from 'uuid';
import { openApiSpec } from './openapi';

const app = express();
const PORT = process.env.PORT || 8000;

// Global state tracking for status endpoint
interface SystemState {
  lastJob?: {
    persona: string;
    job: string;
    style: string;
    count: number;
    timestamp: string;
  };
  lastUpsell?: {
    suggestions_count: number;
    mode: "live" | "fake";
    timestamp: string;
  };
}

const systemState: SystemState = {};

// Request ID middleware for logging
app.use((req: any, res, next) => {
  req.request_id = uuidv4();
  req.start_time = Date.now();
  next();
});

// Rate limiting middleware for protected routes
const apiRateLimit = rateLimit({
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
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Enhanced request logging helper
function logRequest(req: any, route: string, mode: string, persona_id?: string, job_id?: string) {
  const duration = Date.now() - req.start_time;
  logger.info('API Request', {
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
  const llmClient = getLLMClient();
  
  res.json({
    ok: true,
    mode_img: cfg.MODE,
    mode_llm: llmClient.isLive() ? "live" : "fake",
    have: {
      IMG_API_KEY: !!cfg.IMG_API_KEY,
      ANTHROPIC_API_KEY: !!process.env.ANTHROPIC_API_KEY,
      HMAC_SECRET: !!cfg.HMAC_SECRET
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
app.use('/docs', swaggerUi.serve, swaggerUi.setup(openApiSpec, {
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
    
    const persona = await createPersona({ name, traits, refs });
    logger.info(`✅ Created persona via API: ${persona.id}`);
    
    res.json({
      ok: true,
      persona
    });
  } catch (error) {
    logger.error('❌ Failed to create persona:', error);
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
    
    const genRequest: GenRequest = {
      persona_id,
      style,
      count,
      slots,
      tone,
      seed
    };
    
    // Call orchestrator
    const result = await runGen(genRequest);
    
    // Update system state for status tracking
    systemState.lastJob = {
      persona: persona_id,
      job: result.jobId,
      style,
      count,
      timestamp: new Date().toISOString()
    };
    
    // Send notification
    await notifySend({
      job_id: result.jobId,
      persona_id,
      style,
      images: result.images,
      status: 'ok'
    });
    
    logger.info(`✅ Generation completed via API: ${result.jobId}`);
    
    res.json({
      ok: true,
      job_id: result.jobId,
      persona_id,
      style,
      images: result.images
    });
  } catch (error) {
    logger.error('❌ Generation failed via API:', error);
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
    
    const link = getVaultLink(persona_id as string, job_id as string, style as string);
    
    res.json({
      ok: true,
      link
    });
  } catch (error) {
    logger.error('❌ Failed to get vault link:', error);
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
    logger.warn(`⚠️ gen.more not fully implemented yet for job ${job_id}`);
    
    res.status(501).json({
      ok: false,
      error: 'gen.more functionality not yet implemented'
    });
  } catch (error) {
    logger.error('❌ gen.more failed:', error);
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
    await notifySend(payload);
    
    res.json({ ok: true });
  } catch (error) {
    logger.error('❌ Notification failed:', error);
    res.json({ ok: true }); // Always respond ok: true as specified
  }
});

// Helper function to load persona data
async function loadPersonaData(persona_id: string): Promise<{ traits: string[] } | null> {
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
      const persona = data.personas?.find((p: any) => p.id === persona_id);
      if (persona) {
        return { traits: persona.traits || [] };
      }
    }
    
    return null;
  } catch (error) {
    logger.warn(`Failed to load persona data for ${persona_id}:`, error);
    return null;
  }
}

// Helper function to save system persona
async function saveSystemPersona(personaData: any): Promise<void> {
  const systemPersonaPath = path.join(process.cwd(), 'vault', 'dev', 'personas', 'system', `${personaData.id}.json`);
  const dataToSave = {
    ...personaData,
    created_at: new Date().toISOString(),
    system: true
  };
  
  fs.writeFileSync(systemPersonaPath, JSON.stringify(dataToSave, null, 2));
}

// Helper function to load job manifest from vault
async function loadJobManifest(persona_id: string, job_id: string, style: string): Promise<any | null> {
  try {
    const manifestPath = path.join(process.cwd(), 'vault', 'dev', persona_id, job_id, style, 'manifest_job.json');
    if (fs.existsSync(manifestPath)) {
      return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    }
    return null;
  } catch (error) {
    logger.warn(`Failed to load job manifest for ${persona_id}/${job_id}/${style}:`, error);
    return null;
  }
}

// Generate deterministic upsell suggestions for fake mode
function generateFakeUpsellSuggestions(context: any): any[] {
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
app.post('/api/v1/brain.ask', apiRateLimit, async (req: any, res) => {
  try {
    // Authentication check
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json(buildAuthError());
    }
    
    const token = authHeader.substring(7); // Remove 'Bearer '
    if (token !== 'builder_token_123') {
      return res.status(401).json(buildAuthError('Invalid authorization token'));
    }
    
    // Validate request body
    const parseResult = parseBrainAskReq(req.body);
    if (!parseResult.success) {
      return res.status(400).json(buildValidationError(parseResult.error!));
    }
    
    const { persona_id, question, context } = parseResult.data!;
    
    // Build vault context including persona and manifest data
    const vaultContext = buildVaultContext(persona_id);
    
    // Load persona data if persona_id provided
    let persona_traits: string[] | undefined;
    if (vaultContext.persona) {
      persona_traits = vaultContext.persona.traits;
    } else if (persona_id) {
      // Fallback to existing persona system
      const personaData = await loadPersonaData(persona_id);
      persona_traits = personaData?.traits;
      if (!personaData) {
        logger.warn(`Persona ${persona_id} not found, proceeding without persona context`);
      }
    }
    
    // Build enhanced context for brain query
    let enhancedContext = context || {};
    if (vaultContext.manifest_summary) {
      enhancedContext.manifest_summary = vaultContext.manifest_summary;
    }
    
    // Get LLM client and ask question with enhanced context
    const llmClient = getLLMClient();
    const response = await llmClient.ask({
      question,
      persona_traits,
      context: enhancedContext,
      max_tokens: parseInt(process.env.LLM_MAXTOKENS || "512")
    });
    
    const mode = llmClient.isLive() ? 'live' : 'fake';
    
    // Log request with timing and context
    logRequest(req, '/brain.ask', mode, persona_id);
    
    logger.info(`🧠 Brain query completed: ${mode} mode`);
    
    res.json(response);
  } catch (error) {
    logger.error('❌ Brain query failed:', error);
    res.status(500).json({
      ok: false,
      error: 'Brain query failed',
      mode: process.env.LLM_PROVIDER === 'claude' ? 'live' : 'fake'
    });
  }
});

// 6. POST /persona.add_system - Register system-only personas
app.post('/api/v1/persona.add_system', apiRateLimit, async (req: any, res) => {
  try {
    // Authentication check
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json(buildAuthError());
    }
    
    const token = authHeader.substring(7);
    if (token !== 'builder_token_123') {
      return res.status(401).json(buildAuthError('Invalid authorization token'));
    }
    
    // Validate request body
    const parseResult = parsePersonaAddSystemReq(req.body);
    if (!parseResult.success) {
      return res.status(400).json(buildValidationError(parseResult.error!));
    }
    
    const { id, name, role, traits } = parseResult.data!;
    
    const systemPersona = { id, name, role, traits };
    await saveSystemPersona(systemPersona);
    
    // Log request with timing and context
    logRequest(req, '/persona.add_system', 'system', id);
    
    logger.info(`✅ Created system persona: ${id}`);
    
    res.json({
      ok: true,
      system_persona: {
        ...systemPersona,
        created_at: new Date().toISOString(),
        system: true
      }
    });
  } catch (error) {
    logger.error('❌ Failed to create system persona:', error);
    res.status(500).json({
      ok: false,
      error: 'Failed to create system persona'
    });
  }
});

// 7. POST /upsell.suggest - Generate upsell suggestions with vault context
app.post('/api/v1/upsell.suggest', apiRateLimit, async (req: any, res) => {
  try {
    // Authentication check
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json(buildAuthError());
    }
    
    const token = authHeader.substring(7);
    if (token !== 'builder_token_123') {
      return res.status(401).json(buildAuthError('Invalid authorization token'));
    }
    
    // Validate request body
    const parseResult = parseUpsellSuggestReq(req.body);
    if (!parseResult.success) {
      return res.status(400).json(buildValidationError(parseResult.error!));
    }
    
    const { user_id, persona_id, job_id, style, intent, tone } = parseResult.data!;
    
    // Build vault context including persona and manifest data
    const vaultContext = buildVaultContext(persona_id, job_id, style);
    
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
    const llmClient = getLLMClient();
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
          let currentSuggestion: any = null;
          
          for (const line of lines) {
            if (line.match(/^\d+\./)) {
              if (currentSuggestion) suggestions.push(currentSuggestion);
              currentSuggestion = { title: '', copy: '', cta: '', price_hint: '' };
            }
            
            if (line.includes('Title:')) {
              if (currentSuggestion) currentSuggestion.title = line.split('Title:')[1]?.trim() || '';
            } else if (line.includes('Copy:')) {
              if (currentSuggestion) currentSuggestion.copy = line.split('Copy:')[1]?.trim() || '';
            } else if (line.includes('CTA:')) {
              if (currentSuggestion) currentSuggestion.cta = line.split('CTA:')[1]?.trim() || '';
            } else if (line.includes('Price:')) {
              if (currentSuggestion) currentSuggestion.price_hint = line.split('Price:')[1]?.trim() || '';
            }
          }
          
          if (currentSuggestion) suggestions.push(currentSuggestion);
        }
      } catch (error) {
        logger.error('LLM upsell generation failed, falling back to templates:', error);
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
    
    logger.info(`💰 Upsell suggestions generated: ${mode} mode`);
    
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
  } catch (error) {
    logger.error('❌ Upsell suggestion failed:', error);
    res.status(500).json({
      ok: false,
      error: 'Failed to generate upsell suggestions'
    });
  }
});

// Legacy build endpoint for backward compatibility
app.post('/api/v1/build', (req, res) => {
  logger.warn('⚠️ Legacy /build endpoint accessed - deprecated');
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
    logger.info(`Server running on port ${PORT}`);
    logger.info(`Mode: ${cfg.MODE}`);
    logger.info(`Health check: http://localhost:${PORT}/api/v1/health`);
  });
}

export default app;