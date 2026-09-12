"""GET /api/v1/files/by-key/{storage_key} — serves photo bytes. Unauthenticated
by design in this MVP: storage_key is an opaque, server-generated identifier
(never a guessable path) and the route itself is the whole auth boundary for
now (see storage/local.py's url_for docstring) — download of DOCX reports is
the one route that actually needs a signed-in user this phase."""
from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_db
from app.core.config import get_settings
from app.storage.local import LocalFileStorage

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.get("/by-key/{storage_key:path}")
async def get_file(storage_key: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    file_doc = await db.files.find_one({"storage_key": storage_key, "is_deleted": {"$ne": True}})
    if not file_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")

    settings = get_settings()
    if settings.file_storage_backend != "local":
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Only local file storage is wired up in this phase")
    storage = LocalFileStorage(settings.file_storage_root)
    try:
        handle = storage.open(storage_key)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing from storage")

    def _chunks(f, size: int = 64 * 1024):
        try:
            while chunk := f.read(size):
                yield chunk
        finally:
            f.close()

    content_type = file_doc.get("content_type") or mimetypes.guess_type(storage_key)[0] or "application/octet-stream"
    return StreamingResponse(_chunks(handle), media_type=content_type)
