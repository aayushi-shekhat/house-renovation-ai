from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base
from app.core.enums import JobState, RegionType, ReviewStatus, RevisionStatus


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    images: Mapped[list[Image]] = relationship(back_populates="project", cascade="all, delete-orphan")
    design_revisions: Mapped[list[DesignRevision]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list[Job]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Image(TimestampMixin, Base):
    __tablename__ = "images"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    original_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"))
    processing_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    validation_status: Mapped[str] = mapped_column(String(40), default="pending")
    validation_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    project: Mapped[Project] = relationship(back_populates="images")
    region_sets: Mapped[list[RegionSet]] = relationship(back_populates="image", cascade="all, delete-orphan")


class RegionSet(TimestampMixin, Base):
    __tablename__ = "region_sets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"))
    revision_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[RevisionStatus] = mapped_column(String(30), default=RevisionStatus.DRAFT)
    provider_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    image: Mapped[Image] = relationship(back_populates="region_sets")
    regions: Mapped[list[Region]] = relationship(back_populates="region_set", cascade="all, delete-orphan")


class Region(TimestampMixin, Base):
    __tablename__ = "regions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    region_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("region_sets.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    region_type: Mapped[RegionType] = mapped_column(String(30))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    review_status: Mapped[ReviewStatus] = mapped_column(String(30), default=ReviewStatus.PROPOSED)
    mask_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    polygon: Mapped[list | None] = mapped_column(JSON)
    geometry_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    area_pixels: Mapped[int | None] = mapped_column(Integer)
    region_set: Mapped[RegionSet] = relationship(back_populates="regions")
    parent: Mapped[Region | None] = relationship(remote_side=[id])


class Material(TimestampMixin, Base):
    __tablename__ = "materials"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    versions: Mapped[list[MaterialVersion]] = relationship(back_populates="material", cascade="all, delete-orphan")


class MaterialVersion(TimestampMixin, Base):
    __tablename__ = "material_versions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"))
    unit: Mapped[str] = mapped_column(String(30))
    material_rate: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    labor_rate: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    wastage_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    coverage_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    pack_size: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    rate_currency: Mapped[str] = mapped_column(String(3), default="USD")
    specification: Mapped[dict] = mapped_column(JSON, default=dict)
    material: Mapped[Material] = relationship(back_populates="versions")


class DesignRevision(TimestampMixin, Base):
    __tablename__ = "design_revisions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    region_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("region_sets.id"))
    revision_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[RevisionStatus] = mapped_column(String(30), default=RevisionStatus.DRAFT)
    project: Mapped[Project] = relationship(back_populates="design_revisions")
    assignments: Mapped[list[MaterialAssignment]] = relationship(back_populates="design_revision", cascade="all, delete-orphan")
    measurement_revisions: Mapped[list[MeasurementRevision]] = relationship(back_populates="design_revision", cascade="all, delete-orphan")
    renders: Mapped[list[Render]] = relationship(back_populates="design_revision", cascade="all, delete-orphan")
    estimates: Mapped[list[Estimate]] = relationship(back_populates="design_revision", cascade="all, delete-orphan")


class MaterialAssignment(TimestampMixin, Base):
    __tablename__ = "material_assignments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    design_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("design_revisions.id", ondelete="CASCADE"))
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))
    material_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("material_versions.id"))
    application_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    design_revision: Mapped[DesignRevision] = relationship(back_populates="assignments")


class MeasurementRevision(TimestampMixin, Base):
    __tablename__ = "measurement_revisions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    design_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("design_revisions.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(50))
    assumptions: Mapped[dict] = mapped_column(JSON, default=dict)
    design_revision: Mapped[DesignRevision] = relationship(back_populates="measurement_revisions")
    measurements: Mapped[list[Measurement]] = relationship(back_populates="measurement_revision", cascade="all, delete-orphan")


class Measurement(TimestampMixin, Base):
    __tablename__ = "measurements"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    measurement_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("measurement_revisions.id", ondelete="CASCADE"))
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(50))
    measurement_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    measurement_revision: Mapped[MeasurementRevision] = relationship(back_populates="measurements")


class Estimate(TimestampMixin, Base):
    __tablename__ = "estimates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    design_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("design_revisions.id", ondelete="CASCADE"))
    measurement_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("measurement_revisions.id"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    material_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    labor_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    assumptions: Mapped[dict] = mapped_column(JSON, default=dict)
    design_revision: Mapped[DesignRevision] = relationship(back_populates="estimates")
    lines: Mapped[list[EstimateLine]] = relationship(back_populates="estimate", cascade="all, delete-orphan")


class EstimateLine(TimestampMixin, Base):
    __tablename__ = "estimate_lines"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estimates.id", ondelete="CASCADE"))
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit: Mapped[str] = mapped_column(String(30))
    material_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    rate_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    estimate: Mapped[Estimate] = relationship(back_populates="lines")


class Render(TimestampMixin, Base):
    __tablename__ = "renders"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    design_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("design_revisions.id", ondelete="CASCADE"))
    source_image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id"))
    output_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    provider: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    provider_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    design_revision: Mapped[DesignRevision] = relationship(back_populates="renders")


class Report(TimestampMixin, Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    estimate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("estimates.id"))
    original_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"))
    redesigned_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    report_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    job_type: Mapped[str] = mapped_column(String(100))
    state: Mapped[JobState] = mapped_column(String(30), default=JobState.QUEUED)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    project: Mapped[Project | None] = relationship(back_populates="jobs")


__all__ = [
    "Asset", "DesignRevision", "Estimate", "EstimateLine", "Image", "Job",
    "Material", "MaterialAssignment", "MaterialVersion", "Measurement",
    "MeasurementRevision", "Project", "Region", "RegionSet", "Render", "Report",
]
