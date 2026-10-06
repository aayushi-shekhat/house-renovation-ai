from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from app.storage.protocol import StoredAsset


class LocalFilesystemStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if self.root not in path.parents:
            raise ValueError("Storage key escapes the storage root")
        return path

    def put(self, source: BinaryIO, storage_key: str, media_type: str) -> StoredAsset:
        destination = self.path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.uploading")
        try:
            with temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return StoredAsset(storage_key, media_type, destination.stat().st_size)

    def open(self, storage_key: str) -> BinaryIO:
        return self.path_for(storage_key).open("rb")

    def delete(self, storage_key: str) -> None:
        path = self.path_for(storage_key)
        if path.exists():
            path.unlink()
