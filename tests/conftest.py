from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db
from app.models import Product, User


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key-not-for-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(app):
    with app.app_context():
        user = User(username="admin", role="admin")
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def staff(app):
    with app.app_context():
        user = User(username="staff", role="staff")
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def product(app):
    with app.app_context():
        item = Product(
            code="COF-001",
            name="コーヒー豆",
            category="材料",
            unit="kg",
            reorder_point=Decimal("2.000"),
        )
        db.session.add(item)
        db.session.commit()
        return item.id


@pytest.fixture
def login_admin(client, admin):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    return admin


@pytest.fixture
def login_staff(client, staff):
    response = client.post(
        "/login",
        data={"username": "staff", "password": "test-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    return staff
