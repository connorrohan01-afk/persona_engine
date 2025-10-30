"""Generic tool endpoint."""

from fastapi import APIRouter, Depends, Request
from typing import Any
from app.security import verify_token

router = APIRouter(prefix="/api/v1", tags=["tools"])


@router.post("/build")
async def build_tool(
    request: Request,
    token: str = Depends(verify_token)
):
    """Generic build tool endpoint."""
    body = await request.json()
    
    return {
        "ok": True,
        "received": body
    }