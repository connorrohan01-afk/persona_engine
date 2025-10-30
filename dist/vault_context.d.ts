/**
 * Vault Context Utilities
 * Provides persona and manifest loading from vault directory structure
 */
export interface PersonaData {
    id: string;
    name: string;
    traits: string[];
}
export interface ManifestSummary {
    style: string;
    count: number;
    seeds: number[];
    created_at: string;
    files: string[];
}
export interface RawManifest {
    style?: string;
    created_at?: string;
    images?: Array<{
        seed?: number;
        file?: string;
        filename?: string;
    }>;
    files?: string[];
    [key: string]: any;
}
/**
 * Load persona data from vault directory
 * Checks both regular and system persona locations
 */
export declare function loadPersona(persona_id: string): PersonaData | null;
/**
 * Load job manifest from vault directory
 */
export declare function loadManifest(persona_id: string, job_id: string, style: string): RawManifest | null;
/**
 * Summarize manifest into structured format
 */
export declare function summarizeManifest(manifest: RawManifest | null): ManifestSummary | null;
/**
 * Build complete context for brain/upsell requests
 */
export declare function buildVaultContext(persona_id?: string, job_id?: string, style?: string): {
    persona?: PersonaData;
    manifest_summary?: ManifestSummary;
};
//# sourceMappingURL=vault_context.d.ts.map