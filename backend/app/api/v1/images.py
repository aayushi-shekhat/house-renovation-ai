from __future__ import annotations

import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.schemas.image_upload import ImageUploadResponse, ValidationReason
from app.services.image_service import upload_image
from app.storage.local import LocalFilesystemStorage

router = APIRouter(tags=["images"])


def get_storage(settings: Settings = Depends(get_settings)) -> LocalFilesystemStorage:
    return LocalFilesystemStorage(Path(settings.storage_root))


@router.post("/projects/{project_id}/images", response_model=ImageUploadResponse)
async def create_image(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    storage: LocalFilesystemStorage = Depends(get_storage),
) -> ImageUploadResponse | JSONResponse:
    try:
        content = await file.read(settings.max_upload_bytes + 1)
        image, result = upload_image(
            session, storage, settings, project_id, file.filename or "upload", file.content_type, content
        )
    except AppError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )
    return ImageUploadResponse(
        image_id=image.id,
        project_id=image.project_id,
        validation_status=result.status,
        width=result.decoded.width if result.decoded else None,
        height=result.decoded.height if result.decoded else None,
        original_asset_id=image.original_asset_id,
        processing_asset_id=image.processing_asset_id,
        validation_reasons=[ValidationReason.model_validate(reason.__dict__) for reason in result.reasons],
    )