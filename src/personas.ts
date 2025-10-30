import { promises as fs } from 'fs';
import path from 'path';
import { Persona } from './types';
import { logger } from './log';

const DATA_DIR = path.join(process.cwd(), 'data');
const PERSONAS_FILE = path.join(DATA_DIR, 'personas.json');

interface CreatePersonaRequest {
  name: string;
  traits: string[];
  refs?: string[];
}

/**
 * Ensure data directory exists
 */
async function ensureDataDir(): Promise<void> {
  try {
    await fs.mkdir(DATA_DIR, { recursive: true });
  } catch (error) {
    logger.error('Failed to create data directory:', error);
    throw error;
  }
}

/**
 * Load personas from JSON file
 */
async function loadPersonas(): Promise<Persona[]> {
  try {
    await ensureDataDir();
    const data = await fs.readFile(PERSONAS_FILE, 'utf-8');
    const personas = JSON.parse(data);
    return Array.isArray(personas) ? personas : [];
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      // File doesn't exist, return empty array
      return [];
    }
    logger.error('Failed to load personas:', error);
    throw error;
  }
}

/**
 * Save personas to JSON file
 */
async function savePersonas(personas: Persona[]): Promise<void> {
  try {
    await ensureDataDir();
    await fs.writeFile(PERSONAS_FILE, JSON.stringify(personas, null, 2));
    logger.info(`Saved ${personas.length} personas to ${PERSONAS_FILE}`);
  } catch (error) {
    logger.error('Failed to save personas:', error);
    throw error;
  }
}

/**
 * Generate next persona ID (P0001, P0002, etc.)
 */
function generatePersonaId(existingPersonas: Persona[]): string {
  const existingIds = existingPersonas.map(p => p.id);
  const numbers = existingIds
    .filter(id => id.startsWith('P') && /^P\d{4}$/.test(id))
    .map(id => parseInt(id.substring(1)))
    .filter(num => !isNaN(num));
  
  const maxNumber = numbers.length > 0 ? Math.max(...numbers) : 0;
  const nextNumber = maxNumber + 1;
  
  return `P${nextNumber.toString().padStart(4, '0')}`;
}

/**
 * Create a new persona with auto-generated ID
 */
export async function createPersona(request: CreatePersonaRequest): Promise<Persona> {
  logger.info(`Creating new persona: ${request.name}`);
  
  const personas = await loadPersonas();
  const id = generatePersonaId(personas);
  
  const newPersona: Persona = {
    id,
    name: request.name,
    traits: request.traits,
    refs: request.refs
  };
  
  personas.push(newPersona);
  await savePersonas(personas);
  
  logger.info(`Created persona ${id}: ${request.name} with ${request.traits.length} traits`);
  return newPersona;
}

/**
 * Get a persona by ID
 */
export async function getPersona(id: string): Promise<Persona | null> {
  logger.info(`Looking up persona: ${id}`);
  
  const personas = await loadPersonas();
  const persona = personas.find(p => p.id === id) || null;
  
  if (persona) {
    logger.info(`Found persona ${id}: ${persona.name}`);
  } else {
    logger.info(`Persona ${id} not found`);
  }
  
  return persona;
}

/**
 * List all personas
 */
export async function listPersonas(): Promise<Persona[]> {
  logger.info('Loading all personas');
  
  const personas = await loadPersonas();
  logger.info(`Loaded ${personas.length} personas`);
  
  return personas;
}

/**
 * Delete a persona by ID (utility function)
 */
export async function deletePersona(id: string): Promise<boolean> {
  logger.info(`Deleting persona: ${id}`);
  
  const personas = await loadPersonas();
  const initialLength = personas.length;
  const filteredPersonas = personas.filter(p => p.id !== id);
  
  if (filteredPersonas.length < initialLength) {
    await savePersonas(filteredPersonas);
    logger.info(`Deleted persona ${id}`);
    return true;
  } else {
    logger.info(`Persona ${id} not found for deletion`);
    return false;
  }
}