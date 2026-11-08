from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import InventoryMovement, Product, User
from app.services.inventory import record_movement


def test_login_logout(client, admin):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "在庫".encode() in response.data

    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert "ログイン".encode() in response.data


@pytest.mark.parametrize(
    "next_url",
    ["https://attacker.example", "//attacker.example", "/\\\\attacker.example", "http://["],
)
def test_login_next_external_url_is_ignored(client, admin, next_url):
    response = client.post(
        "/login",
        query_string={"next": next_url},
        data={"username": "admin", "password": "test-password"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/inventory")


def test_invalid_password_does_not_authenticate(client, admin):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "ユーザー名またはパスワード".encode() in response.data
    assert client.get("/inventory").status_code == 302


def test_product_registration_and_duplicate_code_rejection(client, login_admin, app):
    form = {
        "code": "TEA-01",
        "name": "紅茶",
        "category": "飲料",
        "unit": "袋",
        "reorder_point": "3.000",
    }
    first = client.post("/products/new", data=form, follow_redirects=True)
    assert first.status_code == 200

    duplicate = client.post(
        "/products/new",
        data={**form, "name": "別の商品"},
        follow_redirects=True,
    )
    assert duplicate.status_code == 200
    with app.app_context():
        assert db.session.query(Product).filter_by(code="TEA-01").count() == 1


def test_product_edit_updates_master(client, login_admin, product, app):
    response = client.post(
        f"/products/{product}/edit",
        data={
            "code": "COF-001",
            "name": "深煎りコーヒー豆",
            "category": "コーヒー",
            "unit": "kg",
            "reorder_point": "1.500",
            "is_active": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        item = db.session.get(Product, product)
        assert item.name == "深煎りコーヒー豆"
        assert item.reorder_point == Decimal("1.500")
        assert item.is_active is True


def test_product_can_be_deactivated_without_deleting_it(client, login_admin, product, app):
    response = client.post(
        f"/products/{product}/edit",
        data={
            "code": "COF-001",
            "name": "コーヒー豆",
            "category": "材料",
            "unit": "kg",
            "reorder_point": "2",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        item = db.session.get(Product, product)
        assert item.is_active is False


def test_stock_forms_record_receipt_usage_and_waste(client, login_admin, app):
    registration = client.post(
        "/products/new",
        data={
            "code": "MILK-01",
            "name": "牛乳",
            "category": "材料",
            "unit": "L",
            "reorder_point": "1",
        },
        follow_redirects=True,
    )
    assert registration.status_code == 200
    with app.app_context():
        item = db.session.scalar(db.select(Product).where(Product.code == "MILK-01"))
        product_id = item.id

    receipt = client.post(
        "/stock/receipt",
        data={"product_id": str(product_id), "quantity": "8"},
        follow_redirects=True,
    )
    usage = client.post(
        "/stock/issue",
        data={"product_id": str(product_id), "quantity": "2.5", "kind": "usage"},
        follow_redirects=True,
    )
    waste = client.post(
        "/stock/issue",
        data={"product_id": str(product_id), "quantity": "0.5", "kind": "waste"},
        follow_redirects=True,
    )

    assert receipt.status_code == usage.status_code == waste.status_code == 200
    with app.app_context():
        assert db.session.query(InventoryMovement).count() == 3
        assert [
            movement.kind
            for movement in db.session.scalars(
                db.select(InventoryMovement).order_by(InventoryMovement.id)
            )
        ] == ["receipt", "usage", "waste"]


def test_staff_cannot_manage_products(client, login_staff):
    response = client.get("/products/new")
    assert response.status_code == 403


def test_public_registration_is_not_available(client):
    assert client.get("/register").status_code == 404


def test_staff_cli_creates_non_admin_account(app):
    result = app.test_cli_runner().invoke(
        args=["create-staff", "--username", "new-staff"],
        input="a-very-long-test-password\na-very-long-test-password\n",
    )
    assert result.exit_code == 0
    assert "スタッフを作成しました" in result.output
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == "new-staff"))
        assert user.role == "staff"
        assert user.check_password("a-very-long-test-password")


def test_production_requires_secret_and_postgresql_url(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY, DATABASE_URL"):
        create_app()


def test_production_configuration_disables_debug_and_requires_ssl(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("SECRET_KEY", "production-test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@db.example/inventory")
    application = create_app({"DEBUG": True, "TESTING": True})

    assert application.config["DEBUG"] is False
    assert application.config["TESTING"] is False
    assert application.config["SESSION_COOKIE_SECURE"] is True
    assert "sslmode=require" in application.config["SQLALCHEMY_DATABASE_URI"]


def test_inventory_history_and_reorder_alert(client, login_admin, app, admin, product):
    with app.app_context():
        record_movement(product, admin, "receipt", Decimal("2"))
        db.session.commit()

    inventory = client.get("/inventory")
    assert inventory.status_code == 200
    assert "発注".encode() in inventory.data

    history = client.get("/history")
    assert history.status_code == 200
    assert "入庫".encode() in history.data
    with app.app_context():
        assert db.session.query(InventoryMovement).count() == 1


def test_state_change_requires_csrf_when_enabled(tmp_path):
    from app import create_app

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-not-for-production",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}",
            "WTF_CSRF_ENABLED": True,
        }
    )
    response = application.test_client().post("/login", data={"username": "x", "password": "x"})
    assert response.status_code == 400
