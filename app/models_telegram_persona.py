"""Telegram Persona SQLModel classes for PersonaEngine."""

import secrets
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class TelegramPersona(SQLModel, table=True):
    """Telegram persona bot linked to a persona in the registry."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    persona_id: str = Field(index=True)  # Reference to persona in registry
    bot_token: str = Field(unique=True)  # Telegram bot token - must be unique
    username: str = Field(unique=True, index=True)  # Telegram bot username - must be unique
    webhook_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))  # Cryptographically secure webhook secret
    linked: bool = Field(default=False)  # Whether linked to persona
    enabled: bool = Field(default=True)  # Whether bot is active
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_telegram_persona_id(self) -> str:
        """Get formatted telegram persona ID."""
        return f"tp_{self.id:03d}" if self.id else "tp_new"
    
    def get_webhook_url(self, base_url: str) -> str:
        """Get webhook URL for this telegram persona."""
        telegram_persona_id = self.get_telegram_persona_id()
        return f"{base_url}/{telegram_persona_id}"