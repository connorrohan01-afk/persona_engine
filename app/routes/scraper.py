"""Scraper endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.security import verify_token
from app.config import settings

router = APIRouter(prefix="/api/v1/scraper", tags=["scraper"])


class ScraperRequest(BaseModel):
    tenant_id: str = settings.tenant_default
    target: str
    subreddit: Optional[str] = None
    limit: int = 10


@router.post("/run")
async def scraper_run(
    request: ScraperRequest,
    dry: Optional[bool] = Query(default=None),
    token: str = Depends(verify_token)
):
    """Run content scraper."""
    is_dry = dry if dry is not None else settings.dry_run_default
    mode = "mock" if is_dry else "live"
    
    mock_items = [
        {
            "title": "Interesting Post About Technology",
            "url": "https://reddit.com/r/technology/comments/abc123",
            "subreddit": "technology",
            "score": 1250
        },
        {
            "title": "Python Development Tips",
            "url": "https://reddit.com/r/python/comments/def456", 
            "subreddit": "python",
            "score": 890
        }
    ]
    
    return {
        "ok": True,
        "mode": mode,
        "items": mock_items[:request.limit]
    }