import { NotifyPayload } from './types';
/**
 * Send notification with HMAC signature
 */
export declare function send(payload: Omit<NotifyPayload, 'signature'>): Promise<{
    ok: boolean;
}>;
//# sourceMappingURL=notify.d.ts.map