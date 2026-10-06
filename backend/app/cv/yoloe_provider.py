from __future__ import annotations

from collections.abc import Sequence

from app.core.enums import RegionType
from app.providers.contracts import RegionProposal


class YoloERegionProposalProvider:
    """Optional YOLOE adapter. It never invents proposals when the model is unavailable."""

    name = "yoloe"

    def __init__(self, model_path: str | None) -> None:
        self._model = None
        if model_path:
            try:
                from ultralytics import YOLO  # type: ignore[import-not-found]

                self._model = YOLO(model_path)
            except Exception:
                self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    def propose(self, image_key: str, region_types: Sequence[RegionType]) -> list[RegionProposal]:
        if self._model is None:
            return []
        # Model-specific open-vocabulary setup is intentionally isolated here.
        # A model that does not expose usable masks/classes returns no proposals.
        try:
            results = self._model.predict(image_key, verbose=False)
        except Exception:
            return []
        proposals: list[RegionProposal] = []
        labels = {region.value for region in region_types}
        for result in results:
            names = getattr(result, "names", {})
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for index, cls in enumerate(getattr(boxes, "cls", [])):
                label = names.get(int(cls), "") if isinstance(names, dict) else ""
                if label not in labels:
                    continue
                region_type = RegionType(label)
                xyxy = getattr(boxes, "xyxy", [])[index].tolist()
                x1, y1, x2, y2 = xyxy
                proposals.append(RegionProposal(
                    region_type, float(getattr(boxes, "conf", [0])[index]),
                    [[x1, y1], [x2, y1], [x2, y2], [x1, y2]], None,
                    {"provider": self.name, "model_label": label},
                ))
        return proposals