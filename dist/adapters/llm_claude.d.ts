/**
 * Claude Adapter - Anthropic Claude integration for LLM brain
 * Uses the latest claude-sonnet-4-20250514 model via HTTP API
 */
import { LLMAdapter, LLMRequest, LLMResponse } from './llm_client';
export declare class ClaudeAdapter implements LLMAdapter {
    private apiKey;
    private model;
    private maxTokens;
    constructor();
    isLive(): boolean;
    ask(request: LLMRequest): Promise<LLMResponse>;
}
//# sourceMappingURL=llm_claude.d.ts.map