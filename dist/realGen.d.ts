interface GenTxt2ImgParams {
    prompt: string;
    negativePrompt?: string;
    count: number;
    seed?: number;
    width?: number;
    height?: number;
    sampler?: string;
    cfg_scale?: number;
    steps?: number;
}
interface GenTxt2ImgResult {
    buffer: Buffer;
    seed: number;
}
/**
 * Real text-to-image generation (placeholder)
 */
export declare function genTxt2Img(params: GenTxt2ImgParams): Promise<GenTxt2ImgResult[]>;
/**
 * Real image upscaling (placeholder)
 */
export declare function upscale(buffer: Buffer): Promise<Buffer>;
/**
 * Real face enhancement (placeholder)
 */
export declare function face(buffer: Buffer): Promise<Buffer>;
export {};
//# sourceMappingURL=realGen.d.ts.map