"""Phase 2: health endpoints + the read API the dashboard talks to (summary,
survey list/detail, reports, file serving, login). Write/sync endpoints are
still Phase 3 (BUILD_SPEC section 16)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, files, surveys
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

app.include_router(auth.router)
app.include_router(surveys.router)
app.include_router(files.router)


@app.get("/healthz")
async def healthz():
    """Process alive — BUILD_SPEC section 12."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Atlas reachable — BUILD_SPEC section 12."""
    ok = await ping() if settings.mongodb_uri else False
    return {"status": "ok" if ok else "not_ready", "mongodb": ok}
