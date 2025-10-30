"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.upscale = upscale;
exports.face = face;
const log_1 = require("./log");
/**
 * Fake upscaling - returns the same buffer unchanged
 */
async function upscale(b) {
    log_1.logger.info(`🔍 Fake upscaling image buffer (${b.length} bytes)`);
    // Simulate some processing time
    await new Promise(resolve => setTimeout(resolve, 100));
    log_1.logger.info(`✨ Fake upscale complete - "enhanced" ${b.length} bytes`);
    return b;
}
/**
 * Fake face enhancement - returns the same buffer unchanged
 */
async function face(b) {
    log_1.logger.info(`👤 Fake face enhancement on image buffer (${b.length} bytes)`);
    // Simulate some processing time
    await new Promise(resolve => setTimeout(resolve, 150));
    log_1.logger.info(`✨ Fake face enhancement complete - "beautified" ${b.length} bytes`);
    return b;
}
//# sourceMappingURL=fakePolish.js.map