from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import RegionType


class RegionCreate(BaseModel):
    region_type: RegionType
    polygon: list[list[float]] = Field(min_length=3)


class RegionUpdate(BaseModel):
    region_type: RegionType | None = None
    polygon: list[list[float]] | None = Field(default=None, min_length=3)


class MeasurementEntry(BaseModel):
    region_id: uuid.UUID
    manual_area_sqft: Decimal | None = None
    length_ft: Decimal | None = None
    assumptions: dict = {}


class MeasurementCreate(BaseModel):
    reference_pixels: Decimal | None = None
    reference_feet: Decimal | None = None
    entries: list[MeasurementEntry]


class EstimateCreate(BaseModel):
    measurement_revision_id: uuid.UUID
    currency: str = "USD"


class RateUpdate(BaseModel):
    line_id: uuid.UUID
    material_rate: Decimal | None = None
    labor_rate: Decimal | None = None


class AssignmentCreate(BaseModel):
    region_id: uuid.UUID
    material_version_id: uuid.UUID
    application_metadata: dict = {}