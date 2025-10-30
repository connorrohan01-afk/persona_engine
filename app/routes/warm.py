"""Account warming endpoints and logic."""

import json
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from app.security import verify_token
from app.config import settings
from app.db import get_session
from app.models import Account, WarmPlan, Session as SessionModel, Metric
from app.queue import enqueue
from app.rate import should_act, record_action, next_window
from app.utils.human import randomize_schedule, pick_subreddits, generate_comment_text, should_be_active
from providers.reddit import reddit_provider
from loguru import logger

router = APIRouter(prefix="/api/v1/warm", tags=["warming"])


class WarmPlanRequest(BaseModel):
    account_id: str
    persona_id: Optional[str] = None
    strategy: str = "default"  # default, aggressive, conservative


class WarmStartRequest(BaseModel):
    account_id: str
    persona_id: Optional[str] = None


@router.post("/plan")
async def create_warm_plan(
    request: WarmPlanRequest,
    dry: Optional[bool] = Query(default=None),
    token: str = Depends(verify_token),
    db: Session = Depends(get_session)
):
    """Create or update a warming plan for an account."""
    
    is_dry = dry if dry is not None else settings.dry_run_default
    mode = "mock" if is_dry else "live"
    
    try:
        account_id = int(request.account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account_id")
    
    # Verify account exists
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check for existing warm plan
    existing_plan = db.exec(
        select(WarmPlan).where(WarmPlan.account_id == account_id)
    ).first()
    
    if existing_plan:
        # Update existing plan
        warm_plan = existing_plan
        warm_plan.stage = "seed_profile"  # Reset to beginning
        warm_plan.next_run_at = randomize_schedule(0.5)  # Start in 30 minutes ±jitter
        warm_plan.progress_json = json.dumps({"strategy": request.strategy, "reset": True})
        warm_plan.updated_at = datetime.utcnow()
    else:
        # Create new warm plan
        warm_plan = WarmPlan(
            account_id=account_id,
            persona_id=int(request.persona_id) if request.persona_id else None,
            stage="seed_profile",
            next_run_at=randomize_schedule(0.5),  # Start in 30 minutes ±jitter
            progress_json=json.dumps({"strategy": request.strategy, "created": True})
        )
        db.add(warm_plan)
    
    db.commit()
    db.refresh(warm_plan)
    
    # Update account warm status
    account.warm_status = "planned"
    db.commit()
    
    logger.info(f"Created warm plan {warm_plan.id} for account {account_id} with strategy {request.strategy}")
    
    return {
        "ok": True,
        "mode": mode,
        "warm_plan_id": str(warm_plan.id),
        "stage": warm_plan.stage,
        "next_run_at": warm_plan.next_run_at.isoformat() if warm_plan.next_run_at else None
    }


@router.post("/start")
async def start_warming(
    request: WarmStartRequest,
    dry: Optional[bool] = Query(default=None),
    token: str = Depends(verify_token),
    db: Session = Depends(get_session)
):
    """Start the warming process for an account."""
    
    is_dry = dry if dry is not None else settings.dry_run_default
    mode = "mock" if is_dry else "live"
    
    try:
        account_id = int(request.account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account_id")
    
    # Verify account exists
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Ensure warm plan exists
    warm_plan = db.exec(
        select(WarmPlan).where(WarmPlan.account_id == account_id)
    ).first()
    
    if not warm_plan:
        # Create default warm plan
        warm_plan = WarmPlan(
            account_id=account_id,
            persona_id=int(request.persona_id) if request.persona_id else None,
            stage="seed_profile",
            next_run_at=datetime.utcnow(),
            progress_json=json.dumps({"strategy": "default", "auto_created": True})
        )
        db.add(warm_plan)
        db.commit()
        db.refresh(warm_plan)
    
    # Enqueue the first warming step
    job_id = enqueue(
        "warm_step",
        {
            "account_id": account_id,
            "tenant_id": account.tenant_id,
            "dry_run": is_dry
        },
        idempotency_key=f"warm_start_{account_id}_{datetime.utcnow().date()}",
        priority=3  # High priority for user-initiated warming
    )
    
    # Update account status
    account.warm_status = "queued"
    db.commit()
    
    logger.info(f"Started warming for account {account_id}, job {job_id}")
    
    return {
        "ok": True,
        "mode": mode,
        "status": "queued",
        "job_id": job_id
    }


@router.get("/status")
async def get_warm_status(
    account_id: str,
    token: str = Depends(verify_token),
    db: Session = Depends(get_session)
):
    """Get warming status for an account."""
    
    try:
        account_id_int = int(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account_id")
    
    # Get account and warm plan
    account = db.get(Account, account_id_int)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    warm_plan = db.exec(
        select(WarmPlan).where(WarmPlan.account_id == account_id_int)
    ).first()
    
    if not warm_plan:
        return {
            "ok": True,
            "mode": "mock" if settings.dry_run_default else "live",
            "warm_status": account.warm_status,
            "stage": None,
            "next_run_at": None,
            "progress": {}
        }
    
    # Parse progress
    try:
        progress = json.loads(warm_plan.progress_json or "{}")
    except json.JSONDecodeError:
        progress = {}
    
    return {
        "ok": True,
        "mode": "mock" if settings.dry_run_default else "live",
        "warm_status": account.warm_status,
        "stage": warm_plan.stage,
        "next_run_at": warm_plan.next_run_at.isoformat() if warm_plan.next_run_at else None,
        "progress": progress
    }


def handle_warm_step(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a warm step job.
    
    Args:
        args: Job arguments containing account_id, tenant_id, dry_run
        
    Returns:
        Result dictionary with ok, error fields
    """
    from app.db import engine
    
    account_id = args.get("account_id")
    dry_run = args.get("dry_run", settings.dry_run_default)
    
    if not account_id:
        return {"ok": False, "error": "Missing account_id"}
    
    logger.info(f"Handling warm step for account {account_id}, dry_run={dry_run}")
    
    with Session(engine) as db:
        # Load account
        account = db.get(Account, account_id)
        if not account:
            return {"ok": False, "error": "Account not found"}
        
        # Load session data
        session_data = db.exec(
            select(SessionModel).where(SessionModel.account_id == account_id)
        ).first()
        
        # Load or create warm plan
        warm_plan = db.exec(
            select(WarmPlan).where(WarmPlan.account_id == account_id)
        ).first()
        
        if not warm_plan:
            # Create default warm plan
            warm_plan = WarmPlan(
                account_id=account_id,
                stage="seed_profile",
                next_run_at=datetime.utcnow(),
                progress_json=json.dumps({"auto_created": True})
            )
            db.add(warm_plan)
            db.commit()
            db.refresh(warm_plan)
        
        # Get current stage
        current_stage = warm_plan.stage
        
        # Check if we should act based on rate limiting
        if not should_act(account_id, current_stage):
            # Schedule retry
            retry_seconds = next_window(account_id, current_stage)
            retry_time = datetime.utcnow() + timedelta(seconds=retry_seconds)
            
            enqueue(
                "warm_step",
                args,
                run_after=retry_time,
                idempotency_key=f"warm_retry_{account_id}_{current_stage}_{retry_time.isoformat()}"
            )
            
            logger.info(f"Rate limited account {account_id} stage {current_stage}, retry in {retry_seconds}s")
            return {"ok": True, "action": "rate_limited", "retry_in": retry_seconds}
        
        # Check diurnal patterns
        if not should_be_active():
            # Schedule for a more active time
            retry_hours = random.uniform(1, 4)  # 1-4 hours from now
            retry_time = randomize_schedule(retry_hours)
            
            enqueue(
                "warm_step",
                args,
                run_after=retry_time,
                idempotency_key=f"warm_sleep_{account_id}_{retry_time.isoformat()}"
            )
            
            logger.info(f"Sleep hours for account {account_id}, rescheduled to {retry_time.isoformat()}")
            return {"ok": True, "action": "sleep_hours", "retry_at": retry_time.isoformat()}
        
        # Execute stage-specific logic
        try:
            result = _execute_warm_stage(db, account, warm_plan, session_data, dry_run)
            
            # Record the action
            record_action(account_id, current_stage, {"stage": current_stage})
            
            # Update account status
            account.warm_status = "running"
            account.last_warm_at = datetime.utcnow()
            
            # Update warm plan
            warm_plan.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Completed warm step for account {account_id}, stage {current_stage}")
            return result
            
        except Exception as e:
            logger.error(f"Error in warm step for account {account_id}: {str(e)}")
            account.warm_status = "failed"
            db.commit()
            return {"ok": False, "error": str(e)}


def _execute_warm_stage(
    db: Session,
    account: Account,
    warm_plan: WarmPlan,
    session_data: Optional[SessionModel],
    dry_run: bool
) -> Dict[str, Any]:
    """Execute the logic for a specific warming stage."""
    
    stage = warm_plan.stage
    account_id = account.id
    
    # Parse existing progress
    try:
        progress = json.loads(warm_plan.progress_json or "{}")
    except json.JSONDecodeError:
        progress = {}
    
    # Get session cookies
    session_cookies = {}
    if session_data:
        try:
            session_cookies = json.loads(session_data.cookies_json or "{}")
        except json.JSONDecodeError:
            pass
    
    logger.info(f"Executing stage {stage} for account {account_id}")
    
    if stage == "seed_profile":
        return _stage_seed_profile(db, account, warm_plan, progress, dry_run)
    elif stage == "browse":
        return _stage_browse(db, account, warm_plan, progress, session_cookies, dry_run)
    elif stage == "join":
        return _stage_join(db, account, warm_plan, progress, session_cookies, dry_run)
    elif stage == "comment":
        return _stage_comment(db, account, warm_plan, progress, session_cookies, dry_run)
    elif stage == "post_light":
        return _stage_post_light(db, account, warm_plan, progress, session_cookies, dry_run)
    else:
        # Unknown stage, mark as complete
        account.warm_status = "complete"
        return {"ok": True, "action": "completed", "stage": "unknown"}


def _stage_seed_profile(db: Session, account: Account, warm_plan: WarmPlan, progress: Dict, dry_run: bool) -> Dict[str, Any]:
    """Execute seed_profile stage - select interests and safe subreddits."""
    
    # Pick safe subreddits to follow
    if "subreddits" not in progress:
        subreddits = pick_subreddits("safe", n=random.randint(5, 10))
        progress["subreddits"] = subreddits
        progress["joined_count"] = 0
    else:
        subreddits = progress["subreddits"]
    
    logger.info(f"Seed profile stage: selected {len(subreddits)} safe subreddits")
    
    # Schedule next stage (browse) in 1-3 hours
    next_stage_time = randomize_schedule(random.uniform(1, 3))
    
    # Update warm plan
    warm_plan.stage = "browse"
    warm_plan.next_run_at = next_stage_time
    warm_plan.progress_json = json.dumps(progress)
    
    # Record metric
    metric = Metric(
        tenant_id=account.tenant_id,
        key="warm.seed_profile",
        value_num=1,
        meta_json=json.dumps({"account_id": account.id, "subreddits_count": len(subreddits)})
    )
    db.add(metric)
    
    # Enqueue next stage
    enqueue(
        "warm_step",
        {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
        run_after=next_stage_time,
        idempotency_key=f"warm_browse_{account.id}_{next_stage_time.isoformat()}"
    )
    
    return {
        "ok": True,
        "action": "seed_profile_completed",
        "subreddits_selected": len(subreddits),
        "next_stage": "browse",
        "next_run_at": next_stage_time.isoformat()
    }


def _stage_browse(db: Session, account: Account, warm_plan: WarmPlan, progress: Dict, session_cookies: Dict, dry_run: bool) -> Dict[str, Any]:
    """Execute browse stage - browse feeds and interact lightly."""
    
    subreddits = progress.get("subreddits", ["askreddit", "pics", "funny"])
    browse_count = progress.get("browse_count", 0)
    target_browses = progress.get("target_browses", 5)
    
    # Pick a random subreddit to browse
    subreddit = random.choice(subreddits)
    
    # Browse the feed
    feed_result = reddit_provider.browse_feed(session_cookies, subreddit)
    if not feed_result.get("ok"):
        logger.warning(f"Failed to browse r/{subreddit}: {feed_result.get('error', 'Unknown error')}")
    else:
        posts = feed_result.get("posts", [])
        logger.info(f"Browsed r/{subreddit}, found {len(posts)} posts")
        
        # Randomly interact with 1-3 posts
        interaction_count = min(random.randint(1, 3), len(posts))
        for i in range(interaction_count):
            post = random.choice(posts)
            
            # Randomly choose action (upvote or save)
            if random.random() < 0.7:  # 70% chance to upvote
                reddit_provider.upvote(session_cookies, post["id"])
                logger.debug(f"Upvoted post {post['id']}")
            elif random.random() < 0.3:  # 30% chance to save
                reddit_provider.save(session_cookies, post["id"])
                logger.debug(f"Saved post {post['id']}")
    
    # Update progress
    browse_count += 1
    progress["browse_count"] = browse_count
    progress[f"browsed_{subreddit}"] = progress.get(f"browsed_{subreddit}", 0) + 1
    
    if browse_count >= target_browses:
        # Move to join stage
        next_stage_time = randomize_schedule(random.uniform(1, 2))
        warm_plan.stage = "join"
        warm_plan.next_run_at = next_stage_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_stage_time,
            idempotency_key=f"warm_join_{account.id}_{next_stage_time.isoformat()}"
        )
        
        next_stage = "join"
        next_run_at = next_stage_time.isoformat()
    else:
        # Schedule another browse
        next_browse_time = randomize_schedule(random.uniform(0.5, 1.5))
        warm_plan.next_run_at = next_browse_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_browse_time,
            idempotency_key=f"warm_browse_{account.id}_{next_browse_time.isoformat()}"
        )
        
        next_stage = "browse"
        next_run_at = next_browse_time.isoformat()
    
    warm_plan.progress_json = json.dumps(progress)
    
    # Record metric
    metric = Metric(
        tenant_id=account.tenant_id,
        key="warm.browse",
        value_num=1,
        meta_json=json.dumps({"account_id": account.id, "subreddit": subreddit, "interactions": interaction_count})
    )
    db.add(metric)
    
    return {
        "ok": True,
        "action": "browse_completed",
        "subreddit": subreddit,
        "browse_count": browse_count,
        "target_browses": target_browses,
        "next_stage": next_stage,
        "next_run_at": next_run_at
    }


def _stage_join(db: Session, account: Account, warm_plan: WarmPlan, progress: Dict, session_cookies: Dict, dry_run: bool) -> Dict[str, Any]:
    """Execute join stage - gradually join subreddits."""
    
    subreddits = progress.get("subreddits", [])
    joined_count = progress.get("joined_count", 0)
    target_joins = min(5, len(subreddits))  # Join up to 5 subreddits
    
    if joined_count >= target_joins:
        # Move to comment stage
        next_stage_time = randomize_schedule(random.uniform(2, 4))
        warm_plan.stage = "comment"
        warm_plan.next_run_at = next_stage_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_stage_time,
            idempotency_key=f"warm_comment_{account.id}_{next_stage_time.isoformat()}"
        )
        
        return {
            "ok": True,
            "action": "join_completed",
            "joined_count": joined_count,
            "next_stage": "comment",
            "next_run_at": next_stage_time.isoformat()
        }
    
    # Pick a subreddit to join
    remaining_subreddits = [s for s in subreddits if s not in progress.get("joined", [])]
    if not remaining_subreddits:
        # All subreddits joined, move to next stage early
        return _advance_to_next_stage(db, account, warm_plan, progress, "comment", dry_run)
    
    subreddit = random.choice(remaining_subreddits)
    
    # Join the subreddit
    if reddit_provider.join_subreddit(session_cookies, subreddit):
        joined_list = progress.get("joined", [])
        joined_list.append(subreddit)
        progress["joined"] = joined_list
        joined_count += 1
        progress["joined_count"] = joined_count
        
        logger.info(f"Joined r/{subreddit} ({joined_count}/{target_joins})")
    
    # Schedule next join or move to next stage
    if joined_count >= target_joins:
        next_stage_time = randomize_schedule(random.uniform(2, 4))
        warm_plan.stage = "comment"
        warm_plan.next_run_at = next_stage_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_stage_time,
            idempotency_key=f"warm_comment_{account.id}_{next_stage_time.isoformat()}"
        )
        
        next_stage = "comment"
        next_run_at = next_stage_time.isoformat()
    else:
        # Schedule another join
        next_join_time = randomize_schedule(random.uniform(1, 2))
        warm_plan.next_run_at = next_join_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_join_time,
            idempotency_key=f"warm_join_{account.id}_{next_join_time.isoformat()}"
        )
        
        next_stage = "join"
        next_run_at = next_join_time.isoformat()
    
    warm_plan.progress_json = json.dumps(progress)
    
    # Record metric
    metric = Metric(
        tenant_id=account.tenant_id,
        key="warm.join",
        value_num=1,
        meta_json=json.dumps({"account_id": account.id, "subreddit": subreddit, "joined_count": joined_count})
    )
    db.add(metric)
    
    return {
        "ok": True,
        "action": "join_completed",
        "subreddit": subreddit,
        "joined_count": joined_count,
        "target_joins": target_joins,
        "next_stage": next_stage,
        "next_run_at": next_run_at
    }


def _stage_comment(db: Session, account: Account, warm_plan: WarmPlan, progress: Dict, session_cookies: Dict, dry_run: bool) -> Dict[str, Any]:
    """Execute comment stage - leave light, positive comments."""
    
    joined_subreddits = progress.get("joined", progress.get("subreddits", ["askreddit"]))
    comment_count = progress.get("comment_count", 0)
    target_comments = progress.get("target_comments", 3)
    
    if comment_count >= target_comments:
        # Move to post_light stage
        next_stage_time = randomize_schedule(random.uniform(6, 12))  # Wait longer before posting
        warm_plan.stage = "post_light"
        warm_plan.next_run_at = next_stage_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_stage_time,
            idempotency_key=f"warm_post_{account.id}_{next_stage_time.isoformat()}"
        )
        
        return {
            "ok": True,
            "action": "comment_completed",
            "comment_count": comment_count,
            "next_stage": "post_light",
            "next_run_at": next_stage_time.isoformat()
        }
    
    # Pick a subreddit and browse for posts to comment on
    subreddit = random.choice(joined_subreddits)
    feed_result = reddit_provider.browse_feed(session_cookies, subreddit)
    
    if feed_result.get("ok"):
        posts = feed_result.get("posts", [])
        if posts:
            # Pick a post to comment on
            post = random.choice(posts)
            
            # Generate a positive, helpful comment
            comment_text = generate_comment_text("positive")
            
            # Post the comment
            comment_result = reddit_provider.comment(session_cookies, post["id"], comment_text)
            
            if comment_result.get("ok"):
                comment_count += 1
                progress["comment_count"] = comment_count
                progress[f"commented_{subreddit}"] = progress.get(f"commented_{subreddit}", 0) + 1
                
                logger.info(f"Posted comment in r/{subreddit}: {comment_text}")
    
    # Schedule next comment or move to next stage
    if comment_count >= target_comments:
        next_stage_time = randomize_schedule(random.uniform(6, 12))
        warm_plan.stage = "post_light"
        warm_plan.next_run_at = next_stage_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_stage_time,
            idempotency_key=f"warm_post_{account.id}_{next_stage_time.isoformat()}"
        )
        
        next_stage = "post_light"
        next_run_at = next_stage_time.isoformat()
    else:
        # Schedule another comment
        next_comment_time = randomize_schedule(random.uniform(12, 24))  # Comments are spaced out
        warm_plan.next_run_at = next_comment_time
        
        enqueue(
            "warm_step",
            {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
            run_after=next_comment_time,
            idempotency_key=f"warm_comment_{account.id}_{next_comment_time.isoformat()}"
        )
        
        next_stage = "comment"
        next_run_at = next_comment_time.isoformat()
    
    warm_plan.progress_json = json.dumps(progress)
    
    # Record metric
    metric = Metric(
        tenant_id=account.tenant_id,
        key="warm.comment",
        value_num=1,
        meta_json=json.dumps({"account_id": account.id, "subreddit": subreddit, "comment_count": comment_count})
    )
    db.add(metric)
    
    return {
        "ok": True,
        "action": "comment_completed",
        "subreddit": subreddit,
        "comment_count": comment_count,
        "target_comments": target_comments,
        "next_stage": next_stage,
        "next_run_at": next_run_at
    }


def _stage_post_light(db: Session, account: Account, warm_plan: WarmPlan, progress: Dict, session_cookies: Dict, dry_run: bool) -> Dict[str, Any]:
    """Execute post_light stage - make one safe post."""
    
    joined_subreddits = progress.get("joined", progress.get("subreddits", ["test"]))
    post_count = progress.get("post_count", 0)
    target_posts = 1  # Only one post in light warming
    
    if post_count >= target_posts:
        # Warming complete
        account.warm_status = "complete"
        
        # Record completion metric
        metric = Metric(
            tenant_id=account.tenant_id,
            key="warm.completed",
            value_num=1,
            meta_json=json.dumps({"account_id": account.id, "stages_completed": ["seed_profile", "browse", "join", "comment", "post_light"]})
        )
        db.add(metric)
        
        return {
            "ok": True,
            "action": "warming_completed",
            "post_count": post_count,
            "status": "complete"
        }
    
    # Pick a safe subreddit for posting
    safe_post_subs = ["test", "FreeKarma4U", "CasualConversation"] 
    available_subs = [s for s in safe_post_subs if s in joined_subreddits] or ["test"]
    subreddit = random.choice(available_subs)
    
    # Enqueue a post job (handled separately for more control)
    enqueue(
        "post_job",
        {
            "account_id": account.id,
            "tenant_id": account.tenant_id,
            "subreddit": subreddit,
            "post_type": "text",
            "dry_run": dry_run
        },
        priority=4  # Lower priority than warming steps
    )
    
    # Update progress
    post_count += 1
    progress["post_count"] = post_count
    progress["post_scheduled"] = True
    warm_plan.progress_json = json.dumps(progress)
    
    # Mark as complete
    account.warm_status = "complete"
    
    logger.info(f"Scheduled post job for account {account.id} in r/{subreddit}")
    
    # Record metric
    metric = Metric(
        tenant_id=account.tenant_id,
        key="warm.post_light",
        value_num=1,
        meta_json=json.dumps({"account_id": account.id, "subreddit": subreddit})
    )
    db.add(metric)
    
    return {
        "ok": True,
        "action": "post_scheduled",
        "subreddit": subreddit,
        "status": "complete"
    }


def _advance_to_next_stage(db: Session, account: Account, warm_plan: WarmPlan, progress: Dict, next_stage: str, dry_run: bool) -> Dict[str, Any]:
    """Helper to advance to the next warming stage."""
    
    stage_delays = {
        "browse": random.uniform(0.5, 1.5),
        "join": random.uniform(1, 3),
        "comment": random.uniform(2, 6),
        "post_light": random.uniform(6, 12)
    }
    
    delay_hours = stage_delays.get(next_stage, 1)
    next_stage_time = randomize_schedule(delay_hours)
    
    warm_plan.stage = next_stage
    warm_plan.next_run_at = next_stage_time
    
    enqueue(
        "warm_step",
        {"account_id": account.id, "tenant_id": account.tenant_id, "dry_run": dry_run},
        run_after=next_stage_time,
        idempotency_key=f"warm_{next_stage}_{account.id}_{next_stage_time.isoformat()}"
    )
    
    return {
        "ok": True,
        "action": f"advanced_to_{next_stage}",
        "next_stage": next_stage,
        "next_run_at": next_stage_time.isoformat()
    }