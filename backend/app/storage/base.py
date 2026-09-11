"""Storage adapter interface — BUILD_SPEC section 3.2 rule 3. LocalFileStorage
is the only implementation needed for the laptop MVP; S3FileStorage (Phase 5)
must satisfy the exact same interface so swapping backends is config, not code."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class FileStorage(ABC):
    @abstractmethod
    def put(self, storage_key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def open(self, storage_key: str) -> BinaryIO: ...

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Admin-only retention job, per spec — never called from normal
        request handling."""

    @abstractmethod
    def url_for(self, storage_key: str, expires_seconds: int = 300) -> str:
        """Signed/read-authorized URL. LocalFileStorage returns an internal
        API path the backend still authorizes on every request (section 7:
        'file storage is private by default')."""
