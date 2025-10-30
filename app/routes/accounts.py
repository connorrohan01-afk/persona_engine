"""Account management routes for session lifecycle, proxy assignment, and captcha solving."""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from loguru import logger

from app.db import get_session
from app.security import verify_token
from app.models_accounts import AccountSession, SessionRecord, CaptchaJob
from app.sessions import session_manager, extract_session_id, extract_account_id
from app.providers.captcha import solve_captcha
from app.providers.proxy import proxy_manager


router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


# Request/Response Models
class CreateAccountRequest(BaseModel):
    tenant_id: str
    platform: str
    username: str
    email: str
    proxy: Optional[str] = None
    dry: bool = False


class LoadSessionRequest(BaseModel):
    tenant_id: str
    account_id: str


class UpdateSessionRequest(BaseModel):
    session_id: str
    status: str


class AssignProxyRequest(BaseModel):
    session_id: str


class SolveCaptchaRequest(BaseModel):
    tenant_id: str
    site_key: str
    url: str
    dry: bool = True


@router.post("/create")
async def create_account(
    request: CreateAccountRequest,
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Create a new account and associated session."""
    try:
        logger.info(f"Creating account for {request.username} on {request.platform} (dry={request.dry})")
        
        # Check if account already exists
        existing_account = db.exec(
            select(AccountSession).where(
                AccountSession.tenant_id == request.tenant_id,
                AccountSession.platform == request.platform,
                AccountSession.username == request.username
            )
        ).first()
        
        if existing_account:
            raise HTTPException(
                status_code=400,
                detail=f"Account {request.username} already exists on {request.platform}"
            )
        
        # Create new account
        account = AccountSession(
            tenant_id=request.tenant_id,
            platform=request.platform,
            username=request.username,
            email=request.email
        )
        
        db.add(account)
        db.commit()
        db.refresh(account)
        
        # Create session for the account
        session_data = await session_manager.new_session(
            db_session=db,
            account=account,
            proxy_string=request.proxy,
            dry=request.dry
        )
        
        logger.info(f"Created account {account.id} and session {session_data['session_id']}")
        
        return {
            "ok": True,
            "account_id": session_data["account_id"],
            "session_id": session_data["session_id"],
            "cookies_path": session_data["cookies_path"],
            "proxy_id": session_data["proxy_id"],
            "proxy": session_data["proxy"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create account: {str(e)}")


@router.post("/session/load")
async def load_session(
    request: LoadSessionRequest,
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Load the most recent session for an account."""
    try:
        account_id = extract_account_id(request.account_id)
        
        # Verify account exists and belongs to tenant
        account = db.exec(
            select(AccountSession).where(
                AccountSession.id == account_id,
                AccountSession.tenant_id == request.tenant_id
            )
        ).first()
        
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account {request.account_id} not found for tenant {request.tenant_id}"
            )
        
        # Load session
        session_data = await session_manager.load_session(db, account_id)
        
        if not session_data:
            raise HTTPException(
                status_code=404,
                detail=f"No session found for account {request.account_id}"
            )
        
        return {
            "ok": True,
            "session_id": session_data["session_id"],
            "status": session_data["status"],
            "cookies_path": session_data["cookies_path"],
            "proxy": session_data["proxy"],
            "proxy_id": session_data["proxy_id"],
            "created_at": session_data["created_at"],
            "updated_at": session_data["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load session: {str(e)}")


@router.post("/session/update")
async def update_session(
    request: UpdateSessionRequest,
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Update the status of a session."""
    try:
        session_id = extract_session_id(request.session_id)
        
        # Update session status
        success = await session_manager.update_session_status(
            db_session=db,
            session_id=session_id,
            status=request.status
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found"
            )
        
        return {
            "ok": True,
            "session_id": request.session_id,
            "status": request.status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@router.post("/proxy/assign")
async def assign_proxy(
    request: AssignProxyRequest,
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Assign a proxy to a session using least-used rotation."""
    try:
        session_id = extract_session_id(request.session_id)
        
        # Sync proxies from file to database if needed
        await proxy_manager.sync_proxies_to_database(db)
        
        # Assign proxy
        proxy_data = await session_manager.assign_proxy(db, session_id)
        
        if not proxy_data:
            raise HTTPException(
                status_code=404,
                detail="No healthy proxies available for assignment"
            )
        
        return {
            "ok": True,
            "session_id": request.session_id,
            "proxy": proxy_data["proxy"],
            "proxy_id": proxy_data["proxy_id"],
            "healthy": proxy_data["healthy"],
            "assigned_at": proxy_data["assigned_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign proxy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to assign proxy: {str(e)}")


@router.post("/captcha/solve")
async def solve_captcha_endpoint(
    request: SolveCaptchaRequest,
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Solve a captcha using the configured provider."""
    try:
        logger.info(f"Solving captcha for site_key={request.site_key}, url={request.url}, dry={request.dry}")
        
        # Create captcha job record
        captcha_job = CaptchaJob(
            tenant_id=request.tenant_id,
            provider="mock" if request.dry else "auto",
            site_key=request.site_key,
            url=request.url,
            status="processing"
        )
        
        db.add(captcha_job)
        db.commit()
        db.refresh(captcha_job)
        
        try:
            # Solve captcha
            result = await solve_captcha(
                site_key=request.site_key,
                url=request.url,
                dry=request.dry
            )
            
            if result.get("success"):
                # Update job with success
                captcha_job.status = "solved"
                captcha_job.solution = result["solution"]
                captcha_job.updated_at = datetime.utcnow()
            else:
                # Update job with error
                captcha_job.status = "failed"
                captcha_job.error = result.get("error", "Unknown error")
                captcha_job.updated_at = datetime.utcnow()
            
            db.add(captcha_job)
            db.commit()
            
            return {
                "ok": True,
                "job_id": f"cap_{captcha_job.id}",
                "status": captcha_job.status,
                "solution": captcha_job.solution,
                "provider": result.get("provider", "unknown"),
                "elapsed_seconds": result.get("elapsed_seconds", 0)
            }
            
        except Exception as solve_error:
            # Update job with error
            captcha_job.status = "failed"
            captcha_job.error = str(solve_error)
            captcha_job.updated_at = datetime.utcnow()
            db.add(captcha_job)
            db.commit()
            
            logger.error(f"Captcha solving failed: {solve_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Captcha solving failed: {str(solve_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to solve captcha: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to solve captcha: {str(e)}")


@router.get("/captcha/status")
async def get_captcha_status(
    id: str = Query(..., description="Captcha job ID (cap_xxx format)"),
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Get the status of a captcha solving job."""
    try:
        # Extract job ID
        if id.startswith("cap_"):
            job_id = int(id[4:])
        else:
            job_id = int(id)
        
        # Get captcha job
        captcha_job = db.get(CaptchaJob, job_id)
        
        if not captcha_job:
            raise HTTPException(
                status_code=404,
                detail=f"Captcha job {id} not found"
            )
        
        return {
            "ok": True,
            "job_id": f"cap_{captcha_job.id}",
            "status": captcha_job.status,
            "solution": captcha_job.solution,
            "error": captcha_job.error,
            "provider": captcha_job.provider,
            "created_at": captcha_job.created_at.isoformat(),
            "updated_at": captcha_job.updated_at.isoformat() if captcha_job.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get captcha status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get captcha status: {str(e)}")


@router.get("/stats")
async def get_account_stats(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: Session = Depends(get_session),
    _: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Get account and session statistics for a tenant."""
    try:
        # Get account counts
        accounts = db.exec(
            select(AccountSession).where(AccountSession.tenant_id == tenant_id)
        ).all()
        
        # Get session stats
        session_stats = await session_manager.get_session_stats(db, tenant_id)
        
        # Get proxy stats
        proxy_stats = await proxy_manager.health_check_all_proxies(db)
        
        return {
            "ok": True,
            "tenant_id": tenant_id,
            "accounts": {
                "total": len(accounts),
                "by_platform": {
                    platform: len([a for a in accounts if a.platform == platform])
                    for platform in set(a.platform for a in accounts)
                }
            },
            "sessions": session_stats,
            "proxies": proxy_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")