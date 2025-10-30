"""System endpoints for health and version checks."""

from datetime import datetime
from fastapi import APIRouter, Depends
from app.security import verify_token

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/health")
async def health():
    """Health check endpoint - no auth required."""
    from app.main import TASK_QUEUE
    
    return {
        "ok": True,
        "queue_depth": TASK_QUEUE.qsize(),
        "time": datetime.utcnow().isoformat()
    }


@router.get("/version")
async def version():
    """Version endpoint - no auth required."""
    return {
        "name": "PersonaEngine",
        "version": "0.1.0"
    }


@router.post("/system/tick")
async def system_tick(token: str = Depends(verify_token)):
    """Trigger job processing - requires auth."""
    from app.queue import worker_tick
    worker_tick()
    return {"ok": True, "message": "Job processing triggered"}