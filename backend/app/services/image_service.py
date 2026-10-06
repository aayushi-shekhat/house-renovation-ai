from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ImageProcessingError, ProjectNotFoundError, StorageError, UploadValidationError
from app.domain.models import Asset, Image, Project
from app.services.image_processing import create_canonical_image
from app.services.image_validator import ImageValidationResult, validate_image
from app.storage.protocol import StorageProvider


def upload_image(
    session: Session,
    storage: StorageProvider,
    settings: Settings,
    project_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> tuple[Image, ImageValidationResult]:
    if session.get(Project, project_id) is None:
        raise ProjectNotFoundError()

    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise UploadValidationError("UNSUPPORTED_FILE", "Choose a JPEG, PNG, or WEBP image.", 415)
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise UploadValidationError("UNSUPPORTED_FILE", "Choose a JPEG, PNG, or WEBP image.", 415)

    result = validate_image(content, settings)
    if result.status == "rejected":
        reason = result.reasons[0]
        status_code = 413 if reason.code == "FILE_TOO_LARGE" else 422
        raise UploadValidationError(reason.code, reason.message, status_code, reasons=[reason.__dict__])
    assert result.decoded is not None
    if result.decoded.media_type != content_type:
        raise UploadValidationError("MIME_MISMATCH", "The file content does not match its declared type.", 415)

    image_id = uuid.uuid4()
    original_id = uuid.uuid4()
    processing_id = uuid.uuid4()
    try:
        canonical = create_canonical_image(result.decoded)
    except Exception as exc:
        raise ImageProcessingError() from exc
    original_key = f"projects/{project_id}/images/{image_id}/original{suffix}"
    processing_key = f"projects/{project_id}/images/{image_id}/processing.png"
    try:
        original = storage.put(io.BytesIO(content), original_key, result.decoded.media_type)
        processed = storage.put(io.BytesIO(canonical), processing_key, "image/png")
    except Exception as exc:
        for key in (original_key, processing_key):
            try:
                storage.delete(key)
            except Exception:
                pass
        raise StorageError() from exc

    original_asset = Asset(
        id=original_id,
        storage_key=original.storage_key,
        media_type=original.media_type,
        byte_size=original.byte_size,
        width=result.decoded.width,
        height=result.decoded.height,
        sha256=hashlib.sha256(content).hexdigest(),
        metadata_json={"role": "original"},
    )
    processing_asset = Asset(
        id=processing_id,
        storage_key=processed.storage_key,
        media_type=processed.media_type,
        byte_size=processed.byte_size,
        width=result.decoded.width,
        height=result.decoded.height,
        sha256=hashlib.sha256(canonical).hexdigest(),
        metadata_json={"role": "processing", "format": "RGB PNG"},
    )
    image = Image(
        id=image_id,
        project_id=project_id,
        original_asset_id=original_id,
        processing_asset_id=processing_id,
        validation_status=result.status,
        validation_metadata={"reasons": [reason.__dict__ for reason in result.reasons]},
    )
    session.add_all([original_asset, processing_asset, image])
    session.commit()
    return image, result