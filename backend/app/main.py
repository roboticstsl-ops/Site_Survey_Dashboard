"""Phase 0/1 skeleton — health endpoints + CORS only. Auth, CRUD, sync and
dashboard routers land in Phase 2/3 (BUILD_SPEC section 16) once there's a
real Atlas connection and secrets to test against."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.client import ping

settings = get_settings()

app = FastAPI(title="Elevator RF Survey API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    """Process alive — BUILD_SPEC section 12."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Atlas reachable — BUILD_SPEC section 12."""
    ok = await ping() if settings.mongodb_uri else False
    return {"status": "ok" if ok else "not_ready", "mongodb": ok}
