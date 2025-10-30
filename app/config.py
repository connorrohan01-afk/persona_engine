"""Configuration management using Pydantic BaseSettings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Required
    auth_bearer_token: str = ""
    
    # Database
    database_url: str = "sqlite:///./data.db"
    
    # Proxy provider
    proxy_pool_url: Optional[str] = None
    proxy_pool_file: str = "./proxies.txt"  # Line per proxy: host:port:user:pass
    
    # SMS providers  
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    fivesim_api_key: Optional[str] = None
    sms_activate_api_key: Optional[str] = None
    
    # Email providers
    gmail_credentials: Optional[str] = None
    mailtm_api_key: Optional[str] = None
    email_forwarder_url: Optional[str] = None
    
    # Captcha providers
    captcha_provider: str = "mock"  # 2captcha, capmonster, anticaptcha, mock
    captcha_key: Optional[str] = None  # Generic captcha API key
    anticaptcha_api_key: Optional[str] = None
    capsolver_api_key: Optional[str] = None
    twocaptcha_api_key: Optional[str] = None
    
    # Reddit API
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None  # Renamed from reddit_secret for clarity
    reddit_redirect_uri: Optional[str] = None
    reddit_username: Optional[str] = None
    reddit_password: Optional[str] = None
    reddit_user_agent: str = "PersonaEngine/1.0 by"
    reddit_timeout_s: int = 30
    reddit_max_retries: int = 3
    reddit_rate_burst: int = 30
    reddit_rate_window_s: int = 60
    
    # Image generation providers
    img_provider: str = "mock"  # openai, replicate, stability, mock
    openai_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    stability_api_key: Optional[str] = None
    
    # Storage backend
    storage_backend: str = "local"  # s3, local
    public_base_url: str = "http://localhost:8000"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    
    # Asset management
    asset_signing_secret: Optional[str] = None  # 32 chars, fallback to app secret
    max_image_mb: int = 8
    allow_nsfw: bool = False
    
    # Account sessions
    session_dir: str = "./_sessions"  # Directory to store session files
    
    # Warming system
    warm_default_window: str = "08:00-22:00"  # Local TZ or UTC if not set
    warm_jitter_seconds_min: int = 15
    warm_jitter_seconds_max: int = 120
    warm_max_concurrency: int = 4
    warm_max_actions_per_run: int = 20
    warm_minutes_between_same_account: int = 30
    dry_default: int = 1  # If set, engine runs in dry unless request overrides
    
    # Telegram persona deployer system
    telegram_default_upsell: str = "Check out my vault 🔗"
    telegram_webhook_base: str = "https://YOUR_APP/api/v1/telegram/persona/webhook"
    
    # Vault storage system
    storage_driver: str = "local"  # r2, s3, local
    storage_bucket: str = "persona-vault"
    storage_public_base: str = "https://YOUR_APP/cdn"
    storage_signing_ttl_s: int = 3600
    storage_max_mb: int = 25
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    default_tenant: str = "owner"
    
    # Legacy services (keeping for backward compatibility)
    image_api_key: Optional[str] = None
    storage_s3_endpoint: Optional[str] = None
    storage_s3_bucket: Optional[str] = None
    storage_s3_key: Optional[str] = None
    storage_s3_secret: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    
    # Defaults
    dry_run_default: bool = True
    tenant_default: str = "owner"
    
    class Config:
        env_file = ".env"


settings = Settings()