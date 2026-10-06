from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from app.core.config import Settings

ImageFile.LOAD_TRUNCATED_IMAGES = False

SUPPORTED_MEDIA_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
ValidationStatus = Literal["accepted", "accepted_with_warnings", "rejected"]


class UnsupportedImageError(ValueError):
    pass


class ImageDimensionError(ValueError):
    pass


@dataclass(frozen=True)
class ValidationReason:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class DecodedImage:
    image: Image.Image
    media_type: str
    width: int
    height: int


@dataclass(frozen=True)
class ImageValidationResult:
    status: ValidationStatus
    reasons: list[ValidationReason]
    decoded: DecodedImage | None


def decode_image(content: bytes, settings: Settings) -> DecodedImage:
    try:
        with Image.open(io.BytesIO(content)) as candidate:
            media_type = SUPPORTED_MEDIA_TYPES.get(candidate.format or "")
            if media_type is None:
                raise UnsupportedImageError("unsupported format")
            if getattr(candidate, "n_frames", 1) != 1:
                raise UnsupportedImageError("animated image")
            candidate.verify()

        with Image.open(io.BytesIO(content)) as image:
            image.load()
            normalized = ImageOps.exif_transpose(image)
            width, height = normalized.size
            if width > settings.max_image_width or height > settings.max_image_height:
                raise ImageDimensionError("dimensions exceed the configured maximum")
            return DecodedImage(normalized.copy(), media_type, width, height)
    except (UnsupportedImageError, ImageDimensionError):
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("image is not a supported, readable image") from exc


def validate_image(content: bytes, settings: Settings) -> ImageValidationResult:
    if len(content) > settings.max_upload_bytes:
        return ImageValidationResult(
            "rejected",
            [ValidationReason("FILE_TOO_LARGE", "Image exceeds the maximum allowed file size.", "error")],
            None,
        )

    try:
        decoded = decode_image(content, settings)
    except ValueError as exc:
        message = str(exc)
        if message == "unsupported format":
            code = "UNSUPPORTED_FORMAT"
        elif message == "dimensions exceed the configured maximum":
            code = "IMAGE_TOO_LARGE_DIMENSIONS"
        else:
            code = "CORRUPTED_IMAGE"
        return ImageValidationResult("rejected", [ValidationReason(code, "The image could not be read as a supported image.", "error")], None)

    reasons: list[ValidationReason] = []
    width, height = decoded.width, decoded.height
    if width < settings.min_image_width or height < settings.min_image_height:
        reasons.append(ValidationReason("IMAGE_TOO_SMALL", "Image dimensions are below the minimum required size.", "error"))
    if max(width / height, height / width) > settings.max_image_aspect_ratio:
        reasons.append(ValidationReason("EXTREME_ASPECT_RATIO", "Image has an unusually extreme aspect ratio.", "warning"))

    grayscale = decoded.image.convert("L")
    histogram = grayscale.histogram()
    pixel_count = width * height
    dark_ratio = sum(histogram[:12]) / pixel_count
    bright_ratio = sum(histogram[244:]) / pixel_count
    if dark_ratio > 0.75:
        reasons.append(ValidationReason("SEVERE_UNDEREXPOSURE", "Image appears very dark and may need retaking.", "warning"))
    if bright_ratio > 0.75:
        reasons.append(ValidationReason("SEVERE_OVEREXPOSURE", "Image appears very bright and may need retaking.", "warning"))

    pixels = list(grayscale.resize((min(width, 512), min(height, 512))).getdata())
    if pixels:
        mean = sum(pixels) / len(pixels)
        variance = sum((pixel - mean) ** 2 for pixel in pixels) / len(pixels)
        if variance < settings.blur_variance_threshold:
            reasons.append(ValidationReason("LOW_SHARPNESS", "Image may be slightly blurry.", "warning"))

    status: ValidationStatus = "rejected" if any(reason.severity == "error" for reason in reasons) else (
        "accepted_with_warnings" if reasons else "accepted"
    )
    return ImageValidationResult(status, reasons, decoded)