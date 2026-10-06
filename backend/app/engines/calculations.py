from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from math import hypot


MONEY = Decimal("0.01")
QTY = Decimal("0.01")


def polygon_area(polygon: list[list[float]] | None) -> int:
    if not polygon or len(polygon) < 3:
        return 0
    area = abs(sum(
        polygon[index][0] * polygon[(index + 1) % len(polygon)][1]
        - polygon[(index + 1) % len(polygon)][0] * polygon[index][1]
        for index in range(len(polygon))
    )) / 2
    return max(0, round(area))


def polygon_length(polygon: list[list[float]] | None) -> float:
    if not polygon or len(polygon) < 2:
        return 0
    return sum(hypot(
        polygon[(index + 1) % len(polygon)][0] - polygon[index][0],
        polygon[(index + 1) % len(polygon)][1] - polygon[index][1],
    ) for index in range(len(polygon)))


def round_decimal(value: Decimal, places: Decimal = QTY) -> Decimal:
    return value.quantize(places, rounding=ROUND_HALF_UP)


def purchasable_quantity(base_quantity: Decimal, wastage: Decimal, pack_size: Decimal | None) -> tuple[Decimal, int | None]:
    allowed = round_decimal(base_quantity * (Decimal("1") + wastage / Decimal("100")))
    if not pack_size or pack_size <= 0:
        return allowed, None
    packs = int((allowed / pack_size).quantize(Decimal("1"), rounding=ROUND_CEILING))
    return round_decimal(pack_size * packs), packs


@dataclass(frozen=True)
class QuantityResult:
    base_quantity: Decimal
    allowed_quantity: Decimal
    purchasable_quantity: Decimal
    packs: int | None
    unit: str


def calculate_quantity(
    area_sqft: Decimal,
    material_category: str,
    coverage: Decimal | None,
    pack_size: Decimal | None,
    wastage: Decimal,
    coats: Decimal = Decimal("1"),
    length: Decimal | None = None,
) -> QuantityResult:
    category = material_category.lower()
    if category in {"paint", "textured paint"}:
        base = area_sqft * coats / (coverage or Decimal("1"))
        unit = "gallon"
    elif category in {"railing", "roof edge"} or length is not None:
        base = length or area_sqft
        unit = "linear_ft"
    elif category in {"tiles", "tile"}:
        base = area_sqft / (coverage or Decimal("1"))
        unit = "box"
    else:
        base = area_sqft
        unit = "sqft"
    allowed, packs = purchasable_quantity(base, wastage, pack_size)
    return QuantityResult(base, allowed, allowed, packs, unit)


def calculate_cost(quantity: Decimal, material_rate: Decimal, labor_rate: Decimal, labor_basis: Decimal = Decimal("1")) -> tuple[Decimal, Decimal]:
    return (
        (quantity * material_rate).quantize(MONEY, rounding=ROUND_HALF_UP),
        (labor_basis * labor_rate).quantize(MONEY, rounding=ROUND_HALF_UP),
    )