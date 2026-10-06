from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import RegionType, ReviewStatus, RevisionStatus
from app.core.errors import AppError
from app.domain.models import DesignRevision, Image, Region, RegionSet
from app.engines.calculations import polygon_area
from app.providers.contracts import RegionProposalProvider


class RegionError(AppError):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__("REGION_WORKFLOW_ERROR", message, status_code)


def get_region_set(session: Session, image_id: uuid.UUID) -> RegionSet | None:
    return session.scalar(select(RegionSet).where(RegionSet.image_id == image_id).order_by(RegionSet.revision_number.desc()))


def analyze_image(
    session: Session,
    image_id: uuid.UUID,
    provider: RegionProposalProvider | None,
) -> RegionSet:
    image = session.get(Image, image_id)
    if image is None:
        raise RegionError("The requested image was not found.", 404)
    previous = get_region_set(session, image_id)
    revision = (previous.revision_number + 1) if previous else 1
    region_set = RegionSet(image_id=image_id, revision_number=revision, status=RevisionStatus.DRAFT,
                           provider_metadata={"provider": getattr(provider, "name", "manual"), "fallback": provider is None})
    if provider:
        try:
            proposals = provider.propose("", list(RegionType))
        except Exception:
            proposals = []
            region_set.provider_metadata = {"provider": getattr(provider, "name", "unknown"), "fallback": True}
        for proposal in proposals:
            region_set.regions.append(Region(
                region_type=proposal.region_type, confidence=Decimal(str(proposal.confidence)),
                review_status=ReviewStatus.PROPOSED, polygon=proposal.polygon,
                area_pixels=polygon_area(proposal.polygon),
                geometry_metadata={"bounds": _bounds(proposal.polygon), "provenance": "model", "metadata": proposal.metadata},
            ))
    session.add(region_set)
    session.commit()
    return region_set


def _bounds(polygon: list[list[float]] | None) -> dict[str, float] | None:
    if not polygon:
        return None
    xs, ys = zip(*polygon)
    return {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}


def add_region(session: Session, region_set_id: uuid.UUID, region_type: RegionType, polygon: list[list[float]], provenance: str = "manual") -> Region:
    region_set = session.get(RegionSet, region_set_id)
    if not region_set or region_set.status == RevisionStatus.APPROVED:
        raise RegionError("Only a draft region revision can be edited.")
    if len(polygon) < 3:
        raise RegionError("A region polygon needs at least three points.")
    region = Region(region_set_id=region_set_id, region_type=region_type, polygon=polygon,
                    review_status=ReviewStatus.PROPOSED, area_pixels=polygon_area(polygon),
                    geometry_metadata={"bounds": _bounds(polygon), "provenance": provenance})
    session.add(region)
    session.commit()
    return region


def update_region(session: Session, region_id: uuid.UUID, region_type: RegionType | None, polygon: list[list[float]] | None) -> Region:
    region = session.get(Region, region_id)
    if not region or not region.region_set or region.region_set.status == RevisionStatus.APPROVED:
        raise RegionError("Only a draft region revision can be edited.", 404 if not region else 422)
    if region_type:
        region.region_type = region_type
    if polygon is not None:
        if len(polygon) < 3:
            raise RegionError("A region polygon needs at least three points.")
        region.polygon = polygon
        region.area_pixels = polygon_area(polygon)
        region.geometry_metadata = {**(region.geometry_metadata or {}), "bounds": _bounds(polygon), "provenance": "corrected"}
    region.review_status = ReviewStatus.REVIEWED
    session.commit()
    return region


def approve_region_set(session: Session, region_set_id: uuid.UUID) -> tuple[RegionSet, DesignRevision]:
    region_set = session.get(RegionSet, region_set_id)
    if not region_set:
        raise RegionError("The region revision was not found.", 404)
    region_set.status = RevisionStatus.APPROVED
    for region in region_set.regions:
        if region.review_status != ReviewStatus.REJECTED:
            region.review_status = ReviewStatus.APPROVED
    design = DesignRevision(project_id=region_set.image.project_id, region_set_id=region_set.id,
                            revision_number=region_set.revision_number, status=RevisionStatus.DRAFT)
    session.add(design)
    session.commit()
    return region_set, design