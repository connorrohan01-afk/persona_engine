"""Core warming engine with scheduler/executor logic."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models_warming import WarmingPlan, WarmingAction, WarmingRun, WarmingLog
from app.models_accounts import AccountSession, SessionRecord, Proxy
from app.rand import (
    WeightedItem, weighted_random_sample, jitter_seconds, sleep_with_jitter,
    is_time_in_window, exponential_backoff_delay
)
from app.providers.reddit import get_reddit_provider
from app.sessions import SessionManager
from app.rate import should_act, record_action
import app.queue

logger = logging.getLogger(__name__)


class WarmingEngine:
    """Core warming engine for automated account warming."""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.reddit_provider = get_reddit_provider()
        
    async def run_eligible_plans(
        self, 
        tenant_id: str, 
        limit_plans: int = 5, 
        dry: bool = False
    ) -> Dict[str, Any]:
        """Run warming actions for eligible plans.
        
        Args:
            tenant_id: Tenant identifier
            limit_plans: Maximum number of plans to process
            dry: Force dry mode
            
        Returns:
            Dict with run results
        """
        # Override dry mode if DRY_DEFAULT is set
        if settings.dry_default and not dry:
            dry = True
            
        mode = "dry" if dry else "live"
        logger.info(f"Running warming engine for tenant {tenant_id} (mode={mode}, limit={limit_plans})")
        
        runs = []
        
        with Session(engine) as db:
            eligible_plans = self._get_eligible_plans(db, tenant_id, limit_plans)
            
            for plan in eligible_plans:
                try:
                    run_result = await self._execute_plan(db, plan, dry)
                    runs.append(run_result)
                    
                except Exception as e:
                    logger.error(f"Failed to execute warming plan {plan.id}: {e}")
                    # Create failed run record
                    failed_run = WarmingRun(
                        plan_id=plan.id or 0,
                        started_at=datetime.utcnow(),
                        finished_at=datetime.utcnow(),
                        actions_attempted=0,
                        actions_succeeded=0,
                        mode=mode
                    )
                    db.add(failed_run)
                    db.commit()
                    
                    runs.append({
                        "plan_id": plan.id,
                        "run_id": failed_run.id,
                        "attempted": 0,
                        "succeeded": 0,
                        "error": str(e)
                    })
        
        return {
            "ok": True,
            "mode": mode,
            "runs": runs
        }
    
    async def run_specific_plan(
        self, 
        plan_id: int, 
        limit_actions: int = 20, 
        dry: bool = False
    ) -> Dict[str, Any]:
        """Run warming actions for a specific plan.
        
        Args:
            plan_id: Plan ID to execute
            limit_actions: Maximum actions to run
            dry: Force dry mode
            
        Returns:
            Dict with run results
        """
        # Override dry mode if DRY_DEFAULT is set
        if settings.dry_default and not dry:
            dry = True
            
        mode = "dry" if dry else "live"
        
        with Session(engine) as db:
            plan = db.get(WarmingPlan, plan_id)
            if not plan:
                return {
                    "ok": False,
                    "mode": mode,
                    "error": "Plan not found"
                }
            
            if not plan.enabled:
                return {
                    "ok": False,
                    "mode": mode,
                    "error": "Plan is disabled"
                }
            
            try:
                result = await self._execute_plan(db, plan, dry, limit_actions)
                return {
                    "ok": True,
                    "mode": mode,
                    **result
                }
            except Exception as e:
                logger.error(f"Failed to execute warming plan {plan_id}: {e}")
                return {
                    "ok": False,
                    "mode": mode,
                    "error": str(e)
                }
    
    def _get_eligible_plans(self, db: Session, tenant_id: str, limit: int) -> List[WarmingPlan]:
        """Get plans eligible for execution."""
        now = datetime.utcnow()
        
        # Get plans that are enabled and within time window
        plans = db.exec(
            select(WarmingPlan)
            .where(
                WarmingPlan.tenant_id == tenant_id,
                WarmingPlan.enabled == True
            )
            .limit(limit)
        ).all()
        
        eligible = []
        
        for plan in plans:
            # Check if current time is within plan window
            if not is_time_in_window(now, plan.window_start, plan.window_end):
                logger.debug(f"Plan {plan.id} outside time window {plan.window_start}-{plan.window_end}")
                continue
            
            # Check account cooldown
            if not self._is_account_ready(db, plan.account_id):
                logger.debug(f"Plan {plan.id} account {plan.account_id} in cooldown")
                continue
            
            eligible.append(plan)
        
        return eligible
    
    def _is_account_ready(self, db: Session, account_id: str) -> bool:
        """Check if account is ready for warming actions."""
        # Check if account has had recent warming activity
        cooldown_minutes = settings.warm_minutes_between_same_account
        cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        
        recent_logs = db.exec(
            select(WarmingLog)
            .where(
                WarmingLog.account_id == account_id,
                WarmingLog.ts > cutoff_time
            )
            .limit(1)
        ).first()
        
        return recent_logs is None
    
    async def _execute_plan(
        self, 
        db: Session, 
        plan: WarmingPlan, 
        dry: bool, 
        limit_actions: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute warming actions for a plan."""
        mode = "dry" if dry else "live"
        limit_actions = limit_actions or settings.warm_max_actions_per_run
        
        # Create run record
        run = WarmingRun(
            plan_id=plan.id or 0,
            started_at=datetime.utcnow(),
            actions_attempted=0,
            actions_succeeded=0,
            mode=mode
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        
        logger.info(f"Starting warming run {run.id} for plan {plan.id} (dry={dry})")
        
        try:
            # Get enabled actions for this plan
            actions = db.exec(
                select(WarmingAction)
                .where(
                    WarmingAction.plan_id == plan.id,
                    WarmingAction.enabled == True
                )
            ).all()
            
            if not actions:
                logger.warning(f"No enabled actions found for plan {plan.id}")
                run.finished_at = datetime.utcnow()
                db.commit()
                return {
                    "run_id": run.id,
                    "attempted": 0,
                    "succeeded": 0,
                    "logs": []
                }
            
            # Select actions using weighted random sampling
            weighted_actions = [
                WeightedItem(item=action, weight=action.weight)
                for action in actions
            ]
            
            selected_actions = weighted_random_sample(weighted_actions, limit_actions)
            
            # Execute actions with jitter between them
            logs = []
            succeeded = 0
            
            for i, action in enumerate(selected_actions):
                try:
                    # Add jitter between actions (except first)
                    if i > 0:
                        await sleep_with_jitter(
                            base_seconds=0,
                            min_jitter=settings.warm_jitter_seconds_min,
                            max_jitter=settings.warm_jitter_seconds_max
                        )
                    
                    # Execute the action
                    log_entry = await self._execute_action(db, run, plan.account_id, action, dry)
                    logs.append(log_entry)
                    
                    if log_entry["status"] in ["ok", "skipped"]:
                        succeeded += 1
                    
                    # If we hit a rate limit or captcha, stop processing
                    if log_entry.get("error_code") in ["rate_limited", "captcha_required"]:
                        logger.warning(f"Stopping plan {plan.id} due to {log_entry['error_code']}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error executing action {action.id}: {e}")
                    log_entry = {
                        "action_kind": action.kind,
                        "status": "failed",
                        "error": str(e),
                        "error_code": "internal"
                    }
                    logs.append(log_entry)
            
            # Update run record
            run.actions_attempted = len(selected_actions)
            run.actions_succeeded = succeeded
            run.finished_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Completed warming run {run.id}: {succeeded}/{len(selected_actions)} succeeded")
            
            return {
                "run_id": run.id,
                "attempted": len(selected_actions),
                "succeeded": succeeded,
                "logs": logs
            }
            
        except Exception as e:
            # Mark run as finished with error
            run.finished_at = datetime.utcnow()
            db.commit()
            raise
    
    async def _execute_action(
        self, 
        db: Session, 
        run: WarmingRun, 
        account_id: str, 
        action: WarmingAction, 
        dry: bool
    ) -> Dict[str, Any]:
        """Execute a single warming action."""
        logger.debug(f"Executing action {action.kind} for account {account_id} (dry={dry})")
        
        # Create log entry
        log = WarmingLog(
            run_id=run.id or 0,
            account_id=account_id,
            action_kind=action.kind,
            status="failed",  # Will update on success
            ts=datetime.utcnow()
        )
        
        try:
            # Check rate limits first
            if not dry and not should_act(int(account_id), action.kind):
                log.status = "skipped"
                log.error = "rate_limited"
                db.add(log)
                db.commit()
                
                return {
                    "action_kind": action.kind,
                    "status": "skipped",
                    "error": "rate_limited",
                    "error_code": "rate_limited"
                }
            
            # Ensure account session exists
            session_data = await self._ensure_account_session(db, account_id, dry)
            
            # Execute action based on kind
            result = await self._dispatch_action(action, session_data, dry)
            
            # Record action for rate limiting (if not dry)
            if not dry:
                record_action(int(account_id), action.kind)
            
            # Update log
            log.status = "skipped" if dry else "ok"
            log.meta = result.get("meta", {})
            db.add(log)
            db.commit()
            
            return {
                "action_kind": action.kind,
                "status": log.status,
                **result
            }
            
        except Exception as e:
            # Log error
            log.status = "failed"
            log.error = str(e)
            db.add(log)
            db.commit()
            
            error_code = "internal"
            if "rate" in str(e).lower():
                error_code = "rate_limited"
            elif "captcha" in str(e).lower():
                error_code = "captcha_required"
            
            return {
                "action_kind": action.kind,
                "status": "failed",
                "error": str(e),
                "error_code": error_code
            }
    
    async def _ensure_account_session(self, db: Session, account_id: str, dry: bool) -> Dict[str, Any]:
        """Ensure account has an active session."""
        # Get account
        account = db.exec(
            select(AccountSession)
            .where(AccountSession.id == int(account_id))
        ).first()
        
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        # Get or create session record
        session_record = db.exec(
            select(SessionRecord)
            .where(
                SessionRecord.account_id == int(account_id),
                SessionRecord.status == "active"
            )
        ).first()
        
        if not session_record:
            # Create new session
            session_data = await self.session_manager.new_session(
                db_session=db,
                account=account,
                proxy_string=None,
                dry=dry
            )
            return session_data
        
        # Load existing session
        session_data = await self.session_manager.load_session(
            db_session=db,
            account_id=int(account_id)
        )
        
        if session_data is None:
            # Create new session if loading failed
            return await self.session_manager.new_session(
                db_session=db,
                account=account,
                proxy_string=None,
                dry=dry
            )
        
        return session_data
    
    async def _dispatch_action(
        self, 
        action: WarmingAction, 
        session_data: Dict[str, Any], 
        dry: bool
    ) -> Dict[str, Any]:
        """Dispatch action to appropriate handler."""
        params = action.params
        
        if action.kind == "view_sub":
            return await self._action_view_sub(params, session_data, dry)
        elif action.kind == "upvote":
            return await self._action_upvote(params, session_data, dry)
        elif action.kind == "comment_short":
            return await self._action_comment_short(params, session_data, dry)
        elif action.kind == "post_text":
            return await self._action_post_text(params, session_data, dry)
        elif action.kind == "post_image":
            return await self._action_post_image(params, session_data, dry)
        elif action.kind == "save_post":
            return await self._action_save_post(params, session_data, dry)
        else:
            raise ValueError(f"Unknown action kind: {action.kind}")
    
    async def _action_view_sub(self, params: Dict[str, Any], session_data: Dict[str, Any], dry: bool) -> Dict[str, Any]:
        """Execute view_sub action (scrape subreddit)."""
        subreddit = params.get("subreddit", "test")
        limit = params.get("limit", 5)
        sort = params.get("sort", "hot")
        
        if dry:
            return {
                "meta": {
                    "subreddit": subreddit,
                    "limit": limit,
                    "sort": sort,
                    "posts_viewed": limit
                }
            }
        
        # Use Reddit provider to scrape
        posts = await self.reddit_provider.get_posts(
            subreddit=subreddit,
            sort=sort,
            limit=limit
        )
        
        return {
            "meta": {
                "subreddit": subreddit,
                "limit": limit,
                "sort": sort,
                "posts_viewed": len(posts)
            }
        }
    
    async def _action_upvote(self, params: Dict[str, Any], session_data: Dict[str, Any], dry: bool) -> Dict[str, Any]:
        """Execute upvote action."""
        post_id = params.get("post_id", "t3_mock123")
        
        if dry:
            return {
                "meta": {
                    "post_id": post_id,
                    "action": "upvote"
                }
            }
        
        # In live mode, would call Reddit API
        # For now, simulate success
        return {
            "meta": {
                "post_id": post_id,
                "action": "upvote"
            }
        }
    
    async def _action_comment_short(self, params: Dict[str, Any], session_data: Dict[str, Any], dry: bool) -> Dict[str, Any]:
        """Execute comment_short action."""
        post_id = params.get("post_id", "t3_mock123")
        body = params.get("body", "Thanks for sharing!")
        
        if dry:
            return {
                "meta": {
                    "post_id": post_id,
                    "body": body,
                    "comment_id": "t1_mock456"
                }
            }
        
        # In live mode, would call Reddit API
        return {
            "meta": {
                "post_id": post_id,
                "body": body,
                "comment_id": f"t1_live_{datetime.utcnow().timestamp():.0f}"
            }
        }
    
    async def _action_post_text(self, params: Dict[str, Any], session_data: Dict[str, Any], dry: bool) -> Dict[str, Any]:
        """Execute post_text action."""
        subreddit = params.get("subreddit", "test")
        title = params.get("title", "Warming post")
        body = params.get("body", "Just warming up the account")
        
        if dry:
            return {
                "meta": {
                    "subreddit": subreddit,
                    "title": title,
                    "body": body,
                    "post_id": "t3_mock789"
                }
            }
        
        # Use Reddit provider to post
        result = self.reddit_provider.submit_post(
            session_data=session_data,
            subreddit=subreddit,
            kind="text",
            title=title,
            body=body
        )
        
        return {
            "meta": {
                "subreddit": subreddit,
                "title": title,
                "body": body,
                "post_id": result.get("post_id")
            }
        }
    
    async def _action_post_image(self, params: Dict[str, Any], session_data: Dict[str, Any], dry: bool) -> Dict[str, Any]:
        """Execute post_image action."""
        subreddit = params.get("subreddit", "test")
        title = params.get("title", "Image post")
        image_url = params.get("image_url", "https://example.com/image.jpg")
        
        if dry:
            return {
                "meta": {
                    "subreddit": subreddit,
                    "title": title,
                    "image_url": image_url,
                    "post_id": "t3_mock890"
                }
            }
        
        # Use Reddit provider to post image
        result = self.reddit_provider.submit_post(
            session_data=session_data,
            subreddit=subreddit,
            kind="image",
            title=title,
            image_url=image_url,
            dry_run=False
        )
        
        return {
            "meta": {
                "subreddit": subreddit,
                "title": title,
                "image_url": image_url,
                "post_id": result.get("post_id")
            }
        }
    
    async def _action_save_post(self, params: Dict[str, Any], session_data: Dict[str, Any], dry: bool) -> Dict[str, Any]:
        """Execute save_post action."""
        post_id = params.get("post_id", "t3_mock123")
        
        if dry:
            return {
                "meta": {
                    "post_id": post_id,
                    "action": "save"
                }
            }
        
        # In live mode, would call Reddit API
        return {
            "meta": {
                "post_id": post_id,
                "action": "save"
            }
        }


# Global warming engine instance
warming_engine = WarmingEngine()