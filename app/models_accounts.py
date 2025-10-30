"""SQLModel database models for account sessions, proxies, and captcha functionality."""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AccountSession(SQLModel, table=True):
    """Account model for user accounts with session management."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    platform: str  # reddit, twitter, instagram, etc.
    username: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionRecord(SQLModel, table=True):
    """Session model for account session lifecycle management."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int  # Foreign key to AccountSession.id
    tenant_id: str
    status: str = "active"  # active, inactive, expired, warm
    cookies_path: Optional[str] = None  # Path to cookies.json file
    proxy_id: Optional[int] = None  # Foreign key to Proxy.id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Proxy(SQLModel, table=True):
    """Proxy model for proxy pool management."""
    id: Optional[int] = Field(default=None, primary_key=True)
    host: str
    port: int
    user: Optional[str] = None
    password: Optional[str] = None  # Using 'password' instead of 'pass' (reserved keyword)
    last_used_at: Optional[datetime] = None
    healthy: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CaptchaJob(SQLModel, table=True):
    """Captcha job model for captcha solving tasks."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str
    provider: str  # 2captcha, capmonster, anticaptcha, mock
    site_key: str
    url: str
    status: str = "pending"  # pending, processing, solved, failed
    solution: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)