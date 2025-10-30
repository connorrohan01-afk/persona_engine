"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.runGen = runGen;
const personas_1 = require("./personas");
const vault_1 = require("./vault");
const styles_1 = require("./styles");
const fakeGen_1 = require("./fakeGen");
const fakePolish_1 = require("./fakePolish");
const realGen_1 = require("./realGen");
const config_1 = require("./config");
const log_1 = require("./log");
const path_1 = __importDefault(require("path"));
/**
 * Run image generation orchestration flow
 */
async function runGen(req) {
    const startTime = Date.now();
    log_1.logger.info(`🚀 Starting generation for persona ${req.persona_id}, style ${req.style}, count ${req.count}`);
    try {
        // Step 1: Validate persona_id
        log_1.logger.info(`📋 Step 1: Validating persona ${req.persona_id}`);
        const persona = await (0, personas_1.getPersona)(req.persona_id);
        if (!persona) {
            throw new Error(`Persona ${req.persona_id} not found`);
        }
        log_1.logger.info(`✅ Persona validated: ${persona.name}`);
        // Step 2: Create job via vault
        log_1.logger.info(`📁 Step 2: Creating job for style ${req.style}`);
        const { jobId, styleDir } = await (0, vault_1.newJob)(req.persona_id, req.style);
        log_1.logger.info(`✅ Job created: ${jobId} in ${styleDir}`);
        // Step 3: Build style configuration and merge slots
        log_1.logger.info(`🎨 Step 3: Building style configuration`);
        const styleConfig = (0, styles_1.getStyle)(req.style, req.tone, req.slots);
        log_1.logger.info(`✅ Style config: ${styleConfig.name} with ${styleConfig.negatives.length} negatives`);
        // Step 4: Generate and process images
        log_1.logger.info(`🖼️ Step 4: Generating ${req.count} images (mode: ${config_1.cfg.MODE})`);
        let generatedImages;
        if (config_1.cfg.MODE === "real") {
            log_1.logger.info(`🔄 Using real image generation`);
            // Convert style config to real generation parameters
            const genParams = {
                prompt: styleConfig.basePrompt,
                negativePrompt: styleConfig.negatives.join(', '),
                count: req.count,
                seed: req.seed,
                sampler: styleConfig.sampler,
                cfg_scale: styleConfig.cfg,
                steps: styleConfig.steps
            };
            generatedImages = await (0, realGen_1.genTxt2Img)(genParams);
        }
        else {
            log_1.logger.info(`🔄 Using fake image generation`);
            generatedImages = await (0, fakeGen_1.gen)(req.count, req.seed);
        }
        log_1.logger.info(`✅ Generated ${generatedImages.length} base images`);
        const processedImages = [];
        for (let i = 0; i < generatedImages.length; i++) {
            const { buffer, seed } = generatedImages[i];
            log_1.logger.info(`🔄 Processing image ${i + 1}/${generatedImages.length} (seed: ${seed})`);
            // Process through polish pipeline
            const upscaledBuffer = config_1.cfg.MODE === "real" ? await (0, realGen_1.upscale)(buffer) : await (0, fakePolish_1.upscale)(buffer);
            const enhancedBuffer = config_1.cfg.MODE === "real" ? await (0, realGen_1.face)(upscaledBuffer) : await (0, fakePolish_1.face)(upscaledBuffer);
            // Save to vault
            const imagePath = await (0, vault_1.saveImage)(styleDir, i + 1, enhancedBuffer);
            // Convert to file:// URL
            const imageUrl = `file://${path_1.default.resolve(imagePath)}`;
            processedImages.push({
                url: imageUrl,
                seed: seed,
                size: enhancedBuffer.length
            });
            log_1.logger.info(`✅ Saved image ${i + 1}: ${imagePath} (${enhancedBuffer.length} bytes)`);
        }
        // Step 5: Write manifest
        log_1.logger.info(`📄 Step 5: Writing manifest`);
        const manifestData = {
            persona_id: req.persona_id,
            job_id: jobId,
            style: req.style,
            count: req.count,
            seeds: processedImages.map(img => img.seed),
            tone: req.tone,
            slots: req.slots,
            styleConfig: {
                name: styleConfig.name,
                sampler: styleConfig.sampler,
                cfg: styleConfig.cfg,
                steps: styleConfig.steps
            },
            images: processedImages.map(img => ({
                url: img.url,
                seed: img.seed,
                size: img.size
            })),
            created_at: new Date().toISOString()
        };
        await (0, vault_1.writeManifest)(styleDir, manifestData);
        log_1.logger.info(`✅ Manifest written`);
        // Step 6: Calculate metrics and return result
        const endTime = Date.now();
        const duration = endTime - startTime;
        const totalSize = processedImages.reduce((sum, img) => sum + img.size, 0);
        const result = {
            jobId,
            style: req.style,
            images: processedImages.map(img => ({ url: img.url, seed: img.seed })),
            metrics: {
                duration,
                count: processedImages.length,
                totalSize
            }
        };
        log_1.logger.info(`🎉 Generation complete! Job ${jobId}: ${result.images.length} images in ${duration}ms (${totalSize} bytes total)`);
        return result;
    }
    catch (error) {
        const duration = Date.now() - startTime;
        log_1.logger.error(`❌ Generation failed after ${duration}ms:`, error);
        throw error;
    }
}
//# sourceMappingURL=orchestrator.js.map