"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.send = send;
const crypto_1 = __importDefault(require("crypto"));
const config_1 = require("./config");
const log_1 = require("./log");
/**
 * Send notification with HMAC signature
 */
async function send(payload) {
    log_1.logger.info(`📢 Sending notification for job ${payload.job_id}`);
    try {
        // Create full payload with signature
        const body = JSON.stringify(payload);
        const signature = crypto_1.default
            .createHmac('sha256', config_1.cfg.HMAC_SECRET)
            .update(body)
            .digest('hex');
        const fullPayload = {
            ...payload,
            signature
        };
        if (config_1.cfg.NOTIFY_WEBHOOK) {
            log_1.logger.info(`🌐 Posting notification to webhook: ${config_1.cfg.NOTIFY_WEBHOOK}`);
            // Use dynamic import for fetch to handle both Node versions
            const fetch = (await Promise.resolve().then(() => __importStar(require('node-fetch')))).default;
            const response = await fetch(config_1.cfg.NOTIFY_WEBHOOK, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Signature': signature
                },
                body: JSON.stringify(fullPayload)
            });
            if (response.ok) {
                log_1.logger.info(`✅ Notification sent successfully (${response.status})`);
            }
            else {
                log_1.logger.warn(`⚠️ Webhook responded with ${response.status}: ${response.statusText}`);
            }
        }
        else {
            log_1.logger.info('📝 No NOTIFY_WEBHOOK configured, logging notification payload:');
            console.log('=== NOTIFICATION PAYLOAD ===');
            console.log(JSON.stringify(fullPayload, null, 2));
            console.log('=== END NOTIFICATION ===');
        }
        return { ok: true };
    }
    catch (error) {
        log_1.logger.error('❌ Failed to send notification:', error);
        return { ok: true }; // Always return ok: true as specified
    }
}
//# sourceMappingURL=notify.js.map