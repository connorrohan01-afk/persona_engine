"""Vault Storage SQLModel classes for PersonaEngine."""

import secrets
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
from enum import Enum


class VaultItemKind(str, Enum):
    """Vault item types."""
    image = "image"
    file = "file" 
    link = "link"


class VaultAccessChannel(str, Enum):
    """Access channels."""
    telegram = "telegram"
    web = "web"
    api = "api"


class VaultAccessAction(str, Enum):
    """Access actions."""
    issued = "issued"
    viewed = "viewed"
    downloaded = "downloaded"
    revoked = "revoked"


class VaultItem(SQLModel, table=True):
    __tablename__ = "vault_storage_items"
    """Vault item representing stored assets (images, files, links)."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    persona_id: str = Field(index=True)  # Reference to persona in registry
    kind: VaultItemKind = Field()  # Type of vault item
    name: str = Field()  # Display name/filename
    mime: str = Field()  # MIME type
    size_bytes: int = Field(default=0)  # File size in bytes
    sha256: str = Field(index=True)  # Content hash for deduplication
    storage_key: str = Field(unique=True)  # Storage backend key
    public_url: Optional[str] = Field(default=None)  # Public access URL
    nsfw: bool = Field(default=False)  # NSFW content flag
    enabled: bool = Field(default=True)  # Whether item is active
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    links: list["VaultLink"] = Relationship(back_populates="vault_item")
    access_logs: list["VaultAccessLog"] = Relationship(back_populates="vault_item")
    
    def get_vault_item_id(self) -> str:
        """Get formatted vault item ID."""
        return f"vi_{self.id:03d}" if self.id else "vi_new"


class VaultLink(SQLModel, table=True):
    __tablename__ = "vault_storage_links"
    """Claim link for accessing vault items with expiration and usage limits."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    vault_item_id: int = Field(foreign_key="vault_storage_items.id", index=True)
    claim_code: str = Field(unique=True, default_factory=lambda: f"c_{secrets.token_urlsafe(8)}")  # Unique claim code
    expires_at: datetime = Field()  # When the link expires
    single_use: bool = Field(default=True)  # Whether link can only be used once
    used_count: int = Field(default=0)  # Number of times link has been used
    max_uses: int = Field(default=1)  # Maximum allowed uses
    revoked: bool = Field(default=False)  # Whether link has been revoked
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    vault_item: Optional[VaultItem] = Relationship(back_populates="links")
    access_logs: list["VaultAccessLog"] = Relationship(back_populates="vault_link")
    
    def get_vault_link_id(self) -> str:
        """Get formatted vault link ID."""
        return f"vl_{self.id:03d}" if self.id else "vl_new"
    
    def is_valid(self) -> bool:
        """Check if link is still valid for use."""
        if self.revoked:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.single_use and self.used_count >= 1:
            return False
        if self.used_count >= self.max_uses:
            return False
        return True


class VaultAccessLog(SQLModel, table=True):
    __tablename__ = "vault_storage_access_logs"
    """Access log for tracking vault item and link usage."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    vault_item_id: Optional[int] = Field(foreign_key="vault_storage_items.id", index=True, default=None)
    vault_link_id: Optional[int] = Field(foreign_key="vault_storage_links.id", index=True, default=None)
    channel: VaultAccessChannel = Field()  # Access channel
    consumer_id: Optional[str] = Field(default=None)  # ID of the consumer (user, bot, etc.)
    action: VaultAccessAction = Field()  # Action performed
    ip: Optional[str] = Field(default=None)  # IP address of requester
    ua: Optional[str] = Field(default=None)  # User agent
    ts: datetime = Field(default_factory=datetime.utcnow)  # Timestamp
    
    # Relationships
    vault_item: Optional[VaultItem] = Relationship(back_populates="access_logs")
    vault_link: Optional[VaultLink] = Relationship(back_populates="access_logs")