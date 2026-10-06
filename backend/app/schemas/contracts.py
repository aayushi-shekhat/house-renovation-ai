from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import JobState, RegionType, ReviewStatus, RevisionStatus


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectRead(APIModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AssetRead(APIModel):
    id: uuid.UUID
    storage_key: str
    media_type: str
    byte_size: int
    width: int | None
    height: int | None


class RegionRead(APIModel):
    id: uuid.UUID
    region_set_id: uuid.UUID
    region_type: RegionType
    confidence: Decimal | None
    review_status: ReviewStatus
    mask_asset_id: uuid.UUID | None
    polygon: list | None
    area_pixels: int | None


class RegionSetRead(APIModel):
    id: uuid.UUID
    image_id: uuid.UUID
    revision_number: int
    status: RevisionStatus
    regions: list[RegionRead] = []


class ImageRead(APIModel):
    id: uuid.UUID
    project_id: uuid.UUID
    original_asset_id: uuid.UUID
    processing_asset_id: uuid.UUID | None
    validation_status: str
    validation_metadata: dict


class MaterialVersionRead(APIModel):
    id: uuid.UUID
    material_id: uuid.UUID
    unit: str
    material_rate: Decimal
    labor_rate: Decimal
    wastage_percentage: Decimal
    coverage_per_unit: Decimal | None
    pack_size: Decimal | None
    rate_currency: str
    specification: dict


class MaterialRead(APIModel):
    id: uuid.UUID
    name: str
    category: str
    description: str | None
    versions: list[MaterialVersionRead] = []


class MaterialAssignmentCreate(BaseModel):
    region_id: uuid.UUID
    material_version_id: uuid.UUID
    application_metadata: dict = {}


class DesignRevisionRead(APIModel):
    id: uuid.UUID
    project_id: uuid.UUID
    region_set_id: uuid.UUID
    revision_number: int
    status: RevisionStatus


class MeasurementRead(APIModel):
    id: uuid.UUID
    measurement_revision_id: uuid.UUID
    region_id: uuid.UUID
    quantity: Decimal
    unit: str
    source: str
    measurement_metadata: dict


class MeasurementRevisionRead(APIModel):
    id: uuid.UUID
    design_revision_id: uuid.UUID
    method: str
    assumptions: dict
    measurements: list[MeasurementRead] = []


class EstimateLineRead(APIModel):
    id: uuid.UUID
    estimate_id: uuid.UUID
    region_id: uuid.UUID | None
    category: str
    description: str
    quantity: Decimal
    unit: str
    material_cost: Decimal
    labor_cost: Decimal
    rate_snapshot: dict


class EstimateRead(APIModel):
    id: uuid.UUID
    design_revision_id: uuid.UUID
    measurement_revision_id: uuid.UUID
    currency: str
    material_total: Decimal
    labor_total: Decimal
    grand_total: Decimal
    assumptions: dict
    lines: list[EstimateLineRead] = []


class RenderRead(APIModel):
    id: uuid.UUID
    design_revision_id: uuid.UUID
    source_image_id: uuid.UUID
    output_asset_id: uuid.UUID | None
    provider: str
    status: str
    provider_metadata: dict


class ReportRead(APIModel):
    id: uuid.UUID
    project_id: uuid.UUID
    estimate_id: uuid.UUID
    report_asset_id: uuid.UUID | None
    status: str


class JobRead(APIModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    job_type: str
    state: JobState
    progress: int
    error_message: str | None
    payload: dict
    result: dict
