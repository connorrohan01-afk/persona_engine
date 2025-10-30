"""Rate limiting and pacing system for account actions."""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlmodel import Session, select
from app.db import engine
from app.models import Account, Metric
from app.config import settings
from loguru import logger


# Default action limits and intervals (in minutes) with Reddit-specific values
DEFAULT_LIMITS = {
    "browse": {
        "min_interval": 5,    # 5-10 minutes between browse actions
        "max_interval": 10,
        "daily_cap": 50,      # Max 50 browse actions per day
    },
    "vote": {
        "min_interval": 2,    # 2-5 minutes between votes
        "max_interval": 5,
        "daily_cap": 30,      # Max 30 votes per day
    },
    "comment": {
        "min_interval": 15,   # 15-30 minutes between comments
        "max_interval": 30,
        "daily_cap": 5,       # Max 5 comments per day (conservative for Reddit)
    },
    "post": {
        "min_interval": 120,  # 2-4 hours between posts (very conservative)
        "max_interval": 240,
        "daily_cap": 2,       # Max 2 posts per day (very conservative for Reddit)
    },
    "join": {
        "min_interval": 30,   # 30-60 minutes between joins
        "max_interval": 60,
        "daily_cap": 5,       # Max 5 joins per day
    },
    "save": {
        "min_interval": 3,    # 3-8 minutes between saves
        "max_interval": 8,
        "daily_cap": 20,      # Max 20 saves per day
    }
}

# Reddit-specific per-subreddit posting intervals (hours)
REDDIT_SUBREDDIT_INTERVALS = {
    "min_hours": 24,      # Minimum 24 hours between posts to same subreddit
    "max_hours": 48,      # Maximum 48 hours for conservative accounts
}

# Cooldown periods after rate limits or bans (minutes)
REDDIT_COOLDOWNS = {
    "ratelimit": {
        "base_minutes": 10,   # Base cooldown after rate limit
        "max_minutes": 360,   # Max 6 hours cooldown
        "multiplier": 2,      # Double cooldown each time
    },
    "shadowban": {
        "cooldown_hours": 72,  # 72 hour cooldown if shadowban suspected
    },
    "captcha": {
        "cooldown_minutes": 60,  # 1 hour cooldown after captcha required
    },
}

# Diurnal schedule: more active during "awake" hours
DIURNAL_SCHEDULE = {
    "active_start": 9,    # 9 AM local time
    "active_end": 23,     # 11 PM local time
    "sleep_multiplier": 3.0,  # 3x longer intervals during sleep hours
    "active_boost": 0.8,  # 20% shorter intervals during active hours
}


def should_act(account_id: int, kind: str) -> bool:
    """
    Check if an account should be allowed to perform an action.
    
    Args:
        account_id: Account ID to check
        kind: Type of action (browse, vote, comment, post, join, save)
        
    Returns:
        True if action is allowed, False otherwise
    """
    if kind not in DEFAULT_LIMITS:
        logger.warning(f"Unknown action kind: {kind}")
        return True  # Allow unknown actions by default
    
    limits = DEFAULT_LIMITS[kind]
    
    # Check daily cap
    if _check_daily_cap_exceeded(account_id, kind, limits["daily_cap"]):
        logger.debug(f"Daily cap exceeded for account {account_id}, kind {kind}")
        return False
    
    # Check minimum interval
    if _check_min_interval_violated(account_id, kind, limits):
        logger.debug(f"Minimum interval violated for account {account_id}, kind {kind}")
        return False
    
    # Check diurnal schedule (quieter at night)
    if _is_sleep_hours():
        # During sleep hours, apply additional restrictions
        if random.random() < 0.7:  # 70% chance to skip action during sleep
            logger.debug(f"Skipping action during sleep hours for account {account_id}, kind {kind}")
            return False
    
    return True


def next_window(account_id: int, kind: str) -> int:
    """
    Calculate seconds until next allowed action for an account.
    
    Args:
        account_id: Account ID
        kind: Type of action
        
    Returns:
        Seconds until next action is allowed
    """
    if kind not in DEFAULT_LIMITS:
        return 0
    
    limits = DEFAULT_LIMITS[kind]
    
    # Get last action time
    last_action = _get_last_action_time(account_id, kind)
    if not last_action:
        return 0  # No previous action, can act now
    
    # Calculate base interval with jitter
    base_interval = random.randint(limits["min_interval"], limits["max_interval"])
    
    # Apply diurnal adjustments
    if _is_sleep_hours():
        base_interval = int(base_interval * DIURNAL_SCHEDULE["sleep_multiplier"])
    else:
        base_interval = int(base_interval * DIURNAL_SCHEDULE["active_boost"])
    
    # Calculate when next action is allowed
    next_allowed = last_action + timedelta(minutes=base_interval)
    now = datetime.utcnow()
    
    if next_allowed <= now:
        return 0  # Can act now
    
    return int((next_allowed - now).total_seconds())


