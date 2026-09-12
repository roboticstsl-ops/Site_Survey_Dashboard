"""POST /api/v1/auth/login — the one auth endpoint this phase needs. Issues a
short-lived JWT for the download endpoint; no refresh-token flow yet (Phase 2
scope, see BUILD_SPEC section 5.3 for the fuller plan)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.api.deps import get_db
from app.core.security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": body.email, "is_active": True})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    await db.users.update_one(
        {"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )
    token = create_access_token(subject=user["email"], role=user["role"])
    return LoginResponse(
        access_token=token,
        user={
            "email": user["email"],
            "display_name": user["display_name"],
            "role": user["role"],
        },
    )
