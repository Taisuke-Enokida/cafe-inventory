from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from app.extensions import db
from app.models import InventoryMovement, Product

ZERO = Decimal("0.000")
QUANTITY_STEP = Decimal("0.001")
MAX_QUANTITY = Decimal("999999999.999")
MOVEMENT_KINDS = {"receipt", "usage", "waste", "correction"}


class InventoryError(Exception):
    """Base error for invalid inventory operations."""


class InsufficientStockError(InventoryError):
    """Raised when an operation would make stock negative."""


class ValidationError(InventoryError):
    """Raised when inventory operation data is invalid."""


def _as_decimal(value: Decimal | str | int) -> Decimal:
    if isinstance(value, float):
        raise ValidationError("数量は小数3桁以内で入力してください。")
    try:
        quantity = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError("数量を正しく入力してください。") from None
    if (
        not quantity.is_finite()
        or abs(quantity) > MAX_QUANTITY
        or quantity.quantize(QUANTITY_STEP) != quantity
    ):
        raise ValidationError("数量は小数3桁以内で入力してください。")
    return quantity


def get_stock(product_id: int) -> Decimal:
    total = db.session.scalar(
        select(func.coalesce(func.sum(InventoryMovement.quantity_delta), ZERO)).where(
            InventoryMovement.product_id == product_id
        )
    )
    return Decimal(total or ZERO)


def record_movement(
    product_id: int,
    actor_id: int,
    kind: str,
    quantity: Decimal | str | int,
    *,
    reason: str | None = None,
    correction_of_id: int | None = None,
) -> InventoryMovement:
    if kind not in MOVEMENT_KINDS:
        raise ValidationError("入出庫の種別が正しくありません。")

    amount = _as_decimal(quantity)
    if amount == ZERO:
        raise ValidationError("数量は0より大きい値を入力してください。")

    if kind != "correction" and (amount <= ZERO or correction_of_id is not None):
        raise ValidationError("数量または履歴の指定が正しくありません。")
    if kind == "correction" and (correction_of_id is None or not reason or not reason.strip()):
        raise ValidationError("訂正には元履歴と理由が必要です。")

    delta = amount if kind == "receipt" else -amount if kind in {"usage", "waste"} else amount

    try:
        product = db.session.scalar(
            select(Product).where(Product.id == product_id).with_for_update()
        )
        if product is None or not product.is_active:
            raise ValidationError("有効な商品が見つかりません。")

        if kind == "correction":
            original = db.session.get(InventoryMovement, correction_of_id)
            if (
                original is None
                or original.product_id != product_id
                or original.kind == "correction"
            ):
                raise ValidationError("訂正対象の履歴が正しくありません。")

        current_stock = get_stock(product_id)
        if current_stock + delta < ZERO:
            raise InsufficientStockError("在庫が不足しています。")

        movement = InventoryMovement(
            product_id=product_id,
            actor_id=actor_id,
            kind=kind,
            quantity_delta=delta,
            reason=reason.strip() if reason else None,
            correction_of_id=correction_of_id,
        )
        db.session.add(movement)
        db.session.commit()
        return movement
    except Exception:
        db.session.rollback()
        raise
