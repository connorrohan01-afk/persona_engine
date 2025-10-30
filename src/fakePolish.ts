import { logger } from './log';

/**
 * Fake upscaling - returns the same buffer unchanged
 */
export async function upscale(b: Buffer): Promise<Buffer> {
  logger.info(`🔍 Fake upscaling image buffer (${b.length} bytes)`);
  
  // Simulate some processing time
  await new Promise(resolve => setTimeout(resolve, 100));
  
  logger.info(`✨ Fake upscale complete - "enhanced" ${b.length} bytes`);
  return b;
}

/**
 * Fake face enhancement - returns the same buffer unchanged
 */
export async function face(b: Buffer): Promise<Buffer> {
  logger.info(`👤 Fake face enhancement on image buffer (${b.length} bytes)`);
  
  // Simulate some processing time
  await new Promise(resolve => setTimeout(resolve, 150));
  
  logger.info(`✨ Fake face enhancement complete - "beautified" ${b.length} bytes`);
  return b;
}