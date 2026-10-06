from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] = field(default_factory=dict)


class ProjectNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("PROJECT_NOT_FOUND", "The requested project was not found.", 404)


class UploadValidationError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 422, **details: Any) -> None:
        super().__init__(code, message, status_code, details)


class ImageProcessingError(AppError):
    def __init__(self, message: str = "The image could not be processed.") -> None:
        super().__init__("IMAGE_PROCESSING_FAILED", message, 422)


class StorageError(AppError):
    def __init__(self) -> None:
        super().__init__("STORAGE_FAILED", "The image could not be stored.", 503)