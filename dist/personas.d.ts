import { Persona } from './types';
interface CreatePersonaRequest {
    name: string;
    traits: string[];
    refs?: string[];
}
/**
 * Create a new persona with auto-generated ID
 */
export declare function createPersona(request: CreatePersonaRequest): Promise<Persona>;
/**
 * Get a persona by ID
 */
export declare function getPersona(id: string): Promise<Persona | null>;
/**
 * List all personas
 */
export declare function listPersonas(): Promise<Persona[]>;
/**
 * Delete a persona by ID (utility function)
 */
export declare function deletePersona(id: string): Promise<boolean>;
export {};
//# sourceMappingURL=personas.d.ts.map