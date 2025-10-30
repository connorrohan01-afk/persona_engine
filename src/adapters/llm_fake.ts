/**
 * Fake LLM Adapter - Deterministic responses for development/testing
 */

import { LLMAdapter, LLMRequest, LLMResponse, createSystemPrompt, createUpsellSystemPrompt } from './llm_client';

export class FakeAdapter implements LLMAdapter {
  
  isLive(): boolean {
    return false;
  }

  async ask(request: LLMRequest): Promise<LLMResponse> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));

    // Generate deterministic fake response based on question content
    let answer = this.generateFakeAnswer(request);

    // Add persona context if available
    if (request.persona_traits && request.persona_traits.length > 0) {
      answer += ` (This persona has traits: ${request.persona_traits.join(', ')})`;
    }

    return {
      ok: true,
      mode: "fake",
      answer,
      tokens_used: Math.floor(answer.length / 4) // Rough token estimate
    };
  }

  private generateFakeAnswer(request: LLMRequest): string {
    const question = request.question.toLowerCase();
    
    // Pattern-based fake responses
    if (question.includes('manifest') || question.includes('job')) {
      return `Based on the fake data, the latest job manifest contains 6 studio images with seeds ranging from 331035 to 589352. The generation used a "red dress, playful mood, loft setting" configuration with DPM++ 2M Karras sampler.`;
    }
    
    if (question.includes('persona') || question.includes('traits')) {
      return `This persona appears to be designed for ${request.persona_traits?.[0] || 'creative'} content generation. The traits suggest a focus on editorial and warm styling approaches.`;
    }
    
    if (question.includes('style') || question.includes('studio')) {
      return `The studio style is optimized for professional portrait generation with controlled lighting and composition. It uses 25 steps with CFG 7 for balanced quality and creativity.`;
    }
    
    if (question.includes('vault') || question.includes('images')) {
      return `The vault system organizes generated content in a structured hierarchy: /vault/dev/{persona_id}/{job_id}/{style}/. Each job includes images and a complete manifest with metadata.`;
    }
    
    // Default response with question echo
    return `I'm running in fake mode, so this is a simulated response to: "${request.question}". In live mode, I would provide detailed insights about your PersonaEngine projects using Claude AI.`;
  }
}