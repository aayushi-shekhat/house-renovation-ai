from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.utils import ImageReader  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Asset, DesignRevision, Estimate, Image as HouseImage, MaterialAssignment, MaterialVersion, RegionSet, Report
from app.storage.protocol import StorageProvider


def create_report(session: Session, storage: StorageProvider, estimate_id: uuid.UUID) -> Report:
    estimate = session.get(Estimate, estimate_id)
    if not estimate:
        raise ValueError("Estimate not found")
    design = session.get(DesignRevision, estimate.design_revision_id)
    region_set = session.get(RegionSet, design.region_set_id) if design else None
    house_image = session.get(HouseImage, region_set.image_id) if region_set else None
    if not design or not house_image:
        raise ValueError("Design source image not found")
    original = session.get(Asset, house_image.original_asset_id)
    if not original:
        raise ValueError("Original image asset not found")
    render = next(iter(design.renders), None)
    rendered = session.get(Asset, render.output_asset_id) if render and render.output_asset_id else None
    output = io.BytesIO()
    pdf = Canvas(output, pagesize=letter)
    width, height = letter
    pdf.setTitle("Exterior Renovation Estimate")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, height - 54, "Exterior Renovation Estimate")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(48, height - 72, f"Generated {datetime.now(timezone.utc).date().isoformat()} | Advisory / non-binding")
    y = height - 105
    y = _draw_image(pdf, storage, original, 48, y, "Original image")
    if rendered:
        y = _draw_image(pdf, storage, rendered, 300, height - 105, "Renovation preview")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(48, y - 10, "Estimate summary")
    pdf.setFont("Helvetica", 10)
    y -= 28
    for label, value in (("Material total", estimate.material_total), ("Labor total", estimate.labor_total), ("Grand total", estimate.grand_total)):
        pdf.drawString(60, y, f"{label}: {estimate.currency} {value}")
        y -= 16
    y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(48, y, "Line items")
    y -= 18
    pdf.setFont("Helvetica", 8)
    for line in estimate.lines:
        pdf.drawString(60, y, f"{line.description} | {line.quantity} {line.unit} | material {line.material_cost} | labor {line.labor_cost}")
        y -= 13
        if y < 60:
            pdf.showPage()
            y = height - 50
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(48, 40, "Measurements are approximate and depend on supplied reference dimensions or manual areas.")
    pdf.save()
    output.seek(0)
    key = f"projects/{house_image.project_id}/reports/{estimate.id}.pdf"
    stored = storage.put(output, key, "application/pdf")
    asset = session.query(Asset).filter(Asset.storage_key == stored.storage_key).one_or_none()
    if asset is None:
        asset = Asset(storage_key=stored.storage_key, media_type=stored.media_type, byte_size=stored.byte_size, metadata_json={"role": "report"})
        session.add(asset)
    else:
        asset.media_type = stored.media_type
        asset.byte_size = stored.byte_size
        asset.metadata_json = {"role": "report"}
    session.flush()
    report = Report(project_id=house_image.project_id, estimate_id=estimate.id, original_asset_id=original.id,
                    redesigned_asset_id=rendered.id if rendered else None, report_asset_id=asset.id, status="ready")
    session.add(report)
    session.commit()
    return report


def _draw_image(pdf: Canvas, storage: StorageProvider, asset: Asset, x: int, y: int, label: str) -> int:
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(x, y, label)
    with storage.open(asset.storage_key) as source:
        image = ImageReader(source)
        pdf.drawImage(image, x, y - 145, width=220, height=130, preserveAspectRatio=True, anchor="sw")
    return y - 170