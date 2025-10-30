"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cfg = void 0;
exports.cfg = {
    MODE: process.env.MODE || "fake",
    IMG_API_BASE: process.env.IMG_API_BASE,
    IMG_API_KEY: process.env.IMG_API_KEY,
    NOTIFY_WEBHOOK: process.env.NOTIFY_WEBHOOK,
    HMAC_SECRET: process.env.HMAC_SECRET || "fake-hmac-secret-placeholder-change-in-production"
};
exports.default = exports.cfg;
//# sourceMappingURL=config.js.map