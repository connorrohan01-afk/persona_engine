"""Reddit posting, scraping, and interaction endpoints."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select, desc, asc
from loguru import logger

from app.security import verify_token
from app.db import get_session
from app.models import Account, Session as SessionModel, Post
from app.models_reddit import RedditPost, RedditQueueItem, RedditScrapeJob
from app.providers.reddit import reddit_provider
from app.reddit_utils import (
    validate_subreddit_name, validate_post_title, validate_post_body,
    validate_url, clean_subreddit_name, format_reddit_url
)

router = APIRouter(prefix="/api/v1/reddit", tags=["reddit"])


# Request models
class PostRequest(BaseModel):
    tenant_id: str
    account_id: int
    subreddit: str
    kind: str = Field(..., description="Post type: text, link, image")
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    flair_id: Optional[str] = None
    nsfw: bool = False
    spoiler: bool = False
    schedule: Optional[str] = None  # ISO datetime string
    dry: bool = False


class ScrapeRequest(BaseModel):
    tenant_id: str
    subreddit: str
    sort: str = Field(default="hot", description="Sort method: hot, new, top, rising")
    time_filter: str = Field(default="day", description="Time filter for top posts: hour, day, week, month, year, all")
    limit: int = Field(default=25, ge=1, le=100)
    dry: bool = False


class QueueRequest(BaseModel):
    tenant_id: str
    account_id: int
    subreddit: str
    kind: str
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    flair_id: Optional[str] = None
    nsfw: bool = False
    spoiler: bool = False
    schedule: datetime


@router.post("/post")
async def submit_post(
    request: PostRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Submit a post to Reddit with validation and optional scheduling."""
    try:
        logger.info(f"Reddit post request: {request.kind} to r/{request.subreddit}")
        
        # Validate account exists and belongs to tenant
        account = session.get(Account, request.account_id)
        if not account or account.tenant_id != request.tenant_id:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Check if dry run mode
        is_dry_run = request.dry
        mode = "mock" if is_dry_run else "live"
        
        # Validate subreddit name
        if not validate_subreddit_name(request.subreddit):
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": mode,
                    "error_code": "validation",
                    "message": f"Invalid subreddit name: {request.subreddit}"
                }
            )
        
        # Validate title
        valid_title, title_error = validate_post_title(request.title)
        if not valid_title:
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": mode,
                    "error_code": "validation",
                    "message": f"Invalid title: {title_error}"
                }
            )
        
        # Validate body for text posts
        if request.kind == "text" and request.body:
            valid_body, body_error = validate_post_body(request.body)
            if not valid_body:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "mode": mode,
                        "error_code": "validation",
                        "message": f"Invalid body: {body_error}"
                    }
                )
        
        # Validate URL for link posts
        if request.kind == "link" and request.url:
            valid_url, url_error = validate_url(request.url)
            if not valid_url:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "mode": mode,
                        "error_code": "validation",
                        "message": f"Invalid URL: {url_error}"
                    }
                )
        
        # Check if scheduled for future
        scheduled_time = None
        if request.schedule:
            try:
                scheduled_time = datetime.fromisoformat(request.schedule.replace('Z', '+00:00'))
                if scheduled_time <= datetime.utcnow():
                    scheduled_time = None  # Post immediately if time is in past
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "mode": mode,
                        "error_code": "validation",
                        "message": "Invalid schedule format, expected ISO datetime"
                    }
                )
        
        if scheduled_time:
            # Queue for later posting
            queue_item = RedditQueueItem(
                tenant_id=request.tenant_id,
                account_id=request.account_id,
                subreddit=clean_subreddit_name(request.subreddit),
                kind=request.kind,
                title=request.title,
                body=request.body,
                url=request.url,
                image_url=request.image_url,
                flair_id=request.flair_id,
                nsfw=request.nsfw,
                spoiler=request.spoiler,
                schedule=scheduled_time,
                status="queued"
            )
            
            session.add(queue_item)
            session.commit()
            
            return {
                "ok": True,
                "mode": mode,
                "status": "queued",
                "queue_id": queue_item.id,
                "scheduled_for": scheduled_time.isoformat(),
                "subreddit": clean_subreddit_name(request.subreddit)
            }
        
        else:
            # Post immediately
            try:
                # Use mock provider if dry run is requested
                from app.providers.reddit import MockRedditProvider
                provider = MockRedditProvider() if is_dry_run else reddit_provider
                
                result = await provider.submit_post(
                    subreddit=clean_subreddit_name(request.subreddit),
                    kind=request.kind,
                    title=request.title,
                    body=request.body,
                    url=request.url,
                    nsfw=request.nsfw,
                    spoiler=request.spoiler,
                    flair_id=request.flair_id
                )
                
                # Store post record
                reddit_post = RedditPost(
                    tenant_id=request.tenant_id,
                    account_id=request.account_id,
                    subreddit=clean_subreddit_name(request.subreddit),
                    kind=request.kind,
                    title=request.title,
                    body=request.body,
                    url=request.url,
                    image_url=request.image_url,
                    reddit_id=result.get("id"),
                    reddit_fullname=result.get("fullname"),
                    permalink=result.get("permalink"),
                    nsfw=request.nsfw,
                    spoiler=request.spoiler,
                    flair_id=request.flair_id,
                    status="posted",
                    submitted_at=datetime.utcnow()
                )
                
                session.add(reddit_post)
                session.commit()
                
                return {
                    "ok": True,
                    "mode": mode,
                    "status": "posted",
                    "post_id": reddit_post.id,
                    "reddit_id": result.get("id"),
                    "permalink": result.get("permalink"),
                    "url": result.get("url"),
                    "subreddit": clean_subreddit_name(request.subreddit)
                }
                
            except Exception as e:
                logger.error(f"Reddit post submission failed: {e}")
                
                # Store failed post record
                reddit_post = RedditPost(
                    tenant_id=request.tenant_id,
                    account_id=request.account_id,
                    subreddit=clean_subreddit_name(request.subreddit),
                    kind=request.kind,
                    title=request.title,
                    body=request.body,
                    url=request.url,
                    image_url=request.image_url,
                    nsfw=request.nsfw,
                    spoiler=request.spoiler,
                    flair_id=request.flair_id,
                    status="failed",
                    error_message=str(e)
                )
                
                session.add(reddit_post)
                session.commit()
                
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "mode": mode,
                        "error_code": "reddit_error",
                        "message": str(e)
                    }
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reddit post endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "mode": "unknown",
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.post("/scrape")
async def scrape_subreddit(
    request: ScrapeRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Scrape posts from a subreddit."""
    try:
        logger.info(f"Reddit scrape request: r/{request.subreddit} {request.sort}")
        
        # Check if dry run mode
        is_dry_run = request.dry
        mode = "mock" if is_dry_run else "live"
        
        # Validate subreddit name
        if not validate_subreddit_name(request.subreddit):
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": mode,
                    "error_code": "validation",
                    "message": f"Invalid subreddit name: {request.subreddit}"
                }
            )
        
        # Create scrape job record
        scrape_job = RedditScrapeJob(
            tenant_id=request.tenant_id,
            subreddit=clean_subreddit_name(request.subreddit),
            sort=request.sort,
            time_filter=request.time_filter,
            limit=request.limit,
            status="processing",
            started_at=datetime.utcnow()
        )
        
        session.add(scrape_job)
        session.commit()
        
        try:
            # Use mock provider if dry run is requested
            from app.providers.reddit import MockRedditProvider
            provider = MockRedditProvider() if is_dry_run else reddit_provider
            
            # Scrape posts
            posts = await provider.get_posts(
                subreddit=clean_subreddit_name(request.subreddit),
                sort=request.sort,
                limit=request.limit,
                time_filter=request.time_filter
            )
            
            # Update job with results
            scrape_job.status = "completed"
            scrape_job.items_found = len(posts)
            scrape_job.items_stored = len(posts)
            scrape_job.result_json = json.dumps(posts)
            scrape_job.completed_at = datetime.utcnow()
            
            session.add(scrape_job)
            session.commit()
            
            return {
                "ok": True,
                "mode": mode,
                "job_id": scrape_job.id,
                "status": "completed",
                "items_found": len(posts),
                "subreddit": clean_subreddit_name(request.subreddit),
                "posts": posts
            }
            
        except Exception as e:
            logger.error(f"Reddit scrape failed: {e}")
            
            # Update job with error
            scrape_job.status = "failed"
            scrape_job.error_message = str(e)
            scrape_job.completed_at = datetime.utcnow()
            
            session.add(scrape_job)
            session.commit()
            
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": mode,
                    "error_code": "reddit_error",
                    "message": str(e)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reddit scrape endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "mode": "unknown",
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.post("/queue")
async def queue_post(
    request: QueueRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Queue a post for future submission."""
    try:
        logger.info(f"Reddit queue request: {request.kind} to r/{request.subreddit}")
        
        # Validate account exists and belongs to tenant
        account = session.get(Account, request.account_id)
        if not account or account.tenant_id != request.tenant_id:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Validate subreddit name
        if not validate_subreddit_name(request.subreddit):
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": "live",
                    "error_code": "validation",
                    "message": f"Invalid subreddit name: {request.subreddit}"
                }
            )
        
        # Validate title
        valid_title, title_error = validate_post_title(request.title)
        if not valid_title:
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": "live",
                    "error_code": "validation",
                    "message": f"Invalid title: {title_error}"
                }
            )
        
        # Create queue item
        queue_item = RedditQueueItem(
            tenant_id=request.tenant_id,
            account_id=request.account_id,
            subreddit=clean_subreddit_name(request.subreddit),
            kind=request.kind,
            title=request.title,
            body=request.body,
            url=request.url,
            image_url=request.image_url,
            flair_id=request.flair_id,
            nsfw=request.nsfw,
            spoiler=request.spoiler,
            schedule=request.schedule,
            status="queued"
        )
        
        session.add(queue_item)
        session.commit()
        
        return {
            "ok": True,
            "mode": "live",
            "status": "queued",
            "queue_id": queue_item.id,
            "scheduled_for": request.schedule.isoformat(),
            "subreddit": clean_subreddit_name(request.subreddit)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reddit queue endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "mode": "unknown",
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.get("/posts/{tenant_id}")
async def get_posts(
    tenant_id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    subreddit: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None)
):
    """Get Reddit posts for a tenant."""
    try:
        query = select(RedditPost).where(RedditPost.tenant_id == tenant_id)
        
        if subreddit:
            query = query.where(RedditPost.subreddit == clean_subreddit_name(subreddit))
        
        if status:
            query = query.where(RedditPost.status == status)
        
        query = query.order_by(desc(RedditPost.created_at)).offset(offset).limit(limit)
        
        posts = session.exec(query).all()
        
        return {
            "ok": True,
            "mode": "live",
            "posts": [
                {
                    "id": post.id,
                    "subreddit": post.subreddit,
                    "kind": post.kind,
                    "title": post.title,
                    "body": post.body,
                    "url": post.url,
                    "reddit_id": post.reddit_id,
                    "permalink": post.permalink,
                    "status": post.status,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "submitted_at": post.submitted_at.isoformat() if post.submitted_at else None,
                    "created_at": post.created_at.isoformat()
                }
                for post in posts
            ],
            "total": len(posts),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Get posts endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "mode": "unknown",
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.get("/queue/{tenant_id}")
async def get_queue(
    tenant_id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None)
):
    """Get queued Reddit posts for a tenant."""
    try:
        query = select(RedditQueueItem).where(RedditQueueItem.tenant_id == tenant_id)
        
        if status:
            query = query.where(RedditQueueItem.status == status)
        
        query = query.order_by(asc(RedditQueueItem.schedule)).offset(offset).limit(limit)
        
        queue_items = session.exec(query).all()
        
        return {
            "ok": True,
            "mode": "live",
            "queue_items": [
                {
                    "id": item.id,
                    "subreddit": item.subreddit,
                    "kind": item.kind,
                    "title": item.title,
                    "body": item.body,
                    "url": item.url,
                    "schedule": item.schedule.isoformat(),
                    "status": item.status,
                    "attempts": item.attempts,
                    "post_id": item.post_id,
                    "created_at": item.created_at.isoformat()
                }
                for item in queue_items
            ],
            "total": len(queue_items),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Get queue endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "mode": "unknown",
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.delete("/queue/{queue_id}")
async def cancel_queue_item(
    queue_id: int,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Cancel a queued Reddit post."""
    try:
        queue_item = session.get(RedditQueueItem, queue_id)
        
        if not queue_item:
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        if queue_item.status in ["posted", "failed"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "mode": "live",
                    "error_code": "invalid_status",
                    "message": f"Cannot cancel item with status: {queue_item.status}"
                }
            )
        
        queue_item.status = "cancelled"
        queue_item.updated_at = datetime.utcnow()
        
        session.add(queue_item)
        session.commit()
        
        return {
            "ok": True,
            "mode": "live",
            "status": "cancelled",
            "queue_id": queue_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel queue endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "mode": "unknown",
                "error_code": "internal",
                "message": "Internal server error"
            }
        )