import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import make_url

from app import create_app
from app.extensions import db
from app.models import Product, User
from app.services.inventory import InsufficientStockError, get_stock, record_movement


@pytest.mark.postgres
def test_concurrent_issue_never_makes_stock_negative():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        if os.getenv("CI") == "true":
            pytest.fail("CI must configure TEST_DATABASE_URL for PostgreSQL integration tests")
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL concurrency tests")

    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() != "postgresql":
        pytest.fail("PostgreSQL concurrency tests refuse non-PostgreSQL databases")
    if os.getenv("CI") != "true":
        pytest.fail("PostgreSQL concurrency tests may only run against CI's disposable service")
    if "neon.tech" in (parsed_url.host or ""):
        pytest.fail("PostgreSQL tests refuse Neon databases")
    if not any(marker in (parsed_url.database or "").lower() for marker in ("test", "ci")):
        pytest.fail("PostgreSQL test database name must clearly identify a disposable test DB")

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "postgres-test-key",
            "SQLALCHEMY_DATABASE_URI": database_url,
            "WTF_CSRF_ENABLED": False,
        }
    )
    with application.app_context():
        db.drop_all()
        migration = application.test_cli_runner().invoke(args=["db", "upgrade"])
        assert migration.exit_code == 0, migration.output
        user = User(username="concurrency-admin", role="admin")
        user.set_password("test-password")
        item = Product(
            code="LOCK-001",
            name="同時出庫テスト",
            category="材料",
            unit="個",
            reorder_point=Decimal("0"),
        )
        db.session.add_all([user, item])
        db.session.commit()
        user_id, product_id = user.id, item.id
        record_movement(product_id, user_id, "receipt", Decimal("5"))
        db.session.remove()

    def issue_four():
        with application.app_context():
            try:
                record_movement(product_id, user_id, "usage", Decimal("4"))
                return "success"
            except InsufficientStockError:
                return "insufficient"
            finally:
                db.session.remove()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: issue_four(), range(2)))
        assert outcomes.count("success") == 1
        assert outcomes.count("insufficient") == 1
        with application.app_context():
            assert get_stock(product_id) == Decimal("1.000")
    finally:
        with application.app_context():
            db.session.remove()
            db.drop_all()
