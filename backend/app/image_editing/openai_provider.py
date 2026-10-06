from __future__ import annotations

from collections.abc import Sequence

from app.core.errors import AppError
from app.providers.contracts import EditedImage, ImageEditor


class ImageEditorUnavailable(AppError):
    def __init__(self, message: str = "AI visualization unavailable") -> None:
        super().__init__("AI_RENDERING_UNAVAILABLE", message, 200)


class OpenAIImageEditor(ImageEditor):
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def edit(self, image_key: str, mask_keys: Sequence[str], prompt: str) -> EditedImage:
        # The provider contract is ready for a storage-aware OpenAI adapter. The
        # prototype deliberately reports provider failure rather than inventing
        # an AI result when the external API is unavailable.
        raise ImageEditorUnavailable()