from __future__ import annotations

import io

from PIL import Image, ImageOps

from app.services.image_validator import DecodedImage


def create_canonical_image(decoded: DecodedImage) -> bytes:
    normalized = ImageOps.exif_transpose(decoded.image).convert("RGB")
    output = io.BytesIO()
    normalized.save(output, format="PNG", optimize=True)
    return output.getvalue()