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
export declare function getLLMClient(): LLMAdapter;
/**
 * Create system prompt for studio brain with persona context
 */
export declare function createSystemPrompt(persona_traits?: string[]): string;
/**
 * Create system prompt for upsell suggestions with persona context
 */
export declare function createUpsellSystemPrompt(persona_traits?: string[]): string;
//# sourceMappingURL=llm_client.d.ts.map