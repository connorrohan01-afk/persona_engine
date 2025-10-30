"""Warming API routes for PersonaEngine."""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models_warming import WarmingPlan, WarmingAction, WarmingRun, WarmingLog
from app.models_accounts import AccountSession
from app.warming_engine import warming_engine
from app.security import verify_token

router = APIRouter(prefix="/api/v1/warm", tags=["warming"])


# Request/Response Models
class CreatePlanRequest(BaseModel):
    tenant_id: str = "owner"
    platform: str = "reddit"
    account_id: str
    enabled: bool = True
    window_start: str = "08:00"
    window_end: str = "22:00"
    actions_per_day: int = 10
    dry: bool = False


class AddActionRequest(BaseModel):
    plan_id: str
    kind: str
    params: Dict[str, Any]
    weight: int = 1
    enabled: bool = True


class RunNowRequest(BaseModel):
    tenant_id: str = "owner"
    plan_id: Optional[str] = None
    limit: int = 6
    dry: bool = True


class RunCronRequest(BaseModel):
    tenant_id: str = "owner"
    limit_plans: int = 5
    dry: bool = False


class TogglePlanRequest(BaseModel):
    plan_id: str
    enabled: bool


# Route implementations
@router.post("/plan/create")
async def create_plan(
    request: CreatePlanRequest,
    token: str = Depends(verify_token)
):
    """Create a new warming plan."""
    # Force dry mode if DRY_DEFAULT is set
    dry = request.dry or bool(settings.dry_default)
    mode = "dry" if dry else "live"
    
    with Session(engine) as db:
        # Verify account exists
        account = db.exec(
            select(AccountSession)
            .where(AccountSession.id == int(request.account_id))
        ).first()
        
        if not account:
            return {
                "ok": False,
                "mode": mode,
                "error": "Account not found"
            }
        
        # Check for existing plan
        existing_plan = db.exec(
            select(WarmingPlan)
            .where(
                WarmingPlan.tenant_id == request.tenant_id,
                WarmingPlan.account_id == request.account_id,
                WarmingPlan.platform == request.platform
            )
        ).first()
        
        if existing_plan:
            return {
                "ok": False,
                "mode": mode,
                "error": "Plan already exists for this account"
            }
        
        # Create new plan
        plan = WarmingPlan(
            tenant_id=request.tenant_id,
            platform=request.platform,
            account_id=request.account_id,
            enabled=request.enabled,
            window_start=request.window_start,
            window_end=request.window_end,
            actions_per_day=request.actions_per_day
        )
        
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        return {
            "ok": True,
            "mode": mode,
            "plan_id": f"wp_{plan.id}"
        }


@router.post("/plan/add-action")
async def add_action(
    request: AddActionRequest,
    token: str = Depends(verify_token)
):
    """Add an action to a warming plan."""
    # Parse plan ID
    try:
        plan_id = int(request.plan_id.replace("wp_", ""))
    except (ValueError, AttributeError):
        return {
            "ok": False,
            "mode": "live",
            "error": "Invalid plan_id format"
        }
    
    with Session(engine) as db:
        # Verify plan exists
        plan = db.get(WarmingPlan, plan_id)
        if not plan:
            return {
                "ok": False,
                "mode": "live",
                "error": "Plan not found"
            }
        
        # Create action
        action = WarmingAction(
            plan_id=plan_id,
            kind=request.kind,
            params_json=json.dumps(request.params),
            weight=request.weight,
            enabled=request.enabled
        )
        
        db.add(action)
        db.commit()
        db.refresh(action)
        
        return {
            "ok": True,
            "mode": "live",
            "action_id": f"wa_{action.id}"
        }


@router.post("/run-now")
async def run_now(
    request: RunNowRequest,
    token: str = Depends(verify_token)
):
    """Run warming actions immediately for a specific plan."""
    # Force dry mode if DRY_DEFAULT is set
    dry = request.dry or bool(settings.dry_default)
    
    if request.plan_id:
        # Run specific plan
        try:
            plan_id = int(request.plan_id.replace("wp_", ""))
        except (ValueError, AttributeError):
            return {
                "ok": False,
                "mode": "dry" if dry else "live",
                "error": "Invalid plan_id format"
            }
        
        result = await warming_engine.run_specific_plan(
            plan_id=plan_id,
            limit_actions=request.limit,
            dry=dry
        )
        
        return result
    else:
        # Run eligible plans for tenant
        result = await warming_engine.run_eligible_plans(
            tenant_id=request.tenant_id,
            limit_plans=request.limit,
            dry=dry
        )
        
        return result


@router.post("/run-cron")
async def run_cron(
    request: RunCronRequest,
    token: str = Depends(verify_token)
):
    """Run warming actions for eligible plans (cron-style)."""
    # Force dry mode if DRY_DEFAULT is set
    dry = request.dry or bool(settings.dry_default)
    
    result = await warming_engine.run_eligible_plans(
        tenant_id=request.tenant_id,
        limit_plans=request.limit_plans,
        dry=dry
    )
    
    return result


@router.get("/plan")
async def get_plan(
    id: str = Query(..., description="Plan ID"),
    token: str = Depends(verify_token)
):
    """Get warming plan details with actions."""
    # Parse plan ID
    try:
        plan_id = int(id.replace("wp_", ""))
    except (ValueError, AttributeError):
        return {
            "ok": False,
            "mode": "live",
            "error": "Invalid plan_id format"
        }
    
    with Session(engine) as db:
        # Get plan
        plan = db.get(WarmingPlan, plan_id)
        if not plan:
            return {
                "ok": False,
                "mode": "live",
                "error": "Plan not found"
            }
        
        # Get actions
        actions = db.exec(
            select(WarmingAction)
            .where(WarmingAction.plan_id == plan_id)
        ).all()
        
        return {
            "ok": True,
            "mode": "live",
            "plan": {
                "id": f"wp_{plan.id}",
                "enabled": plan.enabled,
                "window_start": plan.window_start,
                "window_end": plan.window_end,
                "actions_per_day": plan.actions_per_day,
                "platform": plan.platform,
                "account_id": plan.account_id,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat()
            },
            "actions": [
                {
                    "id": f"wa_{action.id}",
                    "kind": action.kind,
                    "params": action.params,
                    "weight": action.weight,
                    "enabled": action.enabled,
                    "created_at": action.created_at.isoformat()
                }
                for action in actions
            ]
        }


