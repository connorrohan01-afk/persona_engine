"""SQLModel database models."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Account(SQLModel, table=True):
    """Account model for user accounts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    username: str
    status: str = "pending"  # pending, created, needs_verification, verified, failed
    provider_notes: Optional[str] = None  # JSON with provider reference IDs
    warm_status: str = "pending"  # pending, queued, running, waiting, complete, failed
    last_warm_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Persona(SQLModel, table=True):
    """Persona model for user personas."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    name: str
    reddit_account_id: Optional[int] = None
    telegram_bot_token: Optional[str] = None
    config_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Session(SQLModel, table=True):
    """Session model for account sessions."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int
    proxy: Optional[str] = None
    fingerprint_json: Optional[str] = None
    cookies_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Post(SQLModel, table=True):
    """Post model for social media posts."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int
    subreddit: Optional[str] = None
    kind: str  # post, comment, etc.
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    post_id_ext: Optional[str] = None  # External platform post ID
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VaultItem(SQLModel, table=True):
    """Vault item model for file storage."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    kind: str  # image, document, etc.
    url: str
    meta_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Job(SQLModel, table=True):
    """Job model for background tasks."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    type: str
    args_json: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    priority: int = 5  # 1=highest, 10=lowest
    idempotency_key: Optional[str] = None
    run_after: Optional[datetime] = None
    attempts: int = 0
    last_error: Optional[str] = None
    next_run_at: Optional[datetime] = None
    started_at: Optional[datetime] = None  # When job processing began
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Metric(SQLModel, table=True):
    """Metric model for analytics."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    persona_id: Optional[int] = None
    key: str
    value_num: Optional[float] = None
    meta_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WarmPlan(SQLModel, table=True):
    """Warm plan model for account warming stages."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int
    persona_id: Optional[int] = None
    stage: str = "seed_profile"  # seed_profile, browse, join, comment, post_light
    next_run_at: Optional[datetime] = None
    progress_json: Optional[str] = None  # JSON with stage progress data
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LinkClick(SQLModel, table=True):
    """Link click tracking model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    link_id: str
    persona_id: Optional[int] = None
    account_id: Optional[int] = None
    ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Asset(SQLModel, table=True):
    """Asset model for file storage (images, documents, etc)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    kind: str  # image, document, etc.
    sha256: str
    mime: str
    bytes: int
    ext: str
    path: str  # Storage path
    public_url: str
    signed_until: Optional[datetime] = None
    meta_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Secret(SQLModel, table=True):
    """Secret model for encrypted key-value storage."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    key: str
    value_enc: str  # Encrypted value using Fernet
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ImageJob(SQLModel, table=True):
    """Image generation job model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    persona_id: Optional[int] = None
    prompt: str
    style: Optional[str] = None
    width: int = 512
    height: int = 512
    provider: str  # openai, replicate, stability, mock
    status: str = "pending"  # pending, processing, completed, failed
    result_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)