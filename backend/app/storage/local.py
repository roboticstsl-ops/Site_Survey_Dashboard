"""Laptop MVP storage: a private directory outside the repo/static tree,
configured by FILE_STORAGE_ROOT (BUILD_SPEC section 7 / 12). Every read still
goes through an authenticated API route — this class never gets exposed as a
static file mount."""
from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

from app.storage.base import FileStorage


class LocalFileStorage(FileStorage):
    def __init__(self, root: str):
        if not root:
            raise ValueError("FILE_STORAGE_ROOT is not set")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, storage_key: str) -> Path:
        # storage_key is server-generated (UUID-based, spec section 7) — still
        # resolve-and-check so a crafted key can never escape the root.
        p = (self.root / storage_key).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError("storage_key escapes storage root")
        return p

    def put(self, storage_key: str, data: bytes, content_type: str) -> None:
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def open(self, storage_key: str) -> BinaryIO:
        return open(self._path(storage_key), "rb")

    def delete(self, storage_key: str) -> None:
        path = self._path(storage_key)
        if path.exists():
            os.remove(path)

    def url_for(self, storage_key: str, expires_seconds: int = 300) -> str:
        # laptop MVP: the API route itself is the authorization boundary,
        # there is no separate signed-URL mechanism yet.
        return f"/api/v1/files/by-key/{storage_key}"
