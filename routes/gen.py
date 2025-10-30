from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os, json
from datetime import datetime
from pathlib import Path

router = APIRouter()

def parse_args(rest):
    """Parse key:value arguments from command rest"""
    args = {}
    for item in rest:
        if ":" in item:
            key, value = item.split(":", 1)
            args[key] = value
        else:
            # Handle positional args (like persona_id)
            if not args.get("persona_id") and item.startswith("P"):
                args["persona_id"] = item
    return args

@router.post("/persona/new")
async def create_persona(request: Request):
    """Create a new persona card"""
    payload = await request.json()
    text = str(payload.get("text", "")).strip()
    metadata = payload.get("metadata", {})
    
    # Parse arguments from text
    parts = text.split()[1:]  # Skip the command part
    args = parse_args(parts)
    
    # Create persona card
    card = {
        "id": args.get("id"),
        "name": args.get("name"),
        "traits": args.get("traits","").split(",") if args.get("traits") else [],
    }
    
    # Save to vault
    os.makedirs("vault/dev/personas", exist_ok=True)
    with open(f"vault/dev/personas/{card['id']}.json", "w") as f:
        json.dump(card, f, indent=2)
    
    return {
        "ok": True,
        "text": f"✅ persona created: {card['id']}",
        "results": [{"status": "ok", "type": "persona.new", "persona": card}],
        "meta": {"received": {"text": text, "metadata": metadata}}
    }

@router.post("/generate")
async def generate_images(request: Request):
    """Generate images for a persona"""
    payload = await request.json()
    text = str(payload.get("text", "")).strip()
    metadata = payload.get("metadata", {})
    
    # Parse arguments from text
    parts = text.split()[1:]  # Skip the command part
    args = parse_args(parts)
    
    # Get generation parameters
    persona = parts[0] if parts else args.get("persona")
    style = args.get("style", "studio")
    count = int(args.get("count", 6))
    job_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    # Validate persona is provided
    if not persona:
        return {
            "ok": True,
            "text": "❌ Missing persona ID",
            "results": [{"status": "error", "type": "gen", "error": "persona required"}],
            "meta": {"received": {"text": text, "metadata": metadata}}
        }
    
    # Create job directory and manifest
    job_dir = f"vault/dev/{persona}/{job_id}/{style}"
    os.makedirs(job_dir, exist_ok=True)
    manifest = {"job_id": job_id, "persona": persona, "style": style, "count": count, "status": "queued"}
    with open(f"{job_dir}/manifest_job.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Generate images based on provider
    if os.getenv("GEN_PROVIDER") == "fake":
        from adapters.gen_fake import run_fake_gen
        result = run_fake_gen(persona, style, job_id, count)
        # Update manifest with completion
        manifest.update({"status": "completed", "images": result.get("images", [])})
        with open(f"{job_dir}/manifest_job.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        return {
            "ok": True,
            "text": f"🎨 generated → {job_id}",
            "results": [{
                "status": "ok",
                "type": "gen",
                "job_id": job_id,
                "persona": persona,
                "style": style,
                "count": result.get("count", count)
            }],
            "meta": {"received": {"text": text, "metadata": metadata}}
        }
    else:
        # TODO: enqueue real image gen worker here
        return {
            "ok": True,
            "text": f"🎨 queued gen → {job_id}",
            "results": [{
                "status": "ok",
                "type": "gen",
                "job_id": job_id,
                "persona": persona,
                "style": style
            }],
            "meta": {"received": {"text": text, "metadata": metadata}}
        }

@router.post("/generate/more")
async def generate_more(request: Request):
    """Add more images to an existing generation job"""
    payload = await request.json()
    text = str(payload.get("text", "")).strip()
    metadata = payload.get("metadata", {})
    
    # Parse arguments from text
    parts = text.split()[1:]  # Skip the command part
    args = parse_args(parts)
    job = args.get("job")
    
    return {
        "ok": True,
        "text": f"➕ queued more → {job}",
        "results": [{"status": "ok", "type": "gen.more", "job_id": job}],
        "meta": {"received": {"text": text, "metadata": metadata}}
    }

@router.post("/vault/open")
async def open_vault(request: Request):
    """Get vault access URL for a persona"""
    payload = await request.json()
    text = str(payload.get("text", "")).strip()
    metadata = payload.get("metadata", {})
    
    # Parse arguments from text
    parts = text.split()[1:]  # Skip the command part
    args = parse_args(parts)
    persona = args.get("persona") or (parts[0] if parts else None)
    
    return {
        "ok": True,
        "text": "🔓 vault ready",
        "results": [{
            "status": "ok",
            "type": "vault.open",
            "url": f"/vault/dev/{persona}/"
        }],
        "meta": {"received": {"text": text, "metadata": metadata}}
    }