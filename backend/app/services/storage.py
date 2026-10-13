"""Blob storage for uploaded files and their extracted text: local disk or Google Cloud Storage.

Blocking I/O runs through asyncio.to_thread, which carries the request's ContextVars (client id)
into the worker thread (spec D8).
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..core.config import Settings, get_settings


@dataclass(frozen=True)
class ObjectInfo:
    size: int
    updated: datetime


class Storage(ABC):
    @abstractmethod
    async def save_bytes(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    async def read_text(self, key: str) -> Optional[str]: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...

    @abstractmethod
    async def list_prefix(self, prefix: str) -> List[str]: ...

    @abstractmethod
    async def info(self, key: str) -> Optional[ObjectInfo]: ...


class LocalStorage(Storage):
    """Files under a root directory (UPLOAD_DIR); keys are '/'-separated relative paths."""

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        root = self.root.resolve()
        path = (self.root / key).resolve()
        if root not in path.parents:
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    async def save_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(write)

    async def read_text(self, key: str) -> Optional[str]:
        path = self._path(key)
        return await asyncio.to_thread(lambda: path.read_text(encoding="utf-8") if path.is_file() else None)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._path(key).is_file)

    async def delete(self, key: str) -> bool:
        path = self._path(key)

        def remove() -> bool:
            if not path.is_file():
                return False
            path.unlink()
            return True

        return await asyncio.to_thread(remove)

    async def list_prefix(self, prefix: str) -> List[str]:
        def scan() -> List[str]:
            keys = (p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())
            return sorted(key for key in keys if key.startswith(prefix))

        return await asyncio.to_thread(scan)

    async def info(self, key: str) -> Optional[ObjectInfo]:
        path = self._path(key)

        def stat() -> Optional[ObjectInfo]:
            if not path.is_file():
                return None
            st = path.stat()
            return ObjectInfo(size=st.st_size, updated=datetime.fromtimestamp(st.st_mtime))

        return await asyncio.to_thread(stat)


class GCSStorage(Storage):
    """Objects in a Cloud Storage bucket (GCS_BUCKET), using Application Default Credentials."""

    def __init__(self, bucket_name: str, client=None):
        if client is None:
            from google.cloud import storage as gcs

            client = gcs.Client()
        self._client = client
        self._bucket_name = bucket_name
        self._bucket = client.bucket(bucket_name)

    async def save_bytes(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(self._bucket.blob(key).upload_from_string, data)

    async def read_text(self, key: str) -> Optional[str]:
        def read() -> Optional[str]:
            blob = self._bucket.get_blob(key)
            return None if blob is None else blob.download_as_text(encoding="utf-8")

        return await asyncio.to_thread(read)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._bucket.blob(key).exists)

    async def delete(self, key: str) -> bool:
        def remove() -> bool:
            blob = self._bucket.get_blob(key)
            if blob is None:
                return False
            blob.delete()
            return True

        return await asyncio.to_thread(remove)

    async def list_prefix(self, prefix: str) -> List[str]:
        return await asyncio.to_thread(
            lambda: sorted(blob.name for blob in self._client.list_blobs(self._bucket_name, prefix=prefix))
        )

    async def info(self, key: str) -> Optional[ObjectInfo]:
        def stat() -> Optional[ObjectInfo]:
            blob = self._bucket.get_blob(key)
            return None if blob is None else ObjectInfo(size=blob.size, updated=blob.updated)

        return await asyncio.to_thread(stat)


def build_storage(settings: Optional[Settings] = None) -> Storage:
    s = settings or get_settings()
    if s.storage_backend == "gcs":
        return GCSStorage(s.gcs_bucket)
    return LocalStorage(s.upload_dir)
