/**
 * LLM Client Facade - Clean abstraction layer for language model providers
 */

export interface LLMRequest {
  question: string;
  persona_traits?: string[];
  context?: Record<string, any>;
  max_tokens?: number;
}

export interface LLMResponse {
  ok: boolean;
  mode: "live" | "fake";
  answer: string;
  tokens_used?: number;
  error?: string;
}

export interface LLMAdapter {
  ask(request: LLMRequest): Promise<LLMResponse>;
  isLive(): boolean;
}

/**
 * Get the appropriate LLM client based on environment configuration
 */
export function getLLMClient(): LLMAdapter {
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

import * as fs from 'fs';
import * as path from 'path';

/**
 * Load prompt template from file
 */
function loadPromptTemplate(templateName: string): string {
  try {
    const templatePath = path.join(process.cwd(), 'prompts', `${templateName}.txt`);
    return fs.readFileSync(templatePath, 'utf8').trim();
  } catch (error) {
    console.warn(`Failed to load prompt template ${templateName}, using fallback`);
    return getFallbackPrompt(templateName);
  }
}

/**
 * Fallback prompts if template files not found
 */
function getFallbackPrompt(templateName: string): string {
  const fallbacks: Record<string, string> = {
    'brain_system': 'You are Studio Brain: a concise production assistant. Use persona traits if given. Answer in <=120 words, bullet where helpful. If asked about vault data, summarize from provided context only; never invent.',
    'upsell_system': 'You are GBT, a friendly upsell assistant for a photo studio. Given persona traits and job manifest (style, count, created_at), propose 3 tailored offers. Each: title (max 6 words), 1-sentence copy, CTA verb, optional price_hint.'
  };
  
  return fallbacks[templateName] || 'You are a helpful AI assistant.';
}

/**
 * Create system prompt for studio brain with persona context
 */
export function createSystemPrompt(persona_traits?: string[]): string {
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
export function createUpsellSystemPrompt(persona_traits?: string[]): string {
  const template = loadPromptTemplate('upsell_system');
  
  let prompt = template;
  
  if (persona_traits && persona_traits.length > 0) {
    prompt += `\nPersona: ${persona_traits.join(', ')}`;
  }

  return prompt;
}