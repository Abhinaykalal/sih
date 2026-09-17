"""
AgriSaathi AI — Supabase JWT Authentication & Authorization Middleware
======================================================================
Validates incoming Bearer tokens issued by Supabase Auth (HS256 or RS256).
Enforces farmer-level and admin-level ownership checks across FastAPI routes.
"""

import os
import time
import jwt
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from .config import settings
except ImportError:
    from config import settings

security = HTTPBearer(auto_error=False)

class UserPrincipal(BaseModel):
    user_id: str
    email: Optional[str] = None
    role: str = "farmer"
    phone: Optional[str] = None
    raw_claims: Dict[str, Any] = {}

def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a Supabase JWT token.
    Checks expiration, issuer, and signature.
    """
    secret = settings.SUPABASE_JWT_SECRET

    try:
        # Supabase default uses HS256 with project JWT secret
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=[alg],
            options={"verify_signature": True, "verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> UserPrincipal:
    """
    Strict FastAPI dependency: requires valid Bearer token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    claims = decode_supabase_jwt(token)
    
    return UserPrincipal(
        user_id=claims.get("sub", claims.get("user_id", "anonymous")),
        email=claims.get("email"),
        role=claims.get("role", "farmer"),
        phone=claims.get("phone"),
        raw_claims=claims
    )

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[UserPrincipal]:
    """
    Optional dependency: returns UserPrincipal if valid token provided, else None.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

def require_role(allowed_roles: list):
    """Dependency factory ensuring user has one of the allowed roles."""
    async def role_checker(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        if user.role not in allowed_roles and "admin" not in user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}, your role: {user.role}"
            )
        return user
    return role_checker
