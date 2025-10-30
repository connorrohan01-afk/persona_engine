/**
 * Vault Context Utilities
 * Provides persona and manifest loading from vault directory structure
 */

import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// Type Definitions
// ============================================================================

export interface PersonaData {
  id: string;
  name: string;
  traits: string[];
}

export interface ManifestSummary {
  style: string;
  count: number;
  seeds: number[];
  created_at: string;
  files: string[];
}

export interface RawManifest {
  style?: string;
  created_at?: string;
  images?: Array<{
    seed?: number;
    file?: string;
    filename?: string;
  }>;
  files?: string[];
  // Allow for various manifest formats
  [key: string]: any;
}

// ============================================================================
// Persona Loading
// ============================================================================

/**
 * Load persona data from vault directory
 * Checks both regular and system persona locations
 */
export function loadPersona(persona_id: string): PersonaData | null {
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
  } catch (error) {
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
export function loadManifest(persona_id: string, job_id: string, style: string): RawManifest | null {
  if (!persona_id || !job_id || !style) {
    return null;
  }

  const manifestPath = path.join(
    process.cwd(), 
    'vault', 
    'dev', 
    persona_id, 
    job_id, 
    style, 
    'manifest_job.json'
  );

  if (!fs.existsSync(manifestPath)) {
    console.warn(`Manifest not found: ${manifestPath}`);
    return null;
  }

  try {
    const content = fs.readFileSync(manifestPath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
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
export function summarizeManifest(manifest: RawManifest | null): ManifestSummary | null {
  if (!manifest) {
    return null;
  }

  try {
    // Extract style
    const style = manifest.style || 'unknown';
    
    // Extract created_at
    const created_at = manifest.created_at || '';
    
    // Extract image data and build files/seeds arrays
    let files: string[] = [];
    let seeds: number[] = [];
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
        } else if (img.filename) {
          files.push(img.filename);
        }
      });
      count = manifest.images.length;
    } else if (Array.isArray(manifest.files)) {
      // Format: {files: ["file1.jpg", "file2.jpg", ...]}
      files = [...manifest.files];
      count = files.length;
      
      // Try to extract seeds from other properties
      if (Array.isArray(manifest.seeds)) {
        seeds = [...manifest.seeds];
      }
    } else {
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
  } catch (error) {
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
export function buildVaultContext(persona_id?: string, job_id?: string, style?: string): {
  persona?: PersonaData;
  manifest_summary?: ManifestSummary;
} {
  const context: any = {};

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