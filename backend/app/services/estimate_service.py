from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.models import DesignRevision, Estimate, EstimateLine, MaterialAssignment, MaterialVersion, Measurement, MeasurementRevision, Region
from app.engines.calculations import calculate_cost, calculate_quantity


class EstimateError(AppError):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__("ESTIMATE_WORKFLOW_ERROR", message, status_code)


def create_measurements(session: Session, design_revision_id: uuid.UUID, entries: list[dict], reference_pixels: Decimal | None, reference_feet: Decimal | None) -> MeasurementRevision:
    design = session.get(DesignRevision, design_revision_id)
    if not design or design.status != "draft":
        raise EstimateError("The design revision was not found or is not editable.", 404)
    scale = (reference_feet / reference_pixels) if reference_pixels and reference_feet and reference_pixels > 0 else None
    revision = MeasurementRevision(design_revision_id=design_revision_id, method="manual", assumptions={
        "reference_pixels": str(reference_pixels) if reference_pixels else None,
        "reference_feet": str(reference_feet) if reference_feet else None,
        "scale_feet_per_pixel": str(scale) if scale else None,
        "accuracy": "approximate; not survey-grade",
    })
    for entry in entries:
        region = session.get(Region, uuid.UUID(str(entry["region_id"])))
        if not region:
            raise EstimateError("A measurement region was not found.")
        area = Decimal(str(entry["manual_area_sqft"])) if entry.get("manual_area_sqft") is not None else None
        if area is None and scale is None:
            raise EstimateError("Provide a manual area or a known reference dimension before measuring.")
        if area is None:
            if scale is None:
                raise EstimateError("Provide a manual area or a known reference dimension before measuring.")
            area = Decimal(str(region.area_pixels or 0)) * scale * scale
        quantity = Decimal(str(entry.get("length_ft", area))) if entry.get("length_ft") is not None else area
        revision.measurements.append(Measurement(
            region_id=region.id, quantity=quantity, unit="linear_ft" if entry.get("length_ft") is not None else "sqft",
            source="manual" if entry.get("manual_area_sqft") is not None else "reference_scale",
            measurement_metadata={"area_sqft": str(area), "approximate": True, "assumptions": entry.get("assumptions", {})},
        ))
    session.add(revision)
    session.commit()
    return revision


def create_estimate(session: Session, design_revision_id: uuid.UUID, measurement_revision_id: uuid.UUID, currency: str = "USD") -> Estimate:
    design = session.get(DesignRevision, design_revision_id)
    measurement_revision = session.get(MeasurementRevision, measurement_revision_id)
    if not design or not measurement_revision:
        raise EstimateError("The design or measurement revision was not found.", 404)
    assignments = list(session.scalars(select(MaterialAssignment).where(MaterialAssignment.design_revision_id == design_revision_id)))
    measurements = {measurement.region_id: measurement for measurement in measurement_revision.measurements}
    if not assignments:
        raise EstimateError("Assign at least one material before calculating an estimate.")
    estimate = Estimate(design_revision_id=design_revision_id, measurement_revision_id=measurement_revision_id, currency=currency, assumptions={"advisory": True})
    for assignment in assignments:
        region = session.get(Region, assignment.region_id)
        version = session.get(MaterialVersion, assignment.material_version_id)
        measurement = measurements.get(assignment.region_id)
        if not region or not version or not measurement:
            continue
        area = Decimal(str((measurement.measurement_metadata or {}).get("area_sqft", measurement.quantity)))
        length = measurement.quantity if measurement.unit == "linear_ft" else None
        quantity_result = calculate_quantity(area, version.material.category, version.coverage_per_unit, version.pack_size, version.wastage_percentage, Decimal(str((assignment.application_metadata or {}).get("coats", 1))), length)
        material_cost, labor_cost = calculate_cost(quantity_result.purchasable_quantity, version.material_rate, version.labor_rate, area if length is None else length)
        estimate.lines.append(EstimateLine(region_id=region.id, category=version.material.category, description=version.material.name,
                                            quantity=quantity_result.purchasable_quantity, unit=quantity_result.unit,
                                            material_cost=material_cost, labor_cost=labor_cost,
                                            rate_snapshot={"material_rate": str(version.material_rate), "labor_rate": str(version.labor_rate), "base_quantity": str(quantity_result.base_quantity), "wastage_percentage": str(version.wastage_percentage), "packs": quantity_result.packs}))
    estimate.material_total = sum((line.material_cost for line in estimate.lines), Decimal("0"))
    estimate.labor_total = sum((line.labor_cost for line in estimate.lines), Decimal("0"))
    estimate.grand_total = estimate.material_total + estimate.labor_total
    session.add(estimate)
    session.commit()
    return estimate


def update_rates(session: Session, estimate_id: uuid.UUID, rates: list[dict]) -> Estimate:
    estimate = session.get(Estimate, estimate_id)
    if not estimate:
        raise EstimateError("The estimate was not found.", 404)
    for item in rates:
        line = next((line for line in estimate.lines if str(line.id) == str(item["line_id"])), None)
        if not line:
            continue
        material_rate = Decimal(str(item.get("material_rate", line.rate_snapshot["material_rate"])))
        labor_rate = Decimal(str(item.get("labor_rate", line.rate_snapshot["labor_rate"])))
        quantity = line.quantity
        line.material_cost, line.labor_cost = calculate_cost(quantity, material_rate, labor_rate, quantity)
        line.rate_snapshot = {**line.rate_snapshot, "material_rate": str(material_rate), "labor_rate": str(labor_rate)}
    estimate.material_total = sum((line.material_cost for line in estimate.lines), Decimal("0"))
    estimate.labor_total = sum((line.labor_cost for line in estimate.lines), Decimal("0"))
    estimate.grand_total = estimate.material_total + estimate.labor_total
    session.commit()
    return estimate