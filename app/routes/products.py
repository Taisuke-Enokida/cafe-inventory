from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Product

bp = Blueprint("products", __name__, url_prefix="/products")


def _require_admin() -> None:
    if current_user.role != "admin":
        abort(403)


def _form_values():
    try:
        reorder_point = Decimal(request.form.get("reorder_point", ""))
        if not reorder_point.is_finite() or reorder_point < 0:
            raise InvalidOperation
    except InvalidOperation:
        raise ValueError("発注点は0以上の数値で入力してください。") from None

    values = {
        "code": request.form.get("code", "").strip(),
        "name": request.form.get("name", "").strip(),
        "category": request.form.get("category", "").strip(),
        "unit": request.form.get("unit", "").strip(),
        "reorder_point": reorder_point,
    }
    if not all(values[key] for key in ("code", "name", "category", "unit")):
        raise ValueError("商品コード、商品名、カテゴリ、単位は必須です。")
    if (
        len(values["code"]) > 40
        or len(values["name"]) > 120
        or len(values["category"]) > 80
        or len(values["unit"]) > 24
    ):
        raise ValueError("各項目が入力可能な文字数を超えています。")
    if (
        reorder_point > Decimal("999999999.999")
        or reorder_point.quantize(Decimal("0.001")) != reorder_point
    ):
        raise ValueError("発注点は小数3桁以内で入力してください。")
    return values


@bp.get("")
@login_required
def list_products():
    _require_admin()
    products = db.session.scalars(select(Product).order_by(Product.code)).all()
    return render_template("products.html", products=products)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    _require_admin()
    if request.method == "POST":
        try:
            product = Product(**_form_values())
            db.session.add(product)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        except IntegrityError:
            db.session.rollback()
            flash("商品コードが既に登録されています。", "error")
        else:
            flash("商品を登録しました。", "success")
            return redirect(url_for("products.list_products"))
    return render_template("product_form.html", product=None)


@bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit(product_id: int):
    _require_admin()
    product = db.get_or_404(Product, product_id)
    if request.method == "POST":
        try:
            values = _form_values()
            product.code = values["code"]
            product.name = values["name"]
            product.category = values["category"]
            product.unit = values["unit"]
            product.reorder_point = values["reorder_point"]
            product.is_active = request.form.get("is_active") == "on"
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(str(error), "error")
        except IntegrityError:
            db.session.rollback()
            flash("商品コードが既に登録されています。", "error")
        else:
            flash("商品情報を更新しました。", "success")
            return redirect(url_for("products.list_products"))
    return render_template("product_form.html", product=product)
