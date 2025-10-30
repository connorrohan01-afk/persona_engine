interface StyleConfig {
    name: string;
    basePrompt: string;
    negatives: string[];
    sampler: string;
    cfg: number;
    steps: number;
}
interface StyleSlots {
    outfit?: string;
    mood?: string;
    setting?: string;
}
/**
 * Get style configuration with optional tone modification and slot replacement
 */
export declare function getStyle(style: string, tone?: string, slots?: StyleSlots): StyleConfig;
/**
 * Get list of available styles
 */
export declare function getAvailableStyles(): string[];
/**
 * Get style info without processing
 */
export declare function getStyleInfo(style: string): StyleConfig | null;
export {};
//# sourceMappingURL=styles.d.ts.map