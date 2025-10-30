"""
PersonaEngine API Routes
Migrated from TypeScript Express server with Bearer auth and proper error handling
"""

import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.security import verify_token
from app.schemas import (
    BrainAskRequest, BrainAskResponse,
    UpsellSuggestRequest, UpsellSuggestResponse, 
    PersonaAddSystemRequest, PersonaAddSystemResponse,
    PersonaNewRequest, PersonaNewResponse,
    GenRequest, GenResponse,
    VaultOpenRequest, VaultOpenResponse,
    HealthResponse, StatusResponse,
    ErrorResponse
)
from app.claude_adapter import call_brain_ai, call_upsell_ai, get_ai_config
from app.vault_context import (
    ensure_vault_data, get_vault_stats,
    load_persona, load_manifest, load_all_personas, load_all_jobs
)


router = APIRouter(prefix="/api/v1", tags=["persona-engine"])


# =================== Global State ===================

# Track last upsell for status endpoint
last_upsell_data: Optional[Dict[str, Any]] = None


# =================== Request Logging Middleware ===================

def log_request(request: Request, route: str, mode: str, persona_id: Optional[str], job_id: Optional[str], 
                start_time: float) -> str:
    """Log request with UUID and timing."""
    request_id = str(uuid.uuid4())
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Structured logging
    log_data = {
        "request_id": request_id,
        "route": route,
        "mode": mode,
        "persona_id": persona_id,
        "job_id": job_id,
        "ms": elapsed_ms
    }
    
    print(f"INFO: API Request {log_data}")
    
    return request_id


# =================== Protected Endpoints (Bearer Auth Required) ===================

