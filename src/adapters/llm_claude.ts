/**
 * Claude Adapter - Anthropic Claude integration for LLM brain
 * Uses the latest claude-sonnet-4-20250514 model via HTTP API
 */

import { LLMAdapter, LLMRequest, LLMResponse, createSystemPrompt, createUpsellSystemPrompt } from './llm_client';

export class ClaudeAdapter implements LLMAdapter {
  private apiKey: string;
  private model: string;
  private maxTokens: number;

  constructor() {
    this.apiKey = process.env.ANTHROPIC_API_KEY || '';
    // The newest Anthropic model is "claude-sonnet-4-20250514", not older 3.x models
    this.model = process.env.LLM_MODEL || "claude-sonnet-4-20250514";
    this.maxTokens = parseInt(process.env.LLM_MAXTOKENS || "512");

    if (!this.apiKey) {
      throw new Error('ANTHROPIC_API_KEY environment variable must be set');
    }
  }

  isLive(): boolean {
    return true;
  }

  async ask(request: LLMRequest): Promise<LLMResponse> {
    try {
      // Use different system prompts based on request context
      const isUpsellRequest = request.question.includes('Generate 3 concise upsell suggestions') || 
                             request.question.includes('propose 3 tailored offers');
      
      const systemPrompt = isUpsellRequest ? 
        createUpsellSystemPrompt(request.persona_traits) : 
        createSystemPrompt(request.persona_traits);
      
      const payload = {
        model: this.model,
        max_tokens: request.max_tokens || this.maxTokens,
        messages: [
          {
            role: "user",
            content: request.question
          }
        ],
        system: systemPrompt
      };

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.apiKey,
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Claude API error: ${response.status} ${errorText}`);
      }

      const data = await response.json() as any;
      
      // Extract answer from Claude response format and trim
      const rawAnswer = data.content?.[0]?.text || 'No response received from Claude';
      const answer = rawAnswer.trim();
      const tokensUsed = data.usage?.output_tokens || 0;

      return {
        ok: true,
        mode: "live",
        answer,
        tokens_used: tokensUsed
      };

    } catch (error) {
      console.error('Claude adapter error:', error);
      return {
        ok: false,
        mode: "live",
        answer: '',
        error: error instanceof Error ? error.message : 'Unknown Claude error'
      };
    }
  }
}