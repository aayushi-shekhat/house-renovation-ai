from decimal import Decimal

from app.engines.calculations import calculate_cost, calculate_quantity, polygon_area, polygon_length


def test_polygon_geometry_is_deterministic() -> None:
    polygon: list[list[float]] = [[0, 0], [10, 0], [10, 10], [0, 10]]

    assert polygon_area(polygon) == 100
    assert polygon_length(polygon) == 40


def test_quantity_applies_wastage_and_pack_rounding() -> None:
    result = calculate_quantity(
        Decimal("100"), "paint", Decimal("10"), Decimal("5"), Decimal("10"), coats=Decimal("2")
    )

    assert result.base_quantity == Decimal("20")
    assert result.allowed_quantity == Decimal("25.00")
    assert result.purchasable_quantity == Decimal("25")
    assert result.packs == 5


def test_cost_uses_decimal_rounding() -> None:
    material, labor = calculate_cost(Decimal("12.5"), Decimal("8.40"), Decimal("3.25"), Decimal("100"))

    assert material == Decimal("105.00")
    assert labor == Decimal("325.00")