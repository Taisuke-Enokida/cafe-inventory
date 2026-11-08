from decimal import Decimal

import pytest

from app.services.inventory import (
    InsufficientStockError,
    ValidationError,
    get_stock,
    record_movement,
)


def test_receipt_usage_and_waste_update_ledger_and_stock(app, admin, product):
    with app.app_context():
        receipt = record_movement(product, admin, "receipt", Decimal("10"))
        usage = record_movement(product, admin, "usage", Decimal("2.250"))
        waste = record_movement(product, admin, "waste", Decimal("0.500"))

        assert receipt.quantity_delta == Decimal("10.000")
        assert usage.quantity_delta == Decimal("-2.250")
        assert waste.quantity_delta == Decimal("-0.500")
        assert get_stock(product) == Decimal("7.250")


def test_stock_shortage_is_rejected_without_recording_movement(app, admin, product):
    with app.app_context():
        record_movement(product, admin, "receipt", Decimal("3"))

        with pytest.raises(InsufficientStockError):
            record_movement(product, admin, "usage", Decimal("3.001"))

        assert get_stock(product) == Decimal("3.000")


@pytest.mark.parametrize(
    "quantity",
    [Decimal("0"), Decimal("-1"), Decimal("1.0001"), Decimal("1000000000")],
)
def test_invalid_or_overprecision_quantity_is_rejected(app, admin, product, quantity):
    with app.app_context(), pytest.raises(ValidationError):
        record_movement(product, admin, "receipt", quantity)


def test_correction_is_append_only_and_preserves_original(app, admin, product):
    from app.extensions import db
    from app.models import InventoryMovement

    with app.app_context():
        original = record_movement(product, admin, "receipt", Decimal("5"))
        correction = record_movement(
            product,
            admin,
            "correction",
            Decimal("-1"),
            reason="数量の入力誤り",
            correction_of_id=original.id,
        )

        assert correction.correction_of_id == original.id
        assert correction.reason == "数量の入力誤り"
        assert get_stock(product) == Decimal("4.000")
        assert db.session.get(InventoryMovement, original.id) is not None


def test_correction_requires_reason_and_reference(app, admin, product):
    with app.app_context(), pytest.raises(ValidationError):
        record_movement(
            product,
            admin,
            "correction",
            Decimal("-1"),
            reason=" ",
            correction_of_id=None,
        )
