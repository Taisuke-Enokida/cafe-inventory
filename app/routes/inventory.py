from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select

from app.extensions import db
from app.models import InventoryMovement, Product
from app.services.inventory import (
    InventoryError,
    get_stock,
    record_movement,
)

bp = Blueprint("inventory", __name__)


@bp.get("/")
def root():
    return redirect(url_for("inventory.index"))


@bp.get("/health")
def health():
    from flask import current_app, jsonify
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error("Database health check failed")
        return jsonify(status="unavailable"), 503
    return jsonify(status="ok"), 200


@bp.get("/inventory")
@login_required
def index():
    search = request.args.get("q", "").strip()
    query = select(Product).where(Product.is_active.is_(True))
    if search:
        query = query.where(
            or_(Product.name.ilike(f"%{search}%"), Product.category.ilike(f"%{search}%"))
        )
    products = db.session.scalars(query.order_by(Product.category, Product.name)).all()
    rows = [{"product": product, "stock": get_stock(product.id)} for product in products]
    return render_template("inventory.html", rows=rows, search=search)


@bp.get("/history")
@login_required
def history():
    movements = db.session.scalars(
        select(InventoryMovement)
        .join(InventoryMovement.product)
        .order_by(InventoryMovement.occurred_at.desc(), InventoryMovement.id.desc())
        .limit(200)
    ).all()
    return render_template("history.html", movements=movements)


@bp.post("/stock/receipt")
@login_required
def receipt():
    return _record_from_form("receipt")


@bp.post("/stock/issue")
@login_required
def issue():
    kind = request.form.get("kind", "")
    if kind not in {"usage", "waste"}:
        abort(400, description="使用または廃棄を選択してください。")
    return _record_from_form(kind)


@bp.post("/history/<int:movement_id>/correct")
@login_required
def correct(movement_id: int):
    try:
        quantity = Decimal(request.form.get("quantity_delta", ""))
        record_movement(
            int(request.form.get("product_id", "")),
            current_user.id,
            "correction",
            quantity,
            reason=request.form.get("reason"),
            correction_of_id=movement_id,
        )
    except (InvalidOperation, ValueError):
        flash("訂正数量を正しく入力してください。", "error")
    except InventoryError as error:
        flash(str(error), "error")
    else:
        flash("訂正履歴を記録しました。", "success")
    return redirect(url_for("inventory.history"))


def _record_from_form(kind: str):
    try:
        quantity = Decimal(request.form.get("quantity", ""))
        record_movement(
            int(request.form.get("product_id", "")),
            current_user.id,
            kind,
            quantity,
            reason=request.form.get("reason"),
        )
    except (InvalidOperation, ValueError):
        flash("商品と数量を正しく入力してください。", "error")
    except InventoryError as error:
        flash(str(error), "error")
    else:
        flash("在庫履歴を記録しました。", "success")
    return redirect(url_for("inventory.index"))