def record_action(account_id: int, kind: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """
    Record that an account performed an action.
    
    Args:
        account_id: Account ID
        kind: Type of action
        meta: Optional metadata about the action
    """
    with Session(engine) as session:
        # Get account for tenant_id
        account = session.get(Account, account_id)
        if not account:
            logger.error(f"Account {account_id} not found for recording action")
            return
        
        # Create metric entry
        metric = Metric(
            tenant_id=account.tenant_id,
            persona_id=None,  # Could link to persona if available
            key=f"action.{kind}",
            value_num=1.0,
            meta_json=json.dumps({
                "account_id": account_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(meta or {})
            })
        )
        
        session.add(metric)
        session.commit()
        
        logger.info(f"Recorded action {kind} for account {account_id}")


def get_action_stats(account_id: int, kind: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get action statistics for an account.
    
    Args:
        account_id: Account ID
        kind: Type of action
        hours: Time window in hours
        
    Returns:
        Dictionary with action statistics
    """
    with Session(engine) as session:
        # Get actions within time window
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = session.exec(
            select(Metric).where(
                Metric.key == f"action.{kind}",
                Metric.created_at >= cutoff
            )
        ).all()
        
        # Filter by account_id from meta_json
        account_metrics = []
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    account_metrics.append(metric)
            except json.JSONDecodeError:
                continue
        
        total_actions = len(account_metrics)
        daily_cap = DEFAULT_LIMITS.get(kind, {}).get("daily_cap", 0)
        
        # Get last action time
        last_action = None
        if account_metrics:
            last_action = max(m.created_at for m in account_metrics).isoformat()
        
        return {
            "kind": kind,
            "total_actions": total_actions,
            "daily_cap": daily_cap,
            "remaining": max(0, daily_cap - total_actions),
            "last_action": last_action,
            "can_act": should_act(account_id, kind),
            "next_window_seconds": next_window(account_id, kind) if not should_act(account_id, kind) else 0
        }


def _check_daily_cap_exceeded(account_id: int, kind: str, daily_cap: int) -> bool:
    """Check if daily action cap is exceeded."""
    with Session(engine) as session:
        # Count actions in last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        metrics = session.exec(
            select(Metric).where(
                Metric.key == f"action.{kind}",
                Metric.created_at >= cutoff
            )
        ).all()
        
        # Count actions for this account
        count = 0
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    count += 1
            except json.JSONDecodeError:
                continue
        
        return count >= daily_cap


def _check_min_interval_violated(account_id: int, kind: str, limits: Dict[str, Any]) -> bool:
    """Check if minimum interval between actions is violated."""
    last_action = _get_last_action_time(account_id, kind)
    if not last_action:
        return False  # No previous action
    
    # Calculate minimum required interval with diurnal adjustment
    min_interval = limits["min_interval"]
    if _is_sleep_hours():
        min_interval = int(min_interval * DIURNAL_SCHEDULE["sleep_multiplier"])
    else:
        min_interval = int(min_interval * DIURNAL_SCHEDULE["active_boost"])
    
    min_next_time = last_action + timedelta(minutes=min_interval)
    return datetime.utcnow() < min_next_time


def _get_last_action_time(account_id: int, kind: str) -> Optional[datetime]:
    """Get the timestamp of the last action for an account."""
    with Session(engine) as session:
        # Get most recent action
        metrics = session.exec(
            select(Metric).where(
                Metric.key == f"action.{kind}"
            ).order_by(Metric.created_at.desc()).limit(20)  # Check last 20
        ).all()
        
        # Find most recent for this account
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    return metric.created_at
            except json.JSONDecodeError:
                continue
        
        return None


def _is_sleep_hours() -> bool:
    """Check if current time is during sleep hours (simplified UTC-based)."""
    current_hour = datetime.utcnow().hour
    
    # Simple check: assume UTC time, sleep from 0-8 and active 9-23
    active_start = DIURNAL_SCHEDULE["active_start"]
    active_end = DIURNAL_SCHEDULE["active_end"]
    
    return current_hour < active_start or current_hour > active_end


def reset_action_limits(account_id: int) -> Dict[str, Any]:
    """
    Reset action limits for an account (admin function).
    
    Args:
        account_id: Account ID to reset
        
    Returns:
        Reset status
    """
    # This is a mock implementation - in production might clear recent metrics
    # or mark them as "reset" to allow immediate actions
    
    logger.warning(f"Action limits reset requested for account {account_id}")
    
    with Session(engine) as session:
        # Record the reset action
        account = session.get(Account, account_id)
        if not account:
            return {"ok": False, "error": "Account not found"}
        
        metric = Metric(
            tenant_id=account.tenant_id,
            key="admin.reset_limits",
            value_num=1.0,
            meta_json=json.dumps({
                "account_id": account_id,
                "reset_time": datetime.utcnow().isoformat()
            })
        )
        
        session.add(metric)
        session.commit()
    
    return {"ok": True, "reset_time": datetime.utcnow().isoformat()}


def should_post_to_subreddit(account_id: int, subreddit: str) -> bool:
    """
    Check if an account should be allowed to post to a specific subreddit.
    
    Args:
        account_id: Account ID to check
        subreddit: Subreddit name to check
        
    Returns:
        True if posting is allowed, False otherwise
    """
    # Check general posting limits first
    if not should_act(account_id, "post"):
        return False
    
    # Check subreddit-specific interval (24-48 hours)
    last_post_time = _get_last_subreddit_post_time(account_id, subreddit)
    if last_post_time:
        min_interval_hours = REDDIT_SUBREDDIT_INTERVALS["min_hours"]
        next_allowed = last_post_time + timedelta(hours=min_interval_hours)
        
        if datetime.utcnow() < next_allowed:
            logger.debug(f"Subreddit interval not met for account {account_id}, subreddit r/{subreddit}")
            return False
    
    # Check account-level cooldowns
    if _is_account_in_cooldown(account_id):
        logger.debug(f"Account {account_id} is in cooldown period")
        return False
    
    return True


def cooldown(account_id: int, error_code: str, retry_after: Optional[int] = None) -> None:
    """
    Apply cooldown to an account after rate limit or error.
    
    Args:
        account_id: Account ID to apply cooldown to
        error_code: Type of error (ratelimit, shadowban, captcha)
        retry_after: Optional retry delay in seconds from Reddit
    """
    with Session(engine) as session:
        account = session.get(Account, account_id)
        if not account:
            logger.error(f"Account {account_id} not found for cooldown")
            return
        
        cooldown_end = None
        cooldown_type = error_code
        
        if error_code == "ratelimit":
            # Calculate exponential backoff cooldown
            previous_cooldowns = _count_recent_cooldowns(account_id, "ratelimit", hours=24)
            base_minutes = REDDIT_COOLDOWNS["ratelimit"]["base_minutes"]
            multiplier = REDDIT_COOLDOWNS["ratelimit"]["multiplier"]
            max_minutes = REDDIT_COOLDOWNS["ratelimit"]["max_minutes"]
            
            cooldown_minutes = min(base_minutes * (multiplier ** previous_cooldowns), max_minutes)
            
            if retry_after:
                # Use Reddit's retry_after if provided, but apply minimum
                cooldown_minutes = max(cooldown_minutes, retry_after // 60)
            
            cooldown_end = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
            
        elif error_code == "shadowban":
            cooldown_hours = REDDIT_COOLDOWNS["shadowban"]["cooldown_hours"]
            cooldown_end = datetime.utcnow() + timedelta(hours=cooldown_hours)
            
            # Mark account as shadow suspected
            account.warm_status = "shadowban_suspected"
            session.add(account)
            
        elif error_code == "captcha":
            cooldown_minutes = REDDIT_COOLDOWNS["captcha"]["cooldown_minutes"]
            cooldown_end = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        
        if cooldown_end:
            # Record cooldown in metrics
            metric = Metric(
                tenant_id=account.tenant_id,
                key=f"cooldown.{cooldown_type}",
                value_num=1.0,
                meta_json=json.dumps({
                    "account_id": account_id,
                    "cooldown_type": cooldown_type,
                    "cooldown_end": cooldown_end.isoformat(),
                    "retry_after": retry_after,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            
            session.add(metric)
            session.commit()
            
            logger.warning(f"Applied {cooldown_type} cooldown to account {account_id} until {cooldown_end}")


def get_subreddit_next_window(account_id: int, subreddit: str) -> int:
    """
    Calculate seconds until next allowed post to a specific subreddit.
    
    Args:
        account_id: Account ID
        subreddit: Subreddit name
        
    Returns:
        Seconds until next post is allowed to this subreddit
    """
    # Check general post window first
    general_window = next_window(account_id, "post")
    
    # Check subreddit-specific window
    last_post_time = _get_last_subreddit_post_time(account_id, subreddit)
    if last_post_time:
        min_interval_hours = REDDIT_SUBREDDIT_INTERVALS["min_hours"]
        next_allowed = last_post_time + timedelta(hours=min_interval_hours)
        now = datetime.utcnow()
        
        if next_allowed > now:
            subreddit_window = int((next_allowed - now).total_seconds())
            return max(general_window, subreddit_window)
    
    # Check account cooldowns
    cooldown_window = _get_cooldown_window(account_id)
    
    return max(general_window, cooldown_window)


def record_subreddit_post(account_id: int, subreddit: str, post_id: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """
    Record that an account posted to a specific subreddit.
    
    Args:
        account_id: Account ID
        subreddit: Subreddit name
        post_id: Reddit post ID
        meta: Optional metadata
    """
    # Record general post action
    post_meta = {
        "subreddit": subreddit,
        "post_id": post_id,
        **(meta or {})
    }
    record_action(account_id, "post", post_meta)
    
    # Record subreddit-specific post
    with Session(engine) as session:
        account = session.get(Account, account_id)
        if not account:
            logger.error(f"Account {account_id} not found for recording subreddit post")
            return
        
        metric = Metric(
            tenant_id=account.tenant_id,
            key=f"post.subreddit.{subreddit}",
            value_num=1.0,
            meta_json=json.dumps({
                "account_id": account_id,
                "subreddit": subreddit,
                "post_id": post_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(meta or {})
            })
        )
        
        session.add(metric)
        session.commit()
        
        logger.info(f"Recorded post to r/{subreddit} for account {account_id}: {post_id}")


def _get_last_subreddit_post_time(account_id: int, subreddit: str) -> Optional[datetime]:
    """Get the timestamp of the last post to a specific subreddit."""
    with Session(engine) as session:
        metrics = session.exec(
            select(Metric).where(
                Metric.key == f"post.subreddit.{subreddit}"
            ).order_by(Metric.created_at.desc()).limit(10)
        ).all()
        
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    return metric.created_at
            except json.JSONDecodeError:
                continue
        
        return None


def _is_account_in_cooldown(account_id: int) -> bool:
    """Check if account is currently in any cooldown period."""
    with Session(engine) as session:
        # Check for active cooldowns
        now = datetime.utcnow()
        
        # Look for recent cooldown metrics
        cutoff = now - timedelta(hours=168)  # Check last week
        
        metrics = session.exec(
            select(Metric).where(
                Metric.key.like("cooldown.%"),
                Metric.created_at >= cutoff
            ).order_by(Metric.created_at.desc())
        ).all()
        
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    cooldown_end_str = meta.get("cooldown_end")
                    if cooldown_end_str:
                        cooldown_end = datetime.fromisoformat(cooldown_end_str.replace('Z', '+00:00'))
                        if now < cooldown_end:
                            return True
            except (json.JSONDecodeError, ValueError):
                continue
        
        return False


def _count_recent_cooldowns(account_id: int, cooldown_type: str, hours: int = 24) -> int:
    """Count number of recent cooldowns of a specific type."""
    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = session.exec(
            select(Metric).where(
                Metric.key == f"cooldown.{cooldown_type}",
                Metric.created_at >= cutoff
            )
        ).all()
        
        count = 0
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    count += 1
            except json.JSONDecodeError:
                continue
        
        return count


def _get_cooldown_window(account_id: int) -> int:
    """Get seconds until account cooldown expires."""
    with Session(engine) as session:
        now = datetime.utcnow()
        max_window = 0
        
        # Check for active cooldowns
        cutoff = now - timedelta(hours=168)  # Check last week
        
        metrics = session.exec(
            select(Metric).where(
                Metric.key.like("cooldown.%"),
                Metric.created_at >= cutoff
            ).order_by(Metric.created_at.desc())
        ).all()
        
        for metric in metrics:
            try:
                meta = json.loads(metric.meta_json or "{}")
                if meta.get("account_id") == account_id:
                    cooldown_end_str = meta.get("cooldown_end")
                    if cooldown_end_str:
                        cooldown_end = datetime.fromisoformat(cooldown_end_str.replace('Z', '+00:00'))
                        if now < cooldown_end:
                            window = int((cooldown_end - now).total_seconds())
                            max_window = max(max_window, window)
            except (json.JSONDecodeError, ValueError):
                continue
        
        return max_window