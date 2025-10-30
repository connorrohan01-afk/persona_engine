"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.gen = gen;
const log_1 = require("./log");
/**
 * Generates fake images as small PNG buffers with random seeds
 */
async function gen(count, seed) {
    log_1.logger.info(`🎨 Fake generating ${count} images${seed ? ` with seed ${seed}` : ''}`);
    const results = [];
    for (let i = 0; i < count; i++) {
        // Generate a random seed if not provided, or use provided seed + increment
        const imageSeed = seed ? seed + i : Math.floor(Math.random() * 1000000);
        // Create a minimal 1x1 PNG buffer (base64 encoded then converted to buffer)
        // This is a valid 1x1 transparent PNG
        const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
        const buffer = Buffer.from(pngBase64, 'base64');
        results.push({ buffer, seed: imageSeed });
        log_1.logger.info(`📸 Generated fake image ${i + 1}/${count} with seed ${imageSeed}`);
    }
    log_1.logger.info(`✅ Fake generation complete: ${count} images generated`);
    return results;
}
//# sourceMappingURL=fakeGen.js.map