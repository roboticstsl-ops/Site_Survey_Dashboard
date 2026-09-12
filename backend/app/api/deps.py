"""Shared FastAPI dependencies: DB handle + the auth boundary for endpoints
that require a signed-in user (BUILD_SPEC section 5 — download endpoints are
the one place in this phase that must be authenticated)."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import decode_access_token
from app.db.client import get_db as _get_db

_bearer = HTTPBearer(auto_error=False)


def get_db() -> AsyncIOMotorDatabase:
    return _get_db()


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = await db.users.find_one({"email": payload["sub"], "is_active": True})
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    user["_id"] = str(user["_id"])
    return user
