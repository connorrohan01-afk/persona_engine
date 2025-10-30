"""SQLModel database models for Reddit functionality."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


# RedditAccount model removed - using existing Account model from app.models instead


class RedditPost(SQLModel, table=True):
    """Reddit post model for tracking submitted posts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    account_id: int  # Foreign key to AccountSession or RedditAccount
    subreddit: str
    kind: str  # text, link, image, video
    title: str
    body: Optional[str] = None  # For text posts
    url: Optional[str] = None  # For link posts
    image_url: Optional[str] = None  # For image posts
    reddit_id: Optional[str] = None  # Reddit post ID (e.g., "abc123")
    reddit_fullname: Optional[str] = None  # Reddit fullname (e.g., "t3_abc123")
    permalink: Optional[str] = None  # Reddit permalink URL
    nsfw: bool = False
    spoiler: bool = False
    flair_id: Optional[str] = None
    flair_text: Optional[str] = None
    status: str = "pending"  # pending, posted, failed, removed, deleted
    score: int = 0  # Upvotes - downvotes
    upvote_ratio: Optional[float] = None
    num_comments: int = 0
    post_hint: Optional[str] = None  # image, link, video, etc.
    error_message: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RedditQueueItem(SQLModel, table=True):
    """Reddit queue item model for scheduled posts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    account_id: int  # Foreign key to AccountSession or RedditAccount
    subreddit: str
    kind: str  # text, link, image, video
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    nsfw: bool = False
    spoiler: bool = False
    flair_id: Optional[str] = None
    schedule: datetime  # When to post
    status: str = "queued"  # queued, processing, posted, failed, cancelled
    attempts: int = 0
    max_attempts: int = 3
    post_id: Optional[int] = None  # Foreign key to RedditPost when posted
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RedditScrapeJob(SQLModel, table=True):
    """Reddit scrape job model for tracking scraping operations."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    subreddit: str
    sort: str = "hot"  # hot, new, top, rising
    time_filter: str = "day"  # hour, day, week, month, year, all
    limit: int = 25
    after: Optional[str] = None  # Reddit pagination token
    before: Optional[str] = None  # Reddit pagination token
    status: str = "pending"  # pending, processing, completed, failed
    items_found: int = 0
    items_stored: int = 0
    result_json: Optional[str] = None  # Scraped data as JSON
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RedditRateWindow(SQLModel, table=True):
    """Reddit rate limiting window for tracking API usage."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    account_id: Optional[int] = None  # Specific account or global
    endpoint: str  # submit, comment, message, etc.
    window_start: datetime
    window_end: datetime
    requests_made: int = 0
    requests_limit: int = 30  # Default burst limit
    reset_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)