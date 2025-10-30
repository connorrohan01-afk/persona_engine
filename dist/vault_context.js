"use strict";
/**
 * Vault Context Utilities
 * Provides persona and manifest loading from vault directory structure
 */
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadPersona = loadPersona;
exports.loadManifest = loadManifest;
exports.summarizeManifest = summarizeManifest;
exports.buildVaultContext = buildVaultContext;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
// ============================================================================
// Persona Loading
// ============================================================================
/**
 * Load persona data from vault directory
 * Checks both regular and system persona locations
 */
function loadPersona(persona_id) {
    if (!persona_id) {
        return null;
    }
    // Try regular persona location first
    let personaPath = path.join(process.cwd(), 'vault', 'dev', 'personas', `${persona_id}.json`);
    if (!fs.existsSync(personaPath)) {
        // Try system persona location
        personaPath = path.join(process.cwd(), 'vault', 'dev', 'personas', 'system', `${persona_id}.json`);
    }
    if (!fs.existsSync(personaPath)) {
        console.warn(`Persona not found: ${persona_id}`);
        return null;
    }
    try {
        const content = fs.readFileSync(personaPath, 'utf8');
        const data = JSON.parse(content);
        return {
            id: data.id || persona_id,
            name: data.name || '',
            traits: Array.isArray(data.traits) ? data.traits : []
        };
    }
    catch (error) {
        console.warn(`Failed to load persona ${persona_id}:`, error);
        return null;
    }
}
// ============================================================================
// Manifest Loading
// ============================================================================
/**
 * Load job manifest from vault directory
 */
function loadManifest(persona_id, job_id, style) {
    if (!persona_id || !job_id || !style) {
        return null;
    }
    const manifestPath = path.join(process.cwd(), 'vault', 'dev', persona_id, job_id, style, 'manifest_job.json');
    if (!fs.existsSync(manifestPath)) {
        console.warn(`Manifest not found: ${manifestPath}`);
        return null;
    }
    try {
        const content = fs.readFileSync(manifestPath, 'utf8');
        return JSON.parse(content);
    }
    catch (error) {
        console.warn(`Failed to load manifest ${manifestPath}:`, error);
        return null;
    }
}
// ============================================================================
// Manifest Summarization
// ============================================================================
/**
 * Summarize manifest into structured format
 */
function summarizeManifest(manifest) {
    if (!manifest) {
        return null;
    }
    try {
        // Extract style
        const style = manifest.style || 'unknown';
        // Extract created_at
        const created_at = manifest.created_at || '';
        // Extract image data and build files/seeds arrays
        let files = [];
        let seeds = [];
        let count = 0;
        // Handle different manifest formats
        if (Array.isArray(manifest.images)) {
            // Format: {images: [{seed: X, file: "name.jpg"}, ...]}
            manifest.images.forEach(img => {
                if (img.seed !== undefined) {
                    seeds.push(img.seed);
                }
                if (img.file) {
                    files.push(img.file);
                }
                else if (img.filename) {
                    files.push(img.filename);
                }
            });
            count = manifest.images.length;
        }
        else if (Array.isArray(manifest.files)) {
            // Format: {files: ["file1.jpg", "file2.jpg", ...]}
            files = [...manifest.files];
            count = files.length;
            // Try to extract seeds from other properties
            if (Array.isArray(manifest.seeds)) {
                seeds = [...manifest.seeds];
            }
        }
        else {
            // Scan for numeric properties that might be seeds
            Object.keys(manifest).forEach(key => {
                if (key.includes('seed') && typeof manifest[key] === 'number') {
                    seeds.push(manifest[key]);
                }
            });
            // Count from other indicators
            count = seeds.length || Object.keys(manifest).filter(k => k.includes('image')).length || 0;
        }
        return {
            style,
            count,
            seeds,
            created_at,
            files
        };
    }
    catch (error) {
        console.warn('Failed to summarize manifest:', error);
        return null;
    }
}
// ============================================================================
// Combined Context Builder
// ============================================================================
/**
 * Build complete context for brain/upsell requests
 */
function buildVaultContext(persona_id, job_id, style) {
    const context = {};
    // Load persona if provided
    if (persona_id) {
        const persona = loadPersona(persona_id);
        if (persona) {
            context.persona = persona;
        }
    }
    // Load and summarize manifest if all parameters provided
    if (persona_id && job_id && style) {
        const manifest = loadManifest(persona_id, job_id, style);
        const summary = summarizeManifest(manifest);
        if (summary) {
            context.manifest_summary = summary;
        }
    }
    return context;
}
//# sourceMappingURL=vault_context.js.map