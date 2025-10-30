import crypto from 'crypto';
import { cfg } from './config';
import { logger } from './log';
import { NotifyPayload } from './types';

/**
 * Send notification with HMAC signature
 */
export async function send(payload: Omit<NotifyPayload, 'signature'>): Promise<{ ok: boolean }> {
  logger.info(`📢 Sending notification for job ${payload.job_id}`);
  
  try {
    // Create full payload with signature
    const body = JSON.stringify(payload);
    const signature = crypto
      .createHmac('sha256', cfg.HMAC_SECRET)
      .update(body)
      .digest('hex');
    
    const fullPayload: NotifyPayload = {
      ...payload,
      signature
    };
    
    if (cfg.NOTIFY_WEBHOOK) {
      logger.info(`🌐 Posting notification to webhook: ${cfg.NOTIFY_WEBHOOK}`);
      
      // Use dynamic import for fetch to handle both Node versions
      const fetch = (await import('node-fetch')).default;
      
      const response = await fetch(cfg.NOTIFY_WEBHOOK, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Signature': signature
        },
        body: JSON.stringify(fullPayload)
      });
      
      if (response.ok) {
        logger.info(`✅ Notification sent successfully (${response.status})`);
      } else {
        logger.warn(`⚠️ Webhook responded with ${response.status}: ${response.statusText}`);
      }
    } else {
      logger.info('📝 No NOTIFY_WEBHOOK configured, logging notification payload:');
      console.log('=== NOTIFICATION PAYLOAD ===');
      console.log(JSON.stringify(fullPayload, null, 2));
      console.log('=== END NOTIFICATION ===');
    }
    
    return { ok: true };
  } catch (error) {
    logger.error('❌ Failed to send notification:', error);
    return { ok: true }; // Always return ok: true as specified
  }
}