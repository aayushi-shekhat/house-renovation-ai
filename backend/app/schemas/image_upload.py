from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ValidationReason(BaseModel):
    code: str
    message: str
    severity: Literal["warning", "error"]


class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_id: uuid.UUID
    project_id: uuid.UUID
    validation_status: Literal["accepted", "accepted_with_warnings", "rejected"]
    width: int | None
    height: int | None
    original_asset_id: uuid.UUID | None
    processing_asset_id: uuid.UUID | None
    validation_reasons: list[ValidationReason]