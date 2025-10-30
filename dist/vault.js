"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ensurePersona = ensurePersona;
exports.newJob = newJob;
exports.saveImage = saveImage;
exports.writeManifest = writeManifest;
exports.getVaultLink = getVaultLink;
const fs_1 = require("fs");
const path_1 = __importDefault(require("path"));
const log_1 = require("./log");
const VAULT_ROOT = path_1.default.join(process.cwd(), 'vault', 'dev');
/**
 * Ensures persona directory exists and returns its path
 */
async function ensurePersona(personaId) {
    const personaDir = path_1.default.join(VAULT_ROOT, personaId);
    try {
        await fs_1.promises.mkdir(personaDir, { recursive: true });
        log_1.logger.info(`Ensured persona directory: ${personaDir}`);
        return personaDir;
    }
    catch (error) {
        log_1.logger.error(`Failed to create persona directory ${personaDir}:`, error);
        throw error;
    }
}
/**
 * Creates a new job directory with padded job ID (J0001, J0002, etc.)
 */
async function newJob(personaId, style) {
    const personaDir = await ensurePersona(personaId);
    // Find next available job ID by checking existing directories
    const existingJobs = await getExistingJobIds(personaDir);
    const nextJobNumber = Math.max(0, ...existingJobs.map(id => parseInt(id.substring(1)) || 0)) + 1;
    const jobId = `J${nextJobNumber.toString().padStart(4, '0')}`;
    const jobDir = path_1.default.join(personaDir, jobId);
    const styleDir = path_1.default.join(jobDir, style);
    try {
        await fs_1.promises.mkdir(styleDir, { recursive: true });
        log_1.logger.info(`Created job directory: ${styleDir}`);
        return { jobId, jobDir, styleDir };
    }
    catch (error) {
        log_1.logger.error(`Failed to create job directory ${styleDir}:`, error);
        throw error;
    }
}
/**
 * Saves image bytes to the style directory with indexed filename
 */
async function saveImage(styleDir, idx, bytes) {
    const filename = `image_${idx.toString().padStart(3, '0')}.jpg`;
    const absolutePath = path_1.default.join(styleDir, filename);
    try {
        await fs_1.promises.writeFile(absolutePath, bytes);
        log_1.logger.info(`Saved image: ${absolutePath}`);
        return absolutePath;
    }
    catch (error) {
        log_1.logger.error(`Failed to save image ${absolutePath}:`, error);
        throw error;
    }
}
/**
 * Writes manifest file to the style directory
 */
async function writeManifest(styleDir, data) {
    const manifestPath = path_1.default.join(styleDir, 'manifest_job.json');
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
        await fs_1.promises.writeFile(manifestPath, JSON.stringify(manifestData, null, 2));
        log_1.logger.info(`Wrote manifest: ${manifestPath}`);
    }
    catch (error) {
        log_1.logger.error(`Failed to write manifest ${manifestPath}:`, error);
        throw error;
    }
}
/**
 * Returns vault link (currently returns local path)
 */
function getVaultLink(personaId, jobId, style) {
    return path_1.default.join(VAULT_ROOT, personaId, jobId, style);
}
/**
 * Helper function to get existing job IDs from persona directory
 */
async function getExistingJobIds(personaDir) {
    try {
        const entries = await fs_1.promises.readdir(personaDir, { withFileTypes: true });
        return entries
            .filter(entry => entry.isDirectory() && entry.name.startsWith('J'))
            .map(entry => entry.name);
    }
    catch (error) {
        // Directory doesn't exist yet, return empty array
        if (error.code === 'ENOENT') {
            return [];
        }
        throw error;
    }
}
//# sourceMappingURL=vault.js.map