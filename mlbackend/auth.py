"""
AgriSaathi AI authentication and authorization helpers.

Production behavior is strict: a valid Supabase JWT is required. Any
insecure development bypass must be explicitly enabled with both DEV_MODE
and DEV_ALLOW_INSECURE_AUTH and must never be enabled in deployment config.
"""

import jwt
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
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
    raw_claims: Dict[str, Any] = Field(default_factory=dict)


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """Validate a Supabase JWT. Never decode an unverified token in production."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on this server.",
        )

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm != "HS256":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unsupported authentication algorithm.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True},
        )
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> UserPrincipal:
    """Return the authenticated principal or reject the request."""
    if not credentials:
        if settings.DEV_MODE and settings.DEV_ALLOW_INSECURE_AUTH and not settings.ENFORCE_JWT_AUTH:
            return UserPrincipal(
                user_id="00000000-0000-0000-0000-000000000001",
                email="farmer.dev@localhost",
                role="farmer",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = decode_supabase_jwt(credentials.credentials)
    user_id = claims.get("sub") or claims.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token does not contain a user identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserPrincipal(
        user_id=str(user_id),
        email=claims.get("email"),
        role=claims.get("role", "farmer"),
        phone=claims.get("phone"),
        raw_claims=claims,
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[UserPrincipal]:
    """Optional authentication for explicitly public endpoints."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(allowed_roles: list):
    """Dependency factory ensuring a user has one of the allowed roles."""
    async def role_checker(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        if user.role not in allowed_roles and "admin" not in user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for the requested operation.",
            )
        return user

    return role_checker
