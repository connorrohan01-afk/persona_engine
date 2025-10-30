/**
 * Fake LLM Adapter - Deterministic responses for development/testing
 */
import { LLMAdapter, LLMRequest, LLMResponse } from './llm_client';
export declare class FakeAdapter implements LLMAdapter {
    isLive(): boolean;
    ask(request: LLMRequest): Promise<LLMResponse>;
    private generateFakeAnswer;
}
//# sourceMappingURL=llm_fake.d.ts.map