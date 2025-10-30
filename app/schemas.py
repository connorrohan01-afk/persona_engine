"""Shared Pydantic schemas for PersonaEngine API endpoints."""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# =================== Brain Ask Schemas ===================

class BrainAskRequest(BaseModel):
    """Request schema for brain.ask endpoint."""
    question: str = Field(..., description="The question to ask the brain")
    persona_id: Optional[str] = Field(None, description="Optional persona context")
    job_id: Optional[str] = Field(None, description="Optional job context")


class BrainAskResponse(BaseModel):
    """Response schema for brain.ask endpoint."""
    ok: bool = Field(True, description="Success indicator")
    mode: str = Field(..., description="Processing mode (live/fake)")
    answer: str = Field(..., description="Brain's response to the question")
    persona_context: Optional[str] = Field(None, description="Persona context used")
    job_context: Optional[str] = Field(None, description="Job manifest context used")


# =================== Upsell Suggest Schemas ===================

class UpsellSuggestRequest(BaseModel):
    """Request schema for upsell.suggest endpoint."""
    user_id: str = Field(..., description="User identifier")
    persona_id: Optional[str] = Field(None, description="Persona context")
    job_id: Optional[str] = Field(None, description="Job context")
    style: Optional[str] = Field("studio", description="Style preference")
    intent: Optional[str] = Field("prints", description="Intent category")


class UpsellSuggestion(BaseModel):
    """Individual upsell suggestion."""
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    price_range: str = Field(..., description="Price range")
    confidence: float = Field(..., description="Confidence score 0-1")


class UpsellSuggestResponse(BaseModel):
    """Response schema for upsell.suggest endpoint."""
    ok: bool = Field(True, description="Success indicator")
    mode: str = Field(..., description="Processing mode (live/fake)")
    suggestions: List[UpsellSuggestion] = Field(..., description="Upsell suggestions")
    context: Dict[str, Any] = Field(..., description="Context metadata")


# =================== Persona Add System Schemas ===================

class PersonaAddSystemRequest(BaseModel):
    """Request schema for persona.add_system endpoint."""
    id: str = Field(..., description="Persona identifier")
    name: str = Field(..., description="Persona name")
    role: str = Field("system", description="Persona role")
    traits: List[str] = Field(..., description="Persona traits list")


class PersonaAddSystemResponse(BaseModel):
    """Response schema for persona.add_system endpoint."""
    ok: bool = Field(True, description="Success indicator")
    system_persona: Dict[str, Any] = Field(..., description="Created persona data")


# =================== Persona New Schemas ===================

class PersonaNewRequest(BaseModel):
    """Request schema for persona.new endpoint."""
    name: str = Field(..., description="Persona name")
    role: str = Field("user", description="Persona role")
    traits: List[str] = Field(default_factory=list, description="Persona traits")


class PersonaNewResponse(BaseModel):
    """Response schema for persona.new endpoint."""
    ok: bool = Field(True, description="Success indicator")
    persona_id: str = Field(..., description="Generated persona ID")
    persona: Dict[str, Any] = Field(..., description="Created persona data")


# =================== Gen Schemas ===================

class GenRequest(BaseModel):
    """Request schema for gen endpoint."""
    persona_id: str = Field(..., description="Persona identifier")
    style: str = Field("studio", description="Style preference")
    count: int = Field(6, description="Number of images to generate")
    slots: Optional[Dict[str, str]] = Field(default_factory=dict, description="Generation slots (outfit, mood, setting, etc)")


class GenResponse(BaseModel):
    """Response schema for gen endpoint."""
    ok: bool = Field(True, description="Success indicator")
    mode: str = Field(..., description="Processing mode (live/fake)")
    job_id: str = Field(..., description="Generated job identifier")
    images: List[Dict[str, Any]] = Field(..., description="Generated images")
    manifest: Dict[str, Any] = Field(..., description="Generation manifest")


# =================== Vault Open Schemas ===================

class VaultOpenRequest(BaseModel):
    """Request schema for vault.open endpoint."""
    job_id: str = Field(..., description="Job identifier")


class VaultOpenResponse(BaseModel):
    """Response schema for vault.open endpoint."""
    ok: bool = Field(True, description="Success indicator")
    mode: str = Field(..., description="Processing mode (live/fake)")
    images: List[Dict[str, Any]] = Field(..., description="Vault images")
    manifest: Dict[str, Any] = Field(..., description="Job manifest")


# =================== Status Schemas ===================

class HealthResponse(BaseModel):
    """Enhanced health response schema."""
    ok: bool = Field(True, description="System health status")
    mode_llm: str = Field(..., description="LLM provider mode")
    last_upsell: Optional[Dict[str, Any]] = Field(None, description="Last upsell activity")
    timestamp: str = Field(..., description="Response timestamp")


class StatusResponse(BaseModel):
    """Enhanced status response schema."""
    ok: bool = Field(True, description="System status")
    persona_count: Optional[int] = Field(None, description="Total persona count")
    job_count: Optional[int] = Field(None, description="Total job count")
    latest_persona_id: Optional[str] = Field(None, description="Latest persona ID")
    latest_job_id: Optional[str] = Field(None, description="Latest job ID")
    last_upsell: Optional[Dict[str, Any]] = Field(None, description="Last upsell activity")
    timestamp: Optional[str] = Field(None, description="Response timestamp")
    error: Optional[str] = Field(None, description="Error message if any")


# =================== Error Schemas ===================

class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str = Field(..., description="Error message")
    details: Optional[List[ValidationErrorDetail]] = Field(None, description="Validation details")
    request_id: Optional[str] = Field(None, description="Request UUID for tracing")