"""Production-ready job queue system with priorities, retries, backoff, and idempotency."""

import json
import random
import sqlalchemy
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlmodel import Session, select
from app.db import engine
from app.models import Job, Account, WarmPlan, Metric
from app.config import settings
from loguru import logger


def enqueue(
    job_type: str,
    args: Dict[str, Any],
    *,
    idempotency_key: Optional[str] = None,
    priority: int = 5,
    run_after: Optional[datetime] = None
) -> str:
    """
    Enqueue a new job with priority and idempotency support.
    
    Args:
        job_type: Type of job to enqueue
        args: Job arguments
        idempotency_key: Optional key to prevent duplicate jobs
        priority: Job priority (1=highest, 10=lowest)
        run_after: Optional earliest run time
    
    Returns:
        Job ID as string
    """
    with Session(engine) as session:
        # Get tenant_id for scoped operations
        tenant_id = args.get("tenant_id", settings.tenant_default)
        
        # Check for existing job with tenant-scoped idempotency key
        if idempotency_key:
            existing = session.exec(
                select(Job).where(
                    Job.tenant_id == tenant_id,  # CRITICAL: Tenant-scoped idempotency
                    Job.idempotency_key == idempotency_key,
                    Job.status.in_(["pending", "running", "completed"])
                )
            ).first()
            if existing:
                logger.info(f"Job with idempotency key {idempotency_key} already exists for tenant {tenant_id}: {existing.id}")
                return str(existing.id or 0)
        
        # Create new job
        job = Job(
            tenant_id=tenant_id,
            type=job_type,
            args_json=json.dumps(args),
            priority=max(1, min(10, priority)),  # Clamp between 1-10
            idempotency_key=idempotency_key,
            run_after=run_after,
            status="pending",
            next_run_at=run_after or datetime.utcnow()
        )
        
        session.add(job)
        session.commit()
        session.refresh(job)
        
        logger.info(f"Enqueued job {job.id} of type {job_type} with priority {priority}")
        return str(job.id or 0)


def reserve(n: int = 10) -> List[Job]:
    """
    Reserve up to n due jobs for processing with atomic locking.
    Uses PostgreSQL SKIP LOCKED when available, falls back to safer SQLite method.
    
    Args:
        n: Maximum number of jobs to reserve
        
    Returns:
        List of reserved jobs
    """
    with Session(engine) as session:
        # Check database dialect for locking strategy
        dialect_name = engine.dialect.name.lower()
        
        if dialect_name == "postgresql":
            # Use FOR UPDATE SKIP LOCKED for atomic job reservation
            # This prevents multiple workers from claiming the same job
            due_jobs = session.exec(
                select(Job).where(
                    Job.status == "pending",
                    Job.next_run_at <= datetime.utcnow()
                ).order_by(
                    Job.priority.asc(),  # Lower number = higher priority
                    Job.created_at.asc()  # FIFO within priority
                ).limit(n).with_for_update(skip_locked=True)
            ).all()
            
            # Mark jobs as running atomically - they're already locked
            reserved = []
            for job in due_jobs:
                job.status = "running"
                job.started_at = datetime.utcnow()
                reserved.append(job)
        else:
            # SQLite fallback: atomic job claiming with conditional updates
            # Find candidate jobs first
            candidate_jobs = session.exec(
                select(Job).where(
                    Job.status == "pending",
                    Job.next_run_at <= datetime.utcnow()
                ).order_by(
                    Job.priority.asc(),  # Lower number = higher priority
                    Job.created_at.asc()  # FIFO within priority
                ).limit(n * 2)  # Get more candidates to handle concurrent claims
            ).all()
            
            # Atomically claim jobs one by one using SQLAlchemy Core UPDATE
            reserved = []
            current_time = datetime.utcnow()
            
            for job in candidate_jobs:
                # Execute atomic conditional UPDATE to claim the job using SQLAlchemy Core
                # This ensures only one worker can claim each job and avoids table name coupling
                from sqlalchemy import update
                
                update_stmt = update(Job.__table__).where(
                    (Job.id == job.id) & 
                    (Job.status == "pending") &
                    (Job.next_run_at <= current_time)  # Guard against TOCTOU
                ).values(
                    status="running",
                    started_at=current_time
                )
                
                result = session.exec(update_stmt)
                
                # Check if we successfully claimed this job (affected 1 row)
                if result.rowcount == 1:
                    # Refresh the job object to get updated state
                    session.refresh(job)
                    reserved.append(job)
                    
                    # Stop if we have enough jobs
                    if len(reserved) >= n:
                        break
                else:
                    # Job was already claimed by another worker or became overdue
                    logger.debug(f"Job {job.id} already claimed or became overdue")
            
            # Commit all SQLite claims at once for better performance
            if reserved:
                session.commit()
        
        if reserved:
            logger.info(f"Reserved {len(reserved)} jobs for processing (dialect: {dialect_name})")
        
        return reserved