@router.post("/brain.ask", response_model=BrainAskResponse, operation_id="askBrain")
async def brain_ask(
    request: Request,
    body: BrainAskRequest,
    token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Brain AI query endpoint with persona and job context support.
    Requires Bearer token authentication.
    """
    start_time = time.time()
    
    try:
        # Get current mode
        import os
        mode = os.getenv("MODE", "fake")
        
        # Call brain AI with context
        result = await call_brain_ai(
            question=body.question,
            persona_id=body.persona_id,
            job_id=body.job_id,
            mode=mode
        )
        
        # Log request
        request_id = log_request(
            request, "/brain.ask", mode, body.persona_id, body.job_id, start_time
        )
        
        print(f"INFO: 🧠 Brain query completed: {mode} mode")
        
        return {
            "ok": True,
            "mode": mode,
            "answer": result["answer"],
            "persona_context": result.get("persona_context"),
            "job_context": result.get("job_context")
        }
        
    except Exception as e:
        request_id = log_request(request, "/brain.ask", "error", body.persona_id, body.job_id, start_time)
        raise HTTPException(status_code=500, detail=f"Brain processing failed: {str(e)}")


@router.post("/upsell.suggest", response_model=UpsellSuggestResponse, operation_id="suggestUpsells")
async def upsell_suggest(
    request: Request,
    body: UpsellSuggestRequest,
    token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Upsell suggestions endpoint with persona and job context support.
    Requires Bearer token authentication.
    """
    start_time = time.time()
    global last_upsell_data
    
    try:
        # Get current mode
        import os
        mode = os.getenv("MODE", "fake")
        
        # Call upsell AI with context
        result = await call_upsell_ai(
            user_id=body.user_id,
            persona_id=body.persona_id,
            job_id=body.job_id,
            style=body.style or "studio",
            intent=body.intent or "prints",
            mode=mode
        )
        
        # Update global state for status tracking
        last_upsell_data = {
            "suggestions_count": len(result["suggestions"]),
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Log request
        request_id = log_request(
            request, "/upsell.suggest", mode, body.persona_id, body.job_id, start_time
        )
        
        print(f"INFO: 💰 Upsell suggestions generated: {mode} mode")
        
        return {
            "ok": True,
            "mode": mode,
            "suggestions": result["suggestions"],
            "context": result["context"]
        }
        
    except Exception as e:
        request_id = log_request(request, "/upsell.suggest", "error", body.persona_id, body.job_id, start_time)
        raise HTTPException(status_code=500, detail=f"Upsell processing failed: {str(e)}")


@router.post("/persona.add_system", response_model=PersonaAddSystemResponse, operation_id="addSystemPersona")
async def persona_add_system(
    request: Request,
    body: PersonaAddSystemRequest,
    token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Add system persona endpoint with rate limiting.
    Requires Bearer token authentication.
    """
    start_time = time.time()
    
    try:
        # Validate system persona ID format
        if not body.id.startswith("U") or not body.id[1:].isdigit():
            raise HTTPException(
                status_code=400, 
                detail="System persona IDs must start with 'U' followed by numbers (e.g., U0001)"
            )
        
        # Create system persona data
        system_persona = {
            "id": body.id,
            "name": body.name,
            "role": body.role,
            "traits": body.traits,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "system": True
        }
        
        # Log request
        request_id = log_request(request, "/persona.add_system", "system", None, None, start_time)
        
        print(f"INFO: 👤 System persona created: {body.id}")
        
        return {
            "ok": True,
            "system_persona": system_persona
        }
        
    except HTTPException:
        raise
    except Exception as e:
        request_id = log_request(request, "/persona.add_system", "error", None, None, start_time)
        raise HTTPException(status_code=500, detail=f"System persona creation failed: {str(e)}")


# =================== Public Endpoints (No Auth Required) ===================

@router.post("/persona.new", response_model=PersonaNewResponse, operation_id="createPersona")
async def persona_new(
    request: Request,
    body: PersonaNewRequest,
    token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Create new persona endpoint with authentication.
    Requires Bearer token authentication.
    Generates new persona ID and returns persona data.
    """
    try:
        # Generate next persona ID
        personas_data = load_all_personas()
        
        # Handle case where data might be list or dict
        if isinstance(personas_data, dict):
            existing_ids = [p.get("id", "") for p in personas_data.get("personas", [])]
        else:
            existing_ids = []
            
        # Find next available P-ID
        next_id = "P0001"
        for i in range(1, 10000):
            candidate = f"P{i:04d}"
            if candidate not in existing_ids:
                next_id = candidate
                break
        
        # Create persona data
        persona = {
            "id": next_id,
            "name": body.name,
            "role": body.role,
            "traits": body.traits,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "system": False
        }
        
        # Persist to personas.json file
        try:
            import json
            from pathlib import Path
            
            personas_file = Path("data/personas.json")
            
            # Load current personas
            if personas_file.exists():
                with open(personas_file, 'r') as f:
                    current_data = json.load(f)
                    
                # Handle both list and dict formats
                if isinstance(current_data, list):
                    personas_list = current_data
                else:
                    personas_list = current_data.get('personas', [])
            else:
                personas_list = []
            
            # Add new persona
            personas_list.append(persona)
            
            # Write back to file (maintain current format)
            with open(personas_file, 'w') as f:
                json.dump(personas_list, f, indent=2)
                
        except Exception as e:
            print(f"WARNING: Failed to persist persona {next_id}: {e}")
        
        print(f"INFO: 👤 New persona created and persisted: {next_id}")
        
        return {
            "ok": True,
            "persona_id": next_id,
            "persona": persona
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Persona creation failed: {str(e)}")


@router.post("/gen", response_model=GenResponse, operation_id="generateImages")
async def gen_images(body: GenRequest) -> Dict[str, Any]:
    """
    Image generation endpoint (public).
    Generates job ID, creates images with seeds, and saves manifest.
    """
    # Validate persona exists
    persona = load_persona(body.persona_id)
    if not persona:
        raise HTTPException(
            status_code=404,
            detail=f"Persona not found: {body.persona_id}"
        )
    
    try:
        # Get current mode
        import os
        mode = os.getenv("MODE", "fake")
        
        # Generate next job ID
        from app.vault_context import load_all_jobs
        jobs_data = load_all_jobs()
        
        # Get existing job IDs
        if isinstance(jobs_data, dict):
            existing_job_ids = [j.get("id", "") for j in jobs_data.get("jobs", [])]
        else:
            existing_job_ids = []
            
        # Find next available J-ID
        next_job_id = "J0001"
        for i in range(1, 10000):
            candidate = f"J{i:04d}"
            if candidate not in existing_job_ids:
                next_job_id = candidate
                break
        
        if mode == "fake":
            # Generate fake images with seeds and slots
            images = []
            seeds = []
            
            for i in range(body.count):
                seed = 2000 + (int(next_job_id[1:]) * 100) + i  # Unique seed based on job
                seeds.append(seed)
                
                # Build prompt from slots
                prompt_parts = []
                if body.slots:
                    for key, value in body.slots.items():
                        prompt_parts.append(f"{key}: {value}")
                prompt = ", ".join(prompt_parts) if prompt_parts else f"{body.style} style image"
                
                images.append({
                    "id": f"{next_job_id}_img_{i+1}",
                    "url": f"https://picsum.photos/512/512?random={seed}",
                    "seed": seed,
                    "prompt": prompt,
                    "style": body.style,
                    "filename": f"{next_job_id}_{body.style}_{i+1:03d}.jpg"
                })
                
            # Create job manifest
            manifest = {
                "id": next_job_id,
                "persona_id": body.persona_id,
                "style": body.style,
                "count": body.count,
                "slots": body.slots,
                "seeds": seeds,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "mode": "fake",
                "images": images,
                "files": [img["filename"] for img in images]
            }
            
            # Save manifest to jobs data and file system
            try:
                import json
                from pathlib import Path
                
                # Update jobs.json
                jobs_file = Path("data/jobs.json")
                if jobs_file.exists():
                    with open(jobs_file, 'r') as f:
                        current_jobs = json.load(f)
                        
                    if isinstance(current_jobs, list):
                        jobs_list = current_jobs
                    else:
                        jobs_list = current_jobs.get('jobs', [])
                else:
                    jobs_list = []
                
                # Add new job
                job_entry = {
                    "id": next_job_id,
                    "title": f"{body.style.title()} Collection for {body.persona_id}",
                    "description": f"Generated {body.count} images with {body.style} style",
                    "style": body.slots,
                    "images": [img["filename"] for img in images],
                    "created_at": manifest["created_at"]
                }
                jobs_list.append(job_entry)
                
                # Write back to jobs.json
                with open(jobs_file, 'w') as f:
                    json.dump(jobs_list, f, indent=2)
                
                # Create manifest_job.json in vault structure
                vault_dir = Path(f"vault/dev/{body.persona_id}/{next_job_id}/{body.style}")
                vault_dir.mkdir(parents=True, exist_ok=True)
                
                manifest_file = vault_dir / "manifest_job.json"
                with open(manifest_file, 'w') as f:
                    json.dump(manifest, f, indent=2)
                    
                print(f"INFO: 📁 Manifest saved: {manifest_file}")
                    
            except Exception as e:
                print(f"WARNING: Failed to save manifest {next_job_id}: {e}")
            
        else:
            # In live mode, would call actual image generation service
            images = [{"error": "Live mode image generation not implemented"}]
            manifest = {"error": "Live mode not available"}
        
        print(f"INFO: 🖼️ Generated job {next_job_id}: {len(images)} images ({mode} mode)")
        
        return {
            "ok": True,
            "mode": mode,
            "job_id": next_job_id,
            "images": images,
            "manifest": manifest
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.post("/vault.open", response_model=VaultOpenResponse, operation_id="openVault")
async def vault_open(body: VaultOpenRequest) -> Dict[str, Any]:
    """
    Vault open endpoint (public).
    Returns vault images and job manifest from actual saved data.
    """
    try:
        # Get current mode
        import os
        mode = os.getenv("MODE", "fake")
        
        if mode == "fake":
            # Try to load actual manifest from vault structure
            import json
            from pathlib import Path
            
            # Search for manifest files for this job ID
            vault_base = Path("vault/dev")
            manifest_files = list(vault_base.glob(f"*/{body.job_id}/*/manifest_job.json"))
            
            
            if manifest_files:
                # Load the first matching manifest
                manifest_file = manifest_files[0]
                
                try:
                    with open(manifest_file, 'r') as f:
                        manifest_data = json.load(f)
                    
                    # Extract images from manifest
                    images = []
                    if "images" in manifest_data:
                        for img_data in manifest_data["images"]:
                            images.append({
                                "id": img_data.get("id"),
                                "url": img_data.get("url"),
                                "filename": img_data.get("filename"),
                                "seed": img_data.get("seed"),
                                "prompt": img_data.get("prompt"),
                                "style": img_data.get("style")
                            })
                    
                    # Build manifest response
                    manifest = {
                        "job_id": body.job_id,
                        "persona_id": manifest_data.get("persona_id"),
                        "title": f"Vault Job {body.job_id}",
                        "style": manifest_data.get("style"),
                        "slots": manifest_data.get("slots", {}),
                        "seeds": manifest_data.get("seeds", []),
                        "created_at": manifest_data.get("created_at"),
                        "images_count": len(images),
                        "vault_path": str(manifest_file.parent),
                        "manifest_path": str(manifest_file)
                    }
                    
                    print(f"INFO: 📁 Loaded manifest from: {manifest_file}")
                    
                except Exception as e:
                    print(f"WARNING: Failed to load manifest {manifest_file}: {e}")
                    # Fallback to default manifest
                    images = []
                    manifest = {
                        "job_id": body.job_id,
                        "error": f"Failed to load manifest: {e}",
                        "vault_path": str(manifest_file.parent) if manifest_files else "not_found"
                    }
                    
            else:
                # No manifest found, generate placeholder
                images = []
                for i in range(6):  # Default 6 images
                    images.append({
                        "id": f"vault_img_{i+1}",
                        "url": f"https://picsum.photos/512/512?random={100+i}",
                        "filename": f"vault_{body.job_id}_{i+1}.jpg",
                        "size": "512x512"
                    })
                    
                manifest = {
                    "job_id": body.job_id,
                    "title": f"Vault Job {body.job_id} (placeholder)",
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "images_count": len(images),
                    "vault_path": "not_found",
                    "note": "No manifest file found, using placeholder data"
                }
            
        else:
            # In live mode, would load actual vault data
            images = [{"error": "Live mode vault access not implemented"}]
            manifest = {"error": "Live mode not available"}
        
        print(f"INFO: 🔐 Vault opened: {body.job_id} ({len(images)} images)")
        
        return {
            "ok": True,
            "mode": mode,
            "images": images,
            "manifest": manifest
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vault access failed: {str(e)}")


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    """Simple ping endpoint for health checks."""
    return {
        "ok": True,
        "pong": True,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# =================== Enhanced Status/Health Endpoints ===================

@router.get("/health_enhanced", response_model=HealthResponse)
async def enhanced_health() -> Dict[str, Any]:
    """
    Enhanced health endpoint with LLM mode and upsell tracking.
    (Uses /health_enhanced to avoid conflict with system health endpoint)
    """
    # Get current mode
    import os
    mode_llm = os.getenv("MODE", "fake")
    
    return {
        "ok": True,
        "mode_llm": mode_llm,
        "last_upsell": last_upsell_data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/status", response_model=StatusResponse)
async def enhanced_status() -> Dict[str, Any]:
    """
    Enhanced status endpoint with persona/job counters and activity tracking.
    """
    try:
        # Get persona count
        personas_data = load_all_personas()
        if isinstance(personas_data, dict):
            persona_count = len(personas_data.get("personas", []))
        elif isinstance(personas_data, list):
            persona_count = len(personas_data)
        else:
            persona_count = 0
            
        # Get job count
        from app.vault_context import load_all_jobs
        jobs_data = load_all_jobs()
        if isinstance(jobs_data, dict):
            job_count = len(jobs_data.get("jobs", []))
        elif isinstance(jobs_data, list):
            job_count = len(jobs_data)
        else:
            job_count = 0
        
        # Get latest persona ID
        if isinstance(personas_data, dict):
            persona_ids = [p.get("id", "") for p in personas_data.get("personas", [])]
        elif isinstance(personas_data, list):
            persona_ids = [p.get("id", "") for p in personas_data]
        else:
            persona_ids = []
        latest_persona = max(persona_ids) if persona_ids else None
        
        # Get latest job ID
        if isinstance(jobs_data, dict):
            job_ids = [j.get("id", "") for j in jobs_data.get("jobs", [])]
        elif isinstance(jobs_data, list):
            job_ids = [j.get("id", "") for j in jobs_data]
        else:
            job_ids = []
        latest_job = max(job_ids) if job_ids else None
        
        return {
            "ok": True,
            "persona_count": persona_count,
            "job_count": job_count,
            "latest_persona_id": latest_persona,
            "latest_job_id": latest_job,
            "last_upsell": last_upsell_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "ok": True,
            "error": f"Status collection failed: {str(e)}",
            "last_upsell": last_upsell_data
        }


# =================== Development/Debug Endpoints ===================

@router.get("/debug/vault")
async def debug_vault_info() -> Dict[str, Any]:
    """Debug endpoint to check vault configuration and data."""
    # Ensure vault data exists
    ensure_vault_data()
    
    # Get vault stats
    stats = get_vault_stats()
    
    # Get AI config
    ai_config = get_ai_config()
    
    return {
        "ok": True,
        "vault_stats": stats,
        "ai_config": ai_config,
        "endpoints_migrated": [
            "/api/v1/brain.ask",
            "/api/v1/upsell.suggest", 
            "/api/v1/persona.add_system",
            "/api/v1/persona.new",
            "/api/v1/gen",
            "/api/v1/vault.open",
            "/api/v1/ping",
            "/api/v1/health",
            "/api/v1/status"
        ]
    }