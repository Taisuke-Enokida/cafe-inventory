from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import db
from app.models import User

bp = Blueprint("auth", __name__)


def _safe_next_url(value: str) -> str:
    fallback = url_for("inventory.index")
    try:
        parsed = urlparse(value)
    except ValueError:
        return fallback
    if (
        not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or parsed.scheme
        or parsed.netloc
    ):
        return fallback
    return value


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inventory.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.session.scalar(db.select(User).where(User.username == username))
        if user is not None and user.is_active and user.check_password(password):
            login_user(user)
            return redirect(_safe_next_url(request.args.get("next", "")))
        flash("ユーザー名またはパスワードが正しくありません。", "error")

    return render_template("login.html")


@bp.post("/logout")
def logout():
    logout_user()
    flash("ログアウトしました。", "success")
    return redirect(url_for("auth.login"))