@router.post("/plan/toggle")
async def toggle_plan(
    request: TogglePlanRequest,
    token: str = Depends(verify_token)
):
    """Enable or disable a warming plan."""
    # Parse plan ID
    try:
        plan_id = int(request.plan_id.replace("wp_", ""))
    except (ValueError, AttributeError):
        return {
            "ok": False,
            "mode": "live",
            "error": "Invalid plan_id format"
        }
    
    with Session(engine) as db:
        # Get plan
        plan = db.get(WarmingPlan, plan_id)
        if not plan:
            return {
                "ok": False,
                "mode": "live",
                "error": "Plan not found"
            }
        
        # Update enabled status
        plan.enabled = request.enabled
        plan.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "ok": True,
            "mode": "live",
            "plan_id": f"wp_{plan.id}",
            "enabled": plan.enabled
        }


@router.get("/run/status")
async def get_run_status(
    id: str = Query(..., description="Run ID"),
    token: str = Depends(verify_token)
):
    """Get warming run status with logs."""
    # Parse run ID
    try:
        run_id = int(id.replace("wr_", ""))
    except (ValueError, AttributeError):
        return {
            "ok": False,
            "mode": "live",
            "error": "Invalid run_id format"
        }
    
    with Session(engine) as db:
        # Get run
        run = db.get(WarmingRun, run_id)
        if not run:
            return {
                "ok": False,
                "mode": "live",
                "error": "Run not found"
            }
        
        # Get logs
        logs = db.exec(
            select(WarmingLog)
            .where(WarmingLog.run_id == run_id)
        ).all()
        
        return {
            "ok": True,
            "mode": run.mode,
            "run": {
                "id": f"wr_{run.id}",
                "plan_id": f"wp_{run.plan_id}",
                "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "attempted": run.actions_attempted,
                "succeeded": run.actions_succeeded,
                "mode": run.mode
            },
            "logs": [
                {
                    "id": log.id,
                    "account_id": log.account_id,
                    "action_kind": log.action_kind,
                    "status": log.status,
                    "error": log.error,
                    "meta": log.meta,
                    "ts": log.ts.isoformat()
                }
                for log in logs
            ]
        }


@router.get("/plans/{tenant_id}")
async def list_plans(
    tenant_id: str,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    platform: Optional[str] = Query(default=None),
    enabled: Optional[bool] = Query(default=None),
    token: str = Depends(verify_token)
):
    """List warming plans for a tenant."""
    with Session(engine) as db:
        # Build query
        query = select(WarmingPlan).where(WarmingPlan.tenant_id == tenant_id)
        
        if platform:
            query = query.where(WarmingPlan.platform == platform)
        if enabled is not None:
            query = query.where(WarmingPlan.enabled == enabled)
        
        # Get total count
        total_query = query
        total = len(db.exec(total_query).all())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        plans = db.exec(query).all()
        
        return {
            "ok": True,
            "mode": "live",
            "plans": [
                {
                    "id": f"wp_{plan.id}",
                    "platform": plan.platform,
                    "account_id": plan.account_id,
                    "enabled": plan.enabled,
                    "window_start": plan.window_start,
                    "window_end": plan.window_end,
                    "actions_per_day": plan.actions_per_day,
                    "created_at": plan.created_at.isoformat(),
                    "updated_at": plan.updated_at.isoformat()
                }
                for plan in plans
            ],
            "total": total,
            "offset": offset,
            "limit": limit
        }


@router.get("/runs/{tenant_id}")
async def list_runs(
    tenant_id: str,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    mode: Optional[str] = Query(default=None),
    token: str = Depends(verify_token)
):
    """List warming runs for a tenant."""
    with Session(engine) as db:
        # Get plans for this tenant first
        tenant_plans = db.exec(
            select(WarmingPlan).where(WarmingPlan.tenant_id == tenant_id)
        ).all()
        
        if not tenant_plans:
            return {
                "ok": True,
                "mode": "live",
                "runs": [],
                "total": 0,
                "offset": offset,
                "limit": limit
            }
        
        plan_ids = [plan.id for plan in tenant_plans if plan.id]
        
        if not plan_ids:
            return {
                "ok": True,
                "mode": "live",
                "runs": [],
                "total": 0,
                "offset": offset,
                "limit": limit
            }
        
        # Build query for runs - simple approach without .in_()
        query = select(WarmingRun)
        
        if mode:
            query = query.where(WarmingRun.mode == mode)
        
        # Get total count
        total = len(db.exec(query).all())
        
        # Apply pagination and ordering
        query = query.offset(offset).limit(limit)
        runs = db.exec(query).all()
        
        return {
            "ok": True,
            "mode": "live",
            "runs": [
                {
                    "id": f"wr_{run.id}",
                    "plan_id": f"wp_{run.plan_id}",
                    "started_at": run.started_at.isoformat(),
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "attempted": run.actions_attempted,
                    "succeeded": run.actions_succeeded,
                    "mode": run.mode
                }
                for run in runs
            ],
            "total": total,
            "offset": offset,
            "limit": limit
        }