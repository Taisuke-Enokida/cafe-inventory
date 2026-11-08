import os

import click
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.config import Config, normalize_database_url
from app.extensions import csrf, db, login_manager, migrate


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if os.getenv("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    if os.getenv("DATABASE_URL"):
        app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(os.environ["DATABASE_URL"])
    if test_config:
        app.config.update(test_config)

    production = os.getenv("FLASK_ENV") == "production" or os.getenv("RENDER") == "true"
    if production:
        missing = [key for key in ("SECRET_KEY", "DATABASE_URL") if not os.getenv(key)]
        if missing:
            raise RuntimeError(f"本番環境に必須の環境変数がありません: {', '.join(missing)}")
        if not os.getenv("DATABASE_URL", "").startswith(
            ("postgres://", "postgresql://", "postgresql+psycopg://")
        ):
            raise RuntimeError("本番DATABASE_URLにはNeon PostgreSQLのURLが必要です。")
        app.config["DEBUG"] = False
        app.config["TESTING"] = False
        app.config["SESSION_COOKIE_SECURE"] = True
    elif not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEYを設定してください。.env.exampleを参照してください。")

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User
    from app.routes.auth import bp as auth_bp
    from app.routes.inventory import bp as inventory_bp
    from app.routes.products import bp as products_bp

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except ValueError:
            return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(products_bp)
    app.cli.add_command(create_admin)
    app.cli.add_command(create_staff)
    return app


@click.command("create-admin")
@click.option("--username", prompt="管理者ユーザー名")
def create_admin(username: str) -> None:
    """Create an administrator without exposing the password in shell history."""
    _create_user(username, "admin")


@click.command("create-staff")
@click.option("--username", prompt="スタッフユーザー名")
def create_staff(username: str) -> None:
    """Create a staff account without public self-registration."""
    _create_user(username, "staff")


def _create_user(username: str, role: str) -> None:
    from app.models import User

    username = username.strip()
    if not username:
        raise click.ClickException("ユーザー名を入力してください。")
    password = click.prompt("パスワード", hide_input=True, confirmation_prompt=True)
    if len(password) < 12:
        raise click.ClickException("パスワードは12文字以上にしてください。")
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise click.ClickException("そのユーザー名は既に使われています。") from None
    click.echo(f"{'管理者' if role == 'admin' else 'スタッフ'}を作成しました。")
