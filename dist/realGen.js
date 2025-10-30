"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.genTxt2Img = genTxt2Img;
exports.upscale = upscale;
exports.face = face;
const config_1 = require("./config");
const log_1 = require("./log");
/**
 * Real text-to-image generation (placeholder)
 */
async function genTxt2Img(params) {
    log_1.logger.info(`🎨 Real text-to-image generation requested for ${params.count} images`);
    if (config_1.cfg.MODE !== "real") {
        throw new Error('NOT_CONFIGURED: MODE must be "real" for real image generation');
    }
    if (!config_1.cfg.IMG_API_KEY) {
        throw new Error('NOT_CONFIGURED: IMG_API_KEY is required for real image generation');
    }
    // TODO: Implement actual image generation API calls
    throw new Error('NOT_CONFIGURED: Real image generation not yet implemented');
}
/**
 * Real image upscaling (placeholder)
 */
async function upscale(buffer) {
    log_1.logger.info(`🔍 Real upscaling requested for image buffer (${buffer.length} bytes)`);
    if (config_1.cfg.MODE !== "real") {
        throw new Error('NOT_CONFIGURED: MODE must be "real" for real image upscaling');
    }
    if (!config_1.cfg.IMG_API_KEY) {
        throw new Error('NOT_CONFIGURED: IMG_API_KEY is required for real image upscaling');
    }
    // TODO: Implement actual upscaling API calls
    throw new Error('NOT_CONFIGURED: Real image upscaling not yet implemented');
}
/**
 * Real face enhancement (placeholder)
 */
async function face(buffer) {
    log_1.logger.info(`👤 Real face enhancement requested for image buffer (${buffer.length} bytes)`);
    if (config_1.cfg.MODE !== "real") {
        throw new Error('NOT_CONFIGURED: MODE must be "real" for real face enhancement');
    }
    if (!config_1.cfg.IMG_API_KEY) {
        throw new Error('NOT_CONFIGURED: IMG_API_KEY is required for real face enhancement');
    }
    // TODO: Implement actual face enhancement API calls
    throw new Error('NOT_CONFIGURED: Real face enhancement not yet implemented');
}
//# sourceMappingURL=realGen.js.map