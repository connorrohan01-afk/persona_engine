"""Scheduler and job management endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.security import verify_token
from app.queue import enqueue, worker_tick, get_queue_stats
from loguru import logger

router = APIRouter(prefix="/api/v1/schedule", tags=["scheduler"])


class EnqueueJobRequest(BaseModel):
    job_type: str  # warm_step, post_job, custom
    args: Dict[str, Any]
    idempotency_key: Optional[str] = None
    priority: int = 5  # 1=highest, 10=lowest
    run_after: Optional[str] = None  # ISO datetime string


@router.post("/enqueue")
async def enqueue_job(
    request: EnqueueJobRequest,
    token: str = Depends(verify_token)
):
    """Enqueue a job for background processing."""
    
    # Parse run_after if provided
    run_after_dt = None
    if request.run_after:
        try:
            run_after_dt = datetime.fromisoformat(request.run_after.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid run_after datetime format")
    
    try:
        job_id = enqueue(
            job_type=request.job_type,
            args=request.args,
            idempotency_key=request.idempotency_key,
            priority=request.priority,
            run_after=run_after_dt
        )
        
        logger.info(f"Enqueued job {job_id} of type {request.job_type}")
        
        return {
            "ok": True,
            "job_id": job_id
        }
        
    except Exception as e:
        logger.error(f"Failed to enqueue job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")


@router.post("/tick", include_in_schema=False)
async def system_tick(
    token: str = Depends(verify_token)
):
    """Manually trigger job processing."""
    
    try:
        stats = worker_tick(max_jobs=10)
        
        logger.info(f"Manual tick processed {stats['processed']} jobs, {stats['remaining']} remaining")
        
        return {
            "ok": True,
            "processed": stats["processed"],
            "remaining": stats["remaining"]
        }
        
    except Exception as e:
        logger.error(f"System tick failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"System tick failed: {str(e)}")


@router.get("/queue")
async def get_queue_status(
    token: str = Depends(verify_token)
):
    """Get current queue statistics."""
    
    try:
        stats = get_queue_stats()
        
        return {
            "ok": True,
            "counts": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


# System routes (separate prefix)
system_router = APIRouter(prefix="/api/v1/system", tags=["system"])


@system_router.post("/tick")
async def system_tick_endpoint(
    token: str = Depends(verify_token)
):
    """Trigger worker tick for job processing."""
    
    try:
        stats = worker_tick(max_jobs=10)
        
        logger.info(f"System tick processed {stats['processed']} jobs, {stats['remaining']} remaining")
        
        return {
            "ok": True,
            "processed": stats["processed"],
            "remaining": stats["remaining"]
        }
        
    except Exception as e:
        logger.error(f"System tick failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"System tick failed: {str(e)}")


@system_router.get("/queue")
async def system_queue_status(
    token: str = Depends(verify_token)
):
    """Get queue status and statistics."""
    
    try:
        stats = get_queue_stats()
        
        return {
            "ok": True,
            "counts": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@system_router.get("/health")
async def system_health():
    """System health check (no auth required)."""
    
    try:
        # Basic health check - get queue stats
        stats = get_queue_stats()
        
        # Check for stuck jobs
        stuck_jobs = stats.get("locked", 0)
        health_status = "ok" if stuck_jobs < 5 else "degraded"
        
        return {
            "ok": True,
            "status": health_status,
            "queue": {
                "pending": stats.get("pending", 0),
                "due": stats.get("due", 0),
                "running": stats.get("running", 0),
                "stuck": stuck_jobs
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "ok": False,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }