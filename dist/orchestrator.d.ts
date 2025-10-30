import { GenRequest } from './types';
interface GenerationResult {
    jobId: string;
    style: string;
    images: {
        url: string;
        seed: number;
    }[];
    metrics: {
        duration: number;
        count: number;
        totalSize: number;
    };
}
/**
 * Run image generation orchestration flow
 */
export declare function runGen(req: GenRequest): Promise<GenerationResult>;
export {};
//# sourceMappingURL=orchestrator.d.ts.map