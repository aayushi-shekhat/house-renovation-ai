from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from app.core.enums import RegionType


@dataclass(frozen=True)
class RegionProposal:
    region_type: RegionType
    confidence: float
    polygon: list[list[float]] | None
    mask_key: str | None
    metadata: dict


@dataclass(frozen=True)
class SegmentationPrompt:
    points: Sequence[tuple[float, float]] = ()
    labels: Sequence[int] = ()
    box: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class EditedImage:
    storage_key: str
    provider: str
    metadata: dict


class RegionProposalProvider(Protocol):
    name: str

    def propose(self, image_key: str, region_types: Sequence[RegionType]) -> list[RegionProposal]:
        ...


class InteractiveSegmenter(Protocol):
    name: str

    def refine(self, image_key: str, prompt: SegmentationPrompt) -> str:
        """Return a storage key for a canonical binary mask."""
        ...


class ImageEditor(Protocol):
    name: str

    def edit(self, image_key: str, mask_keys: Sequence[str], prompt: str) -> EditedImage:
        ...
