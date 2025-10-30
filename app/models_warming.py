"""Warming system SQLModel classes for PersonaEngine."""

from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, Any
import json


class WarmingPlan(SQLModel, table=True):
    """Warming plan for an account on a platform."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True)
    platform: str = Field()  # e.g., "reddit", "twitter", etc.
    account_id: str = Field(index=True)  # Reference to account
    enabled: bool = Field(default=True)
    window_start: str = Field()  # e.g., "08:00"
    window_end: str = Field()  # e.g., "22:00"
    actions_per_day: int = Field(default=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    actions: list["WarmingAction"] = Relationship(back_populates="plan")
    runs: list["WarmingRun"] = Relationship(back_populates="plan")


class WarmingAction(SQLModel, table=True):
    """Action to be performed as part of a warming plan."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="warmingplan.id", index=True)
    kind: str = Field()  # e.g., "view_sub", "upvote", "comment_short", "post_text", "post_image", "save_post"
    params_json: str = Field(default="{}")  # JSON string of action parameters
    weight: int = Field(default=1)  # Weight for random selection
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    plan: Optional[WarmingPlan] = Relationship(back_populates="actions")
    
    @property
    def params(self) -> dict[str, Any]:
        """Get action parameters as dict."""
        try:
            return json.loads(self.params_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @params.setter
    def params(self, value: dict[str, Any]) -> None:
        """Set action parameters from dict."""
        self.params_json = json.dumps(value)


class WarmingRun(SQLModel, table=True):
    """Record of a warming run execution."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="warmingplan.id", index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)
    actions_attempted: int = Field(default=0)
    actions_succeeded: int = Field(default=0)
    mode: str = Field()  # "live" or "dry"
    
    # Relationships
    plan: Optional[WarmingPlan] = Relationship(back_populates="runs")
    logs: list["WarmingLog"] = Relationship(back_populates="run")


class WarmingLog(SQLModel, table=True):
    """Log entry for individual action within a warming run."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="warmingrun.id", index=True)
    account_id: str = Field(index=True)
    action_kind: str = Field()  # Type of action performed
    status: str = Field()  # "ok", "skipped", "failed"
    error: Optional[str] = Field(default=None)  # Error message if failed
    meta_json: str = Field(default="{}")  # Additional metadata as JSON
    ts: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    run: Optional[WarmingRun] = Relationship(back_populates="logs")
    
    @property
    def meta(self) -> dict[str, Any]:
        """Get metadata as dict."""
        try:
            return json.loads(self.meta_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @meta.setter
    def meta(self, value: dict[str, Any]) -> None:
        """Set metadata from dict."""
        self.meta_json = json.dumps(value)