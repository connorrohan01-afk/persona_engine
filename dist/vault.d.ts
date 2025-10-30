interface ManifestData {
    persona_id: string;
    job_id: string;
    style: string;
    count: number;
    seeds?: number[];
    created_at: string;
    [key: string]: any;
}
/**
 * Ensures persona directory exists and returns its path
 */
export declare function ensurePersona(personaId: string): Promise<string>;
/**
 * Creates a new job directory with padded job ID (J0001, J0002, etc.)
 */
export declare function newJob(personaId: string, style: string): Promise<{
    jobId: string;
    jobDir: string;
    styleDir: string;
}>;
/**
 * Saves image bytes to the style directory with indexed filename
 */
export declare function saveImage(styleDir: string, idx: number, bytes: Buffer): Promise<string>;
/**
 * Writes manifest file to the style directory
 */
export declare function writeManifest(styleDir: string, data: ManifestData): Promise<void>;
/**
 * Returns vault link (currently returns local path)
 */
export declare function getVaultLink(personaId: string, jobId: string, style: string): string;
export {};
//# sourceMappingURL=vault.d.ts.map