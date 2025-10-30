"""Bearer token authentication dependency."""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify the Bearer token."""
    if credentials.credentials != settings.auth_bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def require_tenant_access(
    token: str = Depends(verify_token)
) -> str:
    """
    Derive and validate the tenant for the authenticated user.
    
    In the current single-bearer-token architecture, this returns the
    configured default tenant. For multi-tenant production systems,
    this would extract tenant scope from JWT claims or token metadata.
    
    Returns the authorized tenant_id.
    """
    # Current implementation: Use server-configured default tenant
    # In production multi-tenant systems, this would:
    # 1. Extract tenant claims from JWT token
    # 2. Return authorized tenant(s) for this token
    # 3. Apply role-based access control
    
    # For single-bearer-token architecture, use configured default tenant
    # This prevents clients from specifying arbitrary tenant_id values
    return settings.tenant_default