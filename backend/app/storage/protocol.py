from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredAsset:
    storage_key: str
    media_type: str
    byte_size: int


class StorageProvider(Protocol):
    def put(self, source: BinaryIO, storage_key: str, media_type: str) -> StoredAsset:
        ...

    def open(self, storage_key: str) -> BinaryIO:
        ...

    def delete(self, storage_key: str) -> None:
        ...

    def path_for(self, storage_key: str) -> Path:
        ...
