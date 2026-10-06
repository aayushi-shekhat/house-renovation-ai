from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.enums import RegionType
from app.cv.yoloe_provider import YoloERegionProposalProvider
from app.domain.models import Asset, DesignRevision, Estimate, Image, MaterialAssignment, MaterialVersion, Region, RegionSet
from app.schemas.workflow import AssignmentCreate, EstimateCreate, MeasurementCreate, RateUpdate, RegionCreate, RegionUpdate
from app.services.estimate_service import create_estimate, create_measurements, update_rates
from app.services.material_service import assign_material, list_materials
from app.services.render_service import render_design
from app.services.report_service import create_report
from app.services.region_service import add_region, analyze_image, approve_region_set, get_region_set, update_region
from app.storage.local import LocalFilesystemStorage

router = APIRouter(tags=["workflow"])


def enum_value(value) -> str:
    return getattr(value, "value", value)


def error_response(error: AppError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"error": {"code": error.code, "message": error.message, "details": error.details}})


def region_json(region) -> dict:
    return {"id": str(region.id), "region_set_id": str(region.region_set_id), "region_type": enum_value(region.region_type),
            "confidence": str(region.confidence) if region.confidence is not None else None,
            "review_status": enum_value(region.review_status), "mask_asset_id": str(region.mask_asset_id) if region.mask_asset_id else None,
            "polygon": region.polygon, "area_pixels": region.area_pixels, "geometry_metadata": region.geometry_metadata or {}}


def region_set_json(region_set) -> dict:
    return {"id": str(region_set.id), "image_id": str(region_set.image_id), "revision_number": region_set.revision_number,
            "status": enum_value(region_set.status), "provider_metadata": region_set.provider_metadata or {},
            "regions": [region_json(region) for region in region_set.regions]}


