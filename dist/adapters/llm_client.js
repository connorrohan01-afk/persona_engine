"use strict";
/**
 * LLM Client Facade - Clean abstraction layer for language model providers
 */
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.getLLMClient = getLLMClient;
exports.createSystemPrompt = createSystemPrompt;
exports.createUpsellSystemPrompt = createUpsellSystemPrompt;
/**
 * Get the appropriate LLM client based on environment configuration
 */
function getLLMClient() {
    const provider = process.env.LLM_PROVIDER || "fake";
    const hasApiKey = !!process.env.ANTHROPIC_API_KEY;
    if (provider === "claude" && hasApiKey) {
        const { ClaudeAdapter } = require('./llm_claude');
        return new ClaudeAdapter();
    }
    // Default to fake adapter
    const { FakeAdapter } = require('./llm_fake');
    return new FakeAdapter();
}
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/**
 * Load prompt template from file
 */
function loadPromptTemplate(templateName) {
    try {
        const templatePath = path.join(process.cwd(), 'prompts', `${templateName}.txt`);
        return fs.readFileSync(templatePath, 'utf8').trim();
    }
    catch (error) {
        console.warn(`Failed to load prompt template ${templateName}, using fallback`);
        return getFallbackPrompt(templateName);
    }
}
/**
 * Fallback prompts if template files not found
 */
function getFallbackPrompt(templateName) {
    const fallbacks = {
        'brain_system': 'You are Studio Brain: a concise production assistant. Use persona traits if given. Answer in <=120 words, bullet where helpful. If asked about vault data, summarize from provided context only; never invent.',
        'upsell_system': 'You are GBT, a friendly upsell assistant for a photo studio. Given persona traits and job manifest (style, count, created_at), propose 3 tailored offers. Each: title (max 6 words), 1-sentence copy, CTA verb, optional price_hint.'
    };
    return fallbacks[templateName] || 'You are a helpful AI assistant.';
}
/**
 * Create system prompt for studio brain with persona context
 */
function createSystemPrompt(persona_traits) {
    const template = loadPromptTemplate('brain_system');
    let prompt = template;
    if (persona_traits && persona_traits.length > 0) {
        prompt += `\nPersona: ${persona_traits.join(', ')}`;
    }
    return prompt;
}
/**
 * Create system prompt for upsell suggestions with persona context
 */
function createUpsellSystemPrompt(persona_traits) {
    const template = loadPromptTemplate('upsell_system');
    let prompt = template;
    if (persona_traits && persona_traits.length > 0) {
        prompt += `\nPersona: ${persona_traits.join(', ')}`;
    }
    return prompt;
}
//# sourceMappingURL=llm_client.js.map