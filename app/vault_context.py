"""
Vault Context Utilities for PersonaEngine
Loads persona and job manifest data for AI context building
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


# =================== Configuration ===================

VAULT_DIR = Path("data")
PERSONAS_FILE = VAULT_DIR / "personas.json"
JOBS_FILE = VAULT_DIR / "jobs.json"


# =================== Persona Loading ===================

def load_persona(persona_id: str) -> Optional[Dict[str, Any]]:
    """
    Load persona data from vault storage.
    
    Args:
        persona_id: Persona identifier (e.g., "P0001")
        
    Returns:
        Dict with persona data or None if not found
    """
    try:
        if not PERSONAS_FILE.exists():
            return None
            
        with open(PERSONAS_FILE, 'r') as f:
            data = json.load(f)
            
        # Handle both list and dict formats
        personas_list = []
        if isinstance(data, list):
            personas_list = data
        elif isinstance(data, dict):
            personas_list = data.get('personas', [])
            
        # Find persona by ID
        for persona in personas_list:
            if persona.get('id') == persona_id:
                return persona
                
        return None
        
    except Exception:
        return None


def load_all_personas() -> Dict[str, Any]:
    """
    Load all personas from vault storage.
    
    Returns:
        Dict with all personas data (normalizes list format to dict format)
    """
    try:
        if not PERSONAS_FILE.exists():
            return {"personas": []}
            
        with open(PERSONAS_FILE, 'r') as f:
            data = json.load(f)
            
        # Handle both list and dict formats
        if isinstance(data, list):
            return {"personas": data}
        elif isinstance(data, dict):
            return data
        else:
            return {"personas": []}
            
    except Exception:
        return {"personas": []}


# =================== Job Manifest Loading ===================

def load_manifest(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Load job manifest from vault storage.
    
    Args:
        job_id: Job identifier (e.g., "J0001")
        
    Returns:
        Dict with job manifest or None if not found
    """
    try:
        if not JOBS_FILE.exists():
            return None
            
        with open(JOBS_FILE, 'r') as f:
            jobs = json.load(f)
            
        # Find job by ID
        for job in jobs.get('jobs', []):
            if job.get('id') == job_id:
                return job
                
        return None
        
    except Exception:
        return None


def load_all_jobs() -> Dict[str, Any]:
    """
    Load all jobs from vault storage.
    
    Returns:
        Dict with all jobs data
    """
    try:
        if not JOBS_FILE.exists():
            return {"jobs": []}
            
        with open(JOBS_FILE, 'r') as f:
            return json.load(f)
            
    except Exception:
        return {"jobs": []}


# =================== Summarization Utils ===================

def summarize_manifest(manifest: Dict[str, Any]) -> str:
    """
    Summarize job manifest for AI context.
    
    Args:
        manifest: Job manifest data
        
    Returns:
        Summarized text for AI context
    """
    if not manifest:
        return ""
        
    try:
        title = manifest.get('title', 'Untitled Job')
        description = manifest.get('description', '')
        style = manifest.get('style', {})
        
        # Build summary
        summary_parts = [f"Job: {title}"]
        
        if description:
            # Truncate long descriptions
            desc_short = description[:200] + "..." if len(description) > 200 else description
            summary_parts.append(f"Description: {desc_short}")
            
        if style:
            style_info = []
            for key, value in style.items():
                if isinstance(value, (str, int, float)):
                    style_info.append(f"{key}: {value}")
            if style_info:
                summary_parts.append(f"Style: {', '.join(style_info[:3])}")
                
        return " | ".join(summary_parts)
        
    except Exception:
        return f"Job ID: {manifest.get('id', 'unknown')}"


def summarize_persona(persona: Dict[str, Any]) -> str:
    """
    Summarize persona for AI context.
    
    Args:
        persona: Persona data
        
    Returns:
        Summarized text for AI context
    """
    if not persona:
        return ""
        
    try:
        name = persona.get('name', 'Unknown')
        role = persona.get('role', 'user')
        traits = persona.get('traits', [])
        
        # Build summary
        summary_parts = [f"Persona: {name} ({role})"]
        
        if traits:
            # Limit to first 5 traits
            trait_list = traits[:5]
            summary_parts.append(f"Traits: {', '.join(trait_list)}")
            
        return " | ".join(summary_parts)
        
    except Exception:
        return f"Persona ID: {persona.get('id', 'unknown')}"


# =================== Context Building ===================