@router.post("/images/{image_id}/analysis")
def run_analysis(image_id: uuid.UUID, session: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        provider = YoloERegionProposalProvider(settings.yoloe_model_path)
        region_set = analyze_image(session, image_id, provider if provider.available else None)
        return region_set_json(region_set)
    except AppError as exc:
        return error_response(exc)


@router.get("/images/{image_id}/regions")
def read_regions(image_id: uuid.UUID, session: Session = Depends(get_db)):
    region_set = get_region_set(session, image_id)
    if not region_set:
        return JSONResponse(status_code=404, content={"error": {"code": "REGION_SET_NOT_FOUND", "message": "Run analysis before reviewing regions."}})
    return region_set_json(region_set)


@router.post("/region-sets/{region_set_id}/regions")
def create_region(region_set_id: uuid.UUID, payload: RegionCreate, session: Session = Depends(get_db)):
    try:
        return region_json(add_region(session, region_set_id, payload.region_type, payload.polygon))
    except AppError as exc:
        return error_response(exc)


@router.patch("/regions/{region_id}")
def edit_region(region_id: uuid.UUID, payload: RegionUpdate, session: Session = Depends(get_db)):
    try:
        return region_json(update_region(session, region_id, payload.region_type, payload.polygon))
    except AppError as exc:
        return error_response(exc)


@router.delete("/regions/{region_id}")
def delete_region(region_id: uuid.UUID, session: Session = Depends(get_db)):
    region = session.get(Region, region_id)
    if not region:
        return JSONResponse(status_code=404, content={"error": {"code": "REGION_NOT_FOUND", "message": "The region was not found."}})
    if region.region_set.status.value == "approved":
        return JSONResponse(status_code=422, content={"error": {"code": "REGION_REVISION_APPROVED", "message": "Approved regions cannot be deleted."}})
    session.delete(region)
    session.commit()
    return {"deleted": True}


@router.post("/region-sets/{region_set_id}/approve")
def approve_regions(region_set_id: uuid.UUID, session: Session = Depends(get_db)):
    try:
        region_set, design = approve_region_set(session, region_set_id)
        return {"region_set": region_set_json(region_set), "design_revision_id": str(design.id)}
    except AppError as exc:
        return error_response(exc)


@router.get("/materials")
def materials(session: Session = Depends(get_db)):
    return [{"id": str(material.id), "name": material.name, "category": material.category, "description": material.description,
             "versions": [{"id": str(version.id), "unit": version.unit, "coverage_per_unit": str(version.coverage_per_unit) if version.coverage_per_unit else None,
                           "pack_size": str(version.pack_size) if version.pack_size else None, "material_rate": str(version.material_rate),
                           "labor_rate": str(version.labor_rate), "wastage_percentage": str(version.wastage_percentage),
                           "specification": version.specification} for version in material.versions]} for material in list_materials(session)]


@router.post("/design-revisions/{design_revision_id}/assignments")
def create_assignment(design_revision_id: uuid.UUID, payload: AssignmentCreate, session: Session = Depends(get_db)):
    try:
        assignment = assign_material(session, design_revision_id, payload.region_id, payload.material_version_id, payload.application_metadata)
        return {"id": str(assignment.id), "region_id": str(assignment.region_id), "material_version_id": str(assignment.material_version_id)}
    except AppError as exc:
        return error_response(exc)


@router.get("/design-revisions/{design_revision_id}/assignments")
def read_assignments(design_revision_id: uuid.UUID, session: Session = Depends(get_db)):
    assignments = list(session.scalars(select(MaterialAssignment).where(MaterialAssignment.design_revision_id == design_revision_id)))
    return [{"id": str(item.id), "region_id": str(item.region_id), "material_version_id": str(item.material_version_id), "application_metadata": item.application_metadata or {}} for item in assignments]


@router.post("/design-revisions/{design_revision_id}/measurements")
def create_measurement_revision(design_revision_id: uuid.UUID, payload: MeasurementCreate, session: Session = Depends(get_db)):
    try:
        revision = create_measurements(session, design_revision_id, [item.model_dump(mode="json") for item in payload.entries], payload.reference_pixels, payload.reference_feet)
        return {"id": str(revision.id), "method": revision.method, "assumptions": revision.assumptions,
                "measurements": [{"region_id": str(item.region_id), "quantity": str(item.quantity), "unit": item.unit, "metadata": item.measurement_metadata} for item in revision.measurements]}
    except AppError as exc:
        return error_response(exc)


@router.post("/design-revisions/{design_revision_id}/estimates")
def create_estimate_endpoint(design_revision_id: uuid.UUID, payload: EstimateCreate, session: Session = Depends(get_db)):
    try:
        estimate = create_estimate(session, design_revision_id, payload.measurement_revision_id, payload.currency)
        return estimate_json(estimate)
    except AppError as exc:
        return error_response(exc)


@router.patch("/estimates/{estimate_id}/rates")
def edit_rates(estimate_id: uuid.UUID, payload: list[RateUpdate], session: Session = Depends(get_db)):
    try:
        return estimate_json(update_rates(session, estimate_id, [item.model_dump(mode="json") for item in payload]))
    except AppError as exc:
        return error_response(exc)


def estimate_json(estimate: Estimate) -> dict:
    return {"id": str(estimate.id), "currency": estimate.currency, "material_total": str(estimate.material_total), "labor_total": str(estimate.labor_total), "grand_total": str(estimate.grand_total), "assumptions": estimate.assumptions,
            "lines": [{"id": str(line.id), "region_id": str(line.region_id) if line.region_id else None, "category": line.category, "description": line.description, "quantity": str(line.quantity), "unit": line.unit, "material_cost": str(line.material_cost), "labor_cost": str(line.labor_cost), "rate_snapshot": line.rate_snapshot} for line in estimate.lines]}


@router.post("/design-revisions/{design_revision_id}/render")
def render_endpoint(design_revision_id: uuid.UUID, session: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        render = render_design(session, LocalFilesystemStorage(Path(settings.storage_root)), settings, design_revision_id)
        return {"id": str(render.id), "status": render.status, "provider": render.provider, "provider_metadata": render.provider_metadata,
                "output_asset_id": str(render.output_asset_id) if render.output_asset_id else None}
    except AppError as exc:
        return error_response(exc)
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "RENDER_NOT_FOUND", "message": str(exc)}})


@router.post("/estimates/{estimate_id}/report")
def report_endpoint(estimate_id: uuid.UUID, session: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        report = create_report(session, LocalFilesystemStorage(Path(settings.storage_root)), estimate_id)
        return {"id": str(report.id), "status": report.status, "report_asset_id": str(report.report_asset_id)}
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "REPORT_NOT_FOUND", "message": str(exc)}})


@router.get("/assets/{asset_id}")
def asset_content(asset_id: uuid.UUID, session: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    asset = session.get(Asset, asset_id)
    if not asset:
        return JSONResponse(status_code=404, content={"error": {"code": "ASSET_NOT_FOUND", "message": "The asset was not found."}})
    storage = LocalFilesystemStorage(Path(settings.storage_root))
    return StreamingResponse(storage.open(asset.storage_key), media_type=asset.media_type)