"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createPersona = createPersona;
exports.getPersona = getPersona;
exports.listPersonas = listPersonas;
exports.deletePersona = deletePersona;
const fs_1 = require("fs");
const path_1 = __importDefault(require("path"));
const log_1 = require("./log");
const DATA_DIR = path_1.default.join(process.cwd(), 'data');
const PERSONAS_FILE = path_1.default.join(DATA_DIR, 'personas.json');
/**
 * Ensure data directory exists
 */
async function ensureDataDir() {
    try {
        await fs_1.promises.mkdir(DATA_DIR, { recursive: true });
    }
    catch (error) {
        log_1.logger.error('Failed to create data directory:', error);
        throw error;
    }
}
/**
 * Load personas from JSON file
 */
async function loadPersonas() {
    try {
        await ensureDataDir();
        const data = await fs_1.promises.readFile(PERSONAS_FILE, 'utf-8');
        const personas = JSON.parse(data);
        return Array.isArray(personas) ? personas : [];
    }
    catch (error) {
        if (error.code === 'ENOENT') {
            // File doesn't exist, return empty array
            return [];
        }
        log_1.logger.error('Failed to load personas:', error);
        throw error;
    }
}
/**
 * Save personas to JSON file
 */
async function savePersonas(personas) {
    try {
        await ensureDataDir();
        await fs_1.promises.writeFile(PERSONAS_FILE, JSON.stringify(personas, null, 2));
        log_1.logger.info(`Saved ${personas.length} personas to ${PERSONAS_FILE}`);
    }
    catch (error) {
        log_1.logger.error('Failed to save personas:', error);
        throw error;
    }
}
/**
 * Generate next persona ID (P0001, P0002, etc.)
 */
function generatePersonaId(existingPersonas) {
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
async function createPersona(request) {
    log_1.logger.info(`Creating new persona: ${request.name}`);
    const personas = await loadPersonas();
    const id = generatePersonaId(personas);
    const newPersona = {
        id,
        name: request.name,
        traits: request.traits,
        refs: request.refs
    };
    personas.push(newPersona);
    await savePersonas(personas);
    log_1.logger.info(`Created persona ${id}: ${request.name} with ${request.traits.length} traits`);
    return newPersona;
}
/**
 * Get a persona by ID
 */
async function getPersona(id) {
    log_1.logger.info(`Looking up persona: ${id}`);
    const personas = await loadPersonas();
    const persona = personas.find(p => p.id === id) || null;
    if (persona) {
        log_1.logger.info(`Found persona ${id}: ${persona.name}`);
    }
    else {
        log_1.logger.info(`Persona ${id} not found`);
    }
    return persona;
}
/**
 * List all personas
 */
async function listPersonas() {
    log_1.logger.info('Loading all personas');
    const personas = await loadPersonas();
    log_1.logger.info(`Loaded ${personas.length} personas`);
    return personas;
}
/**
 * Delete a persona by ID (utility function)
 */
async function deletePersona(id) {
    log_1.logger.info(`Deleting persona: ${id}`);
    const personas = await loadPersonas();
    const initialLength = personas.length;
    const filteredPersonas = personas.filter(p => p.id !== id);
    if (filteredPersonas.length < initialLength) {
        await savePersonas(filteredPersonas);
        log_1.logger.info(`Deleted persona ${id}`);
        return true;
    }
    else {
        log_1.logger.info(`Persona ${id} not found for deletion`);
        return false;
    }
}
//# sourceMappingURL=personas.js.map