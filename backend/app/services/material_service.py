from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RegionType
from app.core.errors import AppError
from app.domain.models import DesignRevision, Material, MaterialAssignment, MaterialVersion, Region


CATALOG = [
    ("Exterior Paint", "paint", "gallon", "4", None, "38", "22", "10", ["wall", "pillar", "parapet", "gate"]),
    ("Textured Exterior Paint", "textured paint", "gallon", "3", None, "52", "28", "12", ["wall", "pillar", "parapet"]),
    ("Natural Stone Cladding", "cladding", "sqft", "1", None, "18", "9", "12", ["wall", "pillar", "parapet"]),
    ("Exterior Wall Tiles", "tiles", "box", "12", "10", "42", "14", "10", ["wall", "parapet"]),
    ("Glass Railing", "railing", "linear_ft", "1", None, "95", "32", "8", ["balcony"]),
    ("Metal Railing", "railing", "linear_ft", "1", None, "48", "20", "8", ["balcony", "gate"]),
    ("Exterior Decorative Panels", "panels", "sqft", "1", None, "24", "11", "10", ["wall", "pillar", "parapet"]),
]


class MaterialError(AppError):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__("MATERIAL_WORKFLOW_ERROR", message, status_code)


def seed_catalog(session: Session) -> None:
    if session.scalar(select(Material.id).limit(1)):
        return
    for name, category, unit, coverage, pack, material_rate, labor_rate, wastage, surfaces in CATALOG:
        material = Material(name=name, category=category, description=f"Prototype {name.lower()} for exterior renovation.")
        material.versions.append(MaterialVersion(
            unit=unit, coverage_per_unit=Decimal(coverage), pack_size=Decimal(pack) if pack else None,
            material_rate=Decimal(material_rate), labor_rate=Decimal(labor_rate), wastage_percentage=Decimal(wastage),
            rate_currency="USD", specification={"compatible_surface_types": surfaces, "swatch": _swatch(category)},
        ))
        session.add(material)
    session.commit()


def _swatch(category: str) -> str:
    return {"paint": "#d9d1bf", "textured paint": "#b9a887", "cladding": "#9a8063", "tiles": "#c7d1d3", "railing": "#46545b", "panels": "#7b6654"}.get(category, "#b9b9b9")


def _enum_value(value: str | RegionType) -> str:
    return getattr(value, "value", value)


def list_materials(session: Session) -> list[Material]:
    seed_catalog(session)
    return list(session.scalars(select(Material).order_by(Material.name)).unique())


def assign_material(session: Session, design_revision_id: uuid.UUID, region_id: uuid.UUID, material_version_id: uuid.UUID, metadata: dict | None = None) -> MaterialAssignment:
    design = session.get(DesignRevision, design_revision_id)
    region = session.get(Region, region_id)
    version = session.get(MaterialVersion, material_version_id)
    if not design or not region or not version:
        raise MaterialError("The design revision, region, or material was not found.", 404)
    if design.status != "draft" or region.review_status != "approved":
        raise MaterialError("Materials can only be assigned to approved regions.")
    surfaces = (version.specification or {}).get("compatible_surface_types", [])
    region_type = _enum_value(region.region_type)
    if region_type not in surfaces:
        raise MaterialError(f"{version.material.name} is not compatible with {region_type} regions.")
    assignment = session.scalar(select(MaterialAssignment).where(
        MaterialAssignment.design_revision_id == design_revision_id,
        MaterialAssignment.region_id == region_id,
    ))
    if assignment:
        assignment.material_version_id = material_version_id
        assignment.application_metadata = metadata or {}
    else:
        assignment = MaterialAssignment(design_revision_id=design_revision_id, region_id=region_id,
                                        material_version_id=material_version_id, application_metadata=metadata or {})
        session.add(assignment)
    session.commit()
    return assignment