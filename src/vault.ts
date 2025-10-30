import { promises as fs } from 'fs';
import path from 'path';
import { logger } from './log';

const VAULT_ROOT = path.join(process.cwd(), 'vault', 'dev');

interface ManifestData {
  persona_id: string;
  job_id: string;
  style: string;
  count: number;
  seeds?: number[];
  created_at: string;
  [key: string]: any;
}

/**
 * Ensures persona directory exists and returns its path
 */
export async function ensurePersona(personaId: string): Promise<string> {
  const personaDir = path.join(VAULT_ROOT, personaId);
  
  try {
    await fs.mkdir(personaDir, { recursive: true });
    logger.info(`Ensured persona directory: ${personaDir}`);
    return personaDir;
  } catch (error) {
    logger.error(`Failed to create persona directory ${personaDir}:`, error);
    throw error;
  }
}

/**
 * Creates a new job directory with padded job ID (J0001, J0002, etc.)
 */
export async function newJob(personaId: string, style: string): Promise<{ jobId: string; jobDir: string; styleDir: string }> {
  const personaDir = await ensurePersona(personaId);
  
  // Find next available job ID by checking existing directories
  const existingJobs = await getExistingJobIds(personaDir);
  const nextJobNumber = Math.max(0, ...existingJobs.map(id => parseInt(id.substring(1)) || 0)) + 1;
  const jobId = `J${nextJobNumber.toString().padStart(4, '0')}`;
  
  const jobDir = path.join(personaDir, jobId);
  const styleDir = path.join(jobDir, style);
  
  try {
    await fs.mkdir(styleDir, { recursive: true });
    logger.info(`Created job directory: ${styleDir}`);
    return { jobId, jobDir, styleDir };
  } catch (error) {
    logger.error(`Failed to create job directory ${styleDir}:`, error);
    throw error;
  }
}

/**
 * Saves image bytes to the style directory with indexed filename
 */
export async function saveImage(styleDir: string, idx: number, bytes: Buffer): Promise<string> {
  const filename = `image_${idx.toString().padStart(3, '0')}.jpg`;
  const absolutePath = path.join(styleDir, filename);
  
  try {
    await fs.writeFile(absolutePath, bytes);
    logger.info(`Saved image: ${absolutePath}`);
    return absolutePath;
  } catch (error) {
    logger.error(`Failed to save image ${absolutePath}:`, error);
    throw error;
  }
}

/**
 * Writes manifest file to the style directory
 */
export async function writeManifest(styleDir: string, data: ManifestData): Promise<void> {
  const manifestPath = path.join(styleDir, 'manifest_job.json');
  
  const manifestData = {
    ...data,
    persona_id: data.persona_id,
    job_id: data.job_id,
    style: data.style,
    count: data.count,
    seeds: data.seeds || [],
    created_at: data.created_at || new Date().toISOString()
  };
  
  try {
    await fs.writeFile(manifestPath, JSON.stringify(manifestData, null, 2));
    logger.info(`Wrote manifest: ${manifestPath}`);
  } catch (error) {
    logger.error(`Failed to write manifest ${manifestPath}:`, error);
    throw error;
  }
}

/**
 * Returns vault link (currently returns local path)
 */
export function getVaultLink(personaId: string, jobId: string, style: string): string {
  return path.join(VAULT_ROOT, personaId, jobId, style);
}

/**
 * Helper function to get existing job IDs from persona directory
 */
async function getExistingJobIds(personaDir: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(personaDir, { withFileTypes: true });
    return entries
      .filter(entry => entry.isDirectory() && entry.name.startsWith('J'))
      .map(entry => entry.name);
  } catch (error) {
    // Directory doesn't exist yet, return empty array
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return [];
    }
    throw error;
  }
}