def build_brain_context(persona_id: Optional[str] = None, job_id: Optional[str] = None) -> Dict[str, str]:
    """
    Build context strings for brain AI queries.
    
    Args:
        persona_id: Optional persona context
        job_id: Optional job context
        
    Returns:
        Dict with context strings
    """
    context = {}
    
    if persona_id:
        persona = load_persona(persona_id)
        if persona:
            context['persona_context'] = summarize_persona(persona)
            
    if job_id:
        manifest = load_manifest(job_id)
        if manifest:
            context['job_context'] = summarize_manifest(manifest)
            
    return context


def build_upsell_context(persona_id: Optional[str] = None, job_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build rich context for upsell AI queries.
    
    Args:
        persona_id: Optional persona context
        job_id: Optional job context
        
    Returns:
        Dict with context data and metadata
    """
    context = {
        "persona_data": None,
        "job_data": None,
        "persona_summary": "",
        "job_summary": "",
        "images_count": 0
    }
    
    if persona_id:
        persona = load_persona(persona_id)
        if persona:
            context['persona_data'] = persona
            context['persona_summary'] = summarize_persona(persona)
            
    if job_id:
        manifest = load_manifest(job_id)
        if manifest:
            context['job_data'] = manifest
            context['job_summary'] = summarize_manifest(manifest)
            
            # Count images if available
            images = manifest.get('images', [])
            if isinstance(images, list):
                context['images_count'] = len(images)
            elif isinstance(images, dict):
                context['images_count'] = len(images.get('generated', []))
                
    return context


# =================== Vault Data Management ===================

def ensure_vault_data():
    """
    Ensure vault data files exist with sample data.
    Creates placeholder files if they don't exist.
    """
    # Ensure data directory exists
    VAULT_DIR.mkdir(exist_ok=True)
    
    # Create sample personas if file doesn't exist
    if not PERSONAS_FILE.exists():
        sample_personas = {
            "personas": [
                {
                    "id": "P0001",
                    "name": "Creative Director",
                    "role": "user",
                    "traits": ["creative", "strategic", "visual", "artistic"],
                    "created_at": "2025-01-01T00:00:00Z"
                },
                {
                    "id": "P0002", 
                    "name": "Brand Manager",
                    "role": "user",
                    "traits": ["analytical", "market-focused", "data-driven"],
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ]
        }
        
        with open(PERSONAS_FILE, 'w') as f:
            json.dump(sample_personas, f, indent=2)
    
    # Create sample jobs if file doesn't exist
    if not JOBS_FILE.exists():
        sample_jobs = {
            "jobs": [
                {
                    "id": "J0001",
                    "title": "Studio Portrait Collection",
                    "description": "Professional portrait session with natural lighting",
                    "style": {
                        "lighting": "natural",
                        "background": "studio",
                        "mood": "professional"
                    },
                    "images": ["img1.jpg", "img2.jpg", "img3.jpg"],
                    "created_at": "2025-01-01T00:00:00Z"
                },
                {
                    "id": "J0002",
                    "title": "Creative Brand Shoot", 
                    "description": "Dynamic brand imagery for social media campaign",
                    "style": {
                        "lighting": "dramatic",
                        "background": "colorful",
                        "mood": "energetic"
                    },
                    "images": ["brand1.jpg", "brand2.jpg"],
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ]
        }
        
        with open(JOBS_FILE, 'w') as f:
            json.dump(sample_jobs, f, indent=2)


# =================== Development Helpers ===================

def get_vault_stats() -> Dict[str, Any]:
    """
    Get vault statistics for debugging.
    
    Returns:
        Dict with vault storage stats
    """
    ensure_vault_data()
    
    personas = load_all_personas()
    jobs = load_all_jobs()
    
    # Handle case where data might be list or dict
    personas_count = 0
    if isinstance(personas, dict):
        personas_count = len(personas.get('personas', []))
    elif isinstance(personas, list):
        personas_count = len(personas)
        
    jobs_count = 0
    if isinstance(jobs, dict):
        jobs_count = len(jobs.get('jobs', []))
    elif isinstance(jobs, list):
        jobs_count = len(jobs)
    
    return {
        "personas_count": personas_count,
        "jobs_count": jobs_count,
        "personas_file_exists": PERSONAS_FILE.exists(),
        "jobs_file_exists": JOBS_FILE.exists(),
        "vault_dir_exists": VAULT_DIR.exists()
    }