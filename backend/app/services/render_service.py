from __future__ import annotations

import io
import uuid
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.models import Asset, DesignRevision, Image as HouseImage, MaterialAssignment, MaterialVersion, Region, RegionSet, Render
from app.image_editing.openai_provider import ImageEditorUnavailable, OpenAIImageEditor
from app.storage.protocol import StorageProvider


def render_design(session: Session, storage: StorageProvider, settings: Settings, design_revision_id: uuid.UUID) -> Render:
    design = session.get(DesignRevision, design_revision_id)
    if not design:
        raise ValueError("Design revision not found")
    region_set = session.get(RegionSet, design.region_set_id)
    house_image = session.get(HouseImage, region_set.image_id) if region_set else None
    source_asset = session.get(Asset, house_image.processing_asset_id or house_image.original_asset_id) if house_image else None
    if not house_image or not source_asset:
        raise ValueError("Source image not found")
    assignments = session.query(MaterialAssignment).filter(MaterialAssignment.design_revision_id == design.id).all()
    editor_status = "ai_unavailable"
    provider_metadata = {"message": "AI visualization unavailable; deterministic material preview used.", "fallback": True}
    if settings.openai_api_key:
        try:
            OpenAIImageEditor(settings.openai_api_key, settings.openai_image_model).edit(source_asset.storage_key, [], _prompt())
        except ImageEditorUnavailable:
            pass
        except Exception:
            pass

    with storage.open(source_asset.storage_key) as source:
        image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    for assignment in assignments:
        region = session.get(Region, assignment.region_id)
        version = session.get(MaterialVersion, assignment.material_version_id)
        if not region or not region.polygon or not version:
            continue
        swatch = (version.specification or {}).get("swatch", "#b0b0b0")
        color = tuple(int(swatch[index:index + 2], 16) for index in (1, 3, 5)) + (105,)
        draw.polygon([(point[0], point[1]) for point in region.polygon], fill=color, outline=color[:3] + (220,))
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    key = f"projects/{house_image.project_id}/renders/{design.id}/preview.png"
    stored = storage.put(output, key, "image/png")
    asset = session.query(Asset).filter(Asset.storage_key == stored.storage_key).one_or_none()
    if asset is None:
        asset = Asset(storage_key=stored.storage_key, media_type=stored.media_type, byte_size=stored.byte_size,
                      width=image.width, height=image.height, metadata_json={"role": "render_preview", "ai_status": editor_status})
        session.add(asset)
    else:
        asset.media_type = stored.media_type
        asset.byte_size = stored.byte_size
        asset.width = image.width
        asset.height = image.height
        asset.metadata_json = {"role": "render_preview", "ai_status": editor_status}
    session.flush()
    render = Render(design_revision_id=design.id, source_image_id=house_image.id, output_asset_id=asset.id,
                    provider="deterministic_fallback", status=editor_status, provider_metadata=provider_metadata)
    session.add(render)
    session.commit()
    return render


def _prompt() -> str:
    return ("Preserve building structure, camera viewpoint, perspective, windows, doors, balconies, pillars, "
            "roofline, and existing architectural geometry. Only modify approved material regions.")