def mark_done(
    job_id: int,
    ok: bool,
    error: Optional[str] = None,
    retry_in_seconds: Optional[int] = None
) -> None:
    """
    Mark a job as completed or failed with retry logic.
    
    Args:
        job_id: Job ID to mark
        ok: Whether job completed successfully
        error: Error message if failed
        retry_in_seconds: Override retry delay (optional)
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found for marking done")
            return
        
        if ok:
            job.status = "completed"
            job.last_error = None
            logger.info(f"Job {job_id} ({job.type}) completed successfully")
        else:
            job.attempts += 1
            job.last_error = error
            
            # Calculate retry delay with exponential backoff + jitter
            max_attempts = 5
            if job.attempts >= max_attempts:
                job.status = "failed"
                logger.error(f"Job {job_id} ({job.type}) failed permanently after {job.attempts} attempts: {error}")
            else:
                job.status = "pending"
                
                # Exponential backoff: 2^attempts * 30 seconds + jitter, capped at 6 hours
                if retry_in_seconds is not None:
                    retry_delay = retry_in_seconds
                else:
                    base_delay = min(30 * (2 ** job.attempts), 6 * 3600)  # Cap at 6 hours
                    jitter = random.uniform(0.8, 1.2)  # ±20% jitter
                    retry_delay = int(base_delay * jitter)
                
                job.next_run_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                logger.warning(f"Job {job_id} ({job.type}) will retry in {retry_delay}s (attempt {job.attempts}/{max_attempts}): {error}")
        
        session.commit()


def worker_tick(max_jobs: int = 10) -> Dict[str, int]:
    """
    Process due jobs from the queue.
    
    Args:
        max_jobs: Maximum number of jobs to process
        
    Returns:
        Dictionary with processing stats
    """
    reserved_jobs = reserve(max_jobs)
    processed = 0
    
    for job in reserved_jobs:
        try:
            logger.info(f"Processing job {job.id} of type {job.type}")
            
            # Dispatch to job handlers
            success, error = _dispatch_job(job)
            
            # Mark job as done
            mark_done(job.id or 0, success, error)
            processed += 1
            
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {str(e)}")
            mark_done(job.id or 0, False, str(e))
            processed += 1
    
    # Get remaining job counts
    with Session(engine) as session:
        remaining = session.exec(
            select(Job).where(
                Job.status == "pending",
                Job.next_run_at <= datetime.utcnow()
            )
        ).all()
        
    return {
        "processed": processed,
        "remaining": len(remaining)
    }


def get_queue_stats() -> Dict[str, int]:
    """Get queue statistics."""
    with Session(engine) as session:
        stats = {}
        
        # Count jobs by status
        for status in ["pending", "running", "completed", "failed"]:
            count = len(session.exec(select(Job).where(Job.status == status)).all())
            stats[status] = count
        
        # Count due jobs
        due_count = len(session.exec(
            select(Job).where(
                Job.status == "pending",
                Job.next_run_at <= datetime.utcnow()
            )
        ).all())
        stats["due"] = due_count
        
        # Count scheduled jobs (not yet due)
        scheduled_count = len(session.exec(
            select(Job).where(
                Job.status == "pending",
                Job.next_run_at > datetime.utcnow()
            )
        ).all())
        stats["scheduled"] = scheduled_count
        
        # Count stuck jobs (running too long)
        stuck_cutoff = datetime.utcnow() - timedelta(hours=1)
        stuck_count = len(session.exec(
            select(Job).where(
                Job.status == "running",
                Job.started_at.isnot(None),  # Only jobs that have actually started
                Job.started_at < stuck_cutoff
            )
        ).all())
        stats["stuck"] = stuck_count
        
    return stats


def _dispatch_job(job: Job) -> tuple[bool, Optional[str]]:
    """
    Dispatch job to appropriate handler.
    
    Args:
        job: Job to process
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        args = json.loads(job.args_json or "{}")
        
        if job.type == "warm_step":
            return _handle_warm_step(job, args)
        elif job.type == "warm_account":
            return _handle_warm_account(job, args)
        elif job.type == "post_job":
            return _handle_post_job(job, args)
        else:
            logger.warning(f"Unknown job type: {job.type}")
            return True, None  # Unknown jobs are marked as completed
            
    except json.JSONDecodeError as e:
        return False, f"Invalid job args JSON: {str(e)}"
    except Exception as e:
        return False, f"Job dispatch error: {str(e)}"


def _handle_warm_step(job: Job, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Handle warm_step job."""
    # Import here to avoid circular imports
    from app.routes.warm import handle_warm_step
    
    try:
        result = handle_warm_step(args)
        return result.get("ok", False), result.get("error")
    except Exception as e:
        return False, str(e)


def _handle_warm_account(job: Job, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Handle warm_account job (legacy compatibility)."""
    # Convert to warm_step format
    return _handle_warm_step(job, args)


def _handle_post_job(job: Job, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Handle Reddit post job with comprehensive validation, rate limiting, and error handling.
    
    Expected args:
        account_id: int
        subreddit: str
        kind: str (link, self, image)
        title: str
        body: Optional[str]
        url: Optional[str]
        image_url: Optional[str]
        flair_id: Optional[str]
        nsfw: bool
        spoiler: bool
        dry_run: bool
    """
    # Import here to avoid circular imports
    from app.rate import should_post_to_subreddit, cooldown, record_subreddit_post, next_window
    from app.utils.validate import validate_title, validate_kind, validate_url, validate_comment_text, filter_banned, choose_flair
    from providers.reddit import reddit_provider
    
    try:
        # Extract args
        account_id = args.get("account_id")
        subreddit = args.get("subreddit")
        kind = args.get("kind", "self")
        title = args.get("title", "")
        body = args.get("body")
        url = args.get("url")
        image_url = args.get("image_url")
        flair_id = args.get("flair_id")
        nsfw = args.get("nsfw", False)
        spoiler = args.get("spoiler", False)
        dry_run = args.get("dry_run", False)
        
        # Validate required arguments
        if not account_id or not subreddit or not title:
            return False, "Missing required arguments: account_id, subreddit, title"
        
        logger.info(f"Processing post job for account {account_id} to r/{subreddit}: {title[:50]}...")
        
        # Step 1: Check rate limits
        if not should_post_to_subreddit(account_id, subreddit):
            # Calculate when we can try again
            next_attempt = next_window(account_id, "post")
            if next_attempt > 0:
                # Reschedule the job for later
                from app.rate import get_subreddit_next_window
                delay_seconds = get_subreddit_next_window(account_id, subreddit)
                next_run_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
                
                # Update job to retry later
                with Session(engine) as session:
                    current_job = session.get(Job, job.id)
                    if current_job:
                        current_job.status = "pending"
                        current_job.next_run_at = next_run_at
                        current_job.attempts += 1
                        session.commit()
                        
                        logger.info(f"Rate limit hit for account {account_id}, rescheduled post job for {next_run_at}")
                        return True, None  # Successfully rescheduled
            
            return False, f"Rate limit exceeded for account {account_id}, subreddit r/{subreddit}"
        
        # Step 2: Get account and session data
        with Session(engine) as session:
            account = session.get(Account, account_id)
            if not account:
                return False, f"Account {account_id} not found"
            
            # Get session data for cookies/proxy
            from app.models import Session as SessionModel
            account_session = session.exec(
                select(SessionModel).where(SessionModel.account_id == account_id)
            ).first()
            
            session_data = {
                "cookies_json": account_session.cookies_json if account_session else None,
                "proxy": account_session.proxy if account_session else None
            }
        
        # Step 3: Pre-flight rules validation
        try:
            rules = reddit_provider.get_sub_rules(subreddit)
        except Exception as e:
            logger.error(f"Failed to fetch rules for r/{subreddit}: {e}")
            # Use safe defaults
            rules = {
                "title_max": 300,
                "allow_links": True,
                "allow_images": True,
                "banned_words": [],
                "flairs": [],
                "nsfw_ok": True
            }
        
        # Validate title
        is_valid, error_reason = validate_title(title, rules.get("title_max", 300))
        if not is_valid:
            return False, f"Title validation failed: {error_reason}"
        
        # Validate kind
        is_valid, error_reason = validate_kind(kind, rules)
        if not is_valid:
            return False, f"Post kind validation failed: {error_reason}"
        
        # Validate banned words
        text_to_check = title + " " + (body or "")
        is_clean, offending_word = filter_banned(text_to_check, rules.get("banned_words", []))
        if not is_clean:
            return False, f"Content contains banned word: {offending_word}"
        
        # Validate URL if needed
        if kind == "link" and url:
            is_valid, error_reason = validate_url(url)
            if not is_valid:
                return False, f"URL validation failed: {error_reason}"
        
        # Step 4: Attempt to post via Reddit provider
        try:
            result = reddit_provider.submit_post(
                session_data=session_data,
                subreddit=subreddit,
                kind=kind,
                title=title,
                body=body,
                url=url,
                image_url=image_url,
                flair_id=flair_id,
                nsfw=nsfw,
                spoiler=spoiler,
                dry_run=dry_run
            )
            
            if result.get("ok"):
                # Success! Record the post
                post_id = result.get("post_id", f"t3_unknown_{job.id}")
                mode = result.get("mode", "unknown")
                
                # Store Post record
                with Session(engine) as session:
                    from app.models import Post
                    post = Post(
                        account_id=account_id,
                        subreddit=subreddit,
                        kind=kind,
                        title=title,
                        body=body,
                        url=url,
                        image_url=image_url,
                        post_id_ext=post_id,
                        status="posted" if mode == "live" else "mock"
                    )
                    session.add(post)
                    session.commit()
                
                # Record metrics and rate limiting
                record_subreddit_post(account_id, subreddit, post_id, {
                    "kind": kind,
                    "title": title,
                    "mode": mode,
                    "job_id": job.id
                })
                
                # Success metric
                with Session(engine) as session:
                    metric = Metric(
                        tenant_id=job.tenant_id,
                        key="reddit.post",
                        value_num=1.0,
                        meta_json=json.dumps({
                            "account_id": account_id,
                            "subreddit": subreddit,
                            "post_id": post_id,
                            "kind": kind,
                            "mode": mode,
                            "job_id": job.id
                        })
                    )
                    session.add(metric)
                    session.commit()
                
                logger.info(f"Successfully posted to r/{subreddit} for account {account_id}: {post_id} ({mode})")
                return True, None
            
            else:
                # Handle specific error types from Reddit
                error_code = result.get("error_code", "unknown")
                error_message = result.get("message", "Unknown error")
                
                # Apply appropriate cooldowns and decide on retry strategy
                if error_code == "ratelimit":
                    retry_after = result.get("details", {}).get("retry_after", 60)
                    cooldown(account_id, "ratelimit", retry_after)
                    
                    # For rate limits, reschedule with exponential backoff
                    backoff_minutes = min(10 * (2 ** job.attempts), 360)  # Cap at 6 hours
                    next_run_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
                    
                    with Session(engine) as session:
                        current_job = session.get(Job, job.id)
                        if current_job and current_job.attempts < 5:  # Max 5 retries
                            current_job.status = "pending"
                            current_job.next_run_at = next_run_at
                            current_job.attempts += 1
                            session.commit()
                            
                            logger.warning(f"Reddit rate limit for account {account_id}, rescheduled for {next_run_at}")
                            return True, None  # Successfully rescheduled
                    
                elif error_code == "shadowban":
                    cooldown(account_id, "shadowban")
                    return False, f"Account {account_id} may be shadowbanned: {error_message}"
                
                elif error_code == "captcha":
                    cooldown(account_id, "captcha")
                    return False, f"Captcha required for account {account_id}: {error_message}"
                
                elif error_code == "rules":
                    # Rules violations are not retried
                    return False, f"Post violates subreddit rules: {error_message}"
                
                else:
                    # Unknown errors get limited retries with backoff
                    if job.attempts < 3:
                        backoff_minutes = min(2 * (2 ** job.attempts), 30)  # Cap at 30 minutes
                        next_run_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
                        
                        with Session(engine) as session:
                            current_job = session.get(Job, job.id)
                            if current_job:
                                current_job.status = "pending"
                                current_job.next_run_at = next_run_at
                                current_job.attempts += 1
                                session.commit()
                                
                                logger.warning(f"Unknown error for account {account_id}, rescheduled for {next_run_at}: {error_message}")
                                return True, None  # Successfully rescheduled
                    
                    return False, f"Reddit posting failed: {error_message}"
                
        except Exception as e:
            logger.error(f"Exception during Reddit post for account {account_id}: {e}")
            
            # For network/timeout errors, retry with backoff
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                if job.attempts < 3:
                    backoff_minutes = min(5 * (2 ** job.attempts), 30)
                    next_run_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
                    
                    with Session(engine) as session:
                        current_job = session.get(Job, job.id)
                        if current_job:
                            current_job.status = "pending"
                            current_job.next_run_at = next_run_at
                            current_job.attempts += 1
                            session.commit()
                            
                            logger.warning(f"Network error for account {account_id}, rescheduled for {next_run_at}")
                            return True, None  # Successfully rescheduled
            
            return False, f"Failed to post to Reddit: {str(e)}"
    
    except Exception as e:
        logger.error(f"Post job handler error: {e}")
        return False, f"Post job handler error: {str(e)}"