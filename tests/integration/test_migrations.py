from sqlalchemy import inspect

from app import create_app
from app.extensions import db


def test_fresh_database_can_be_upgraded_with_flask_migrate(tmp_path):
    database_file = tmp_path / "migration-test.db"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "migration-test-key",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file}",
            "WTF_CSRF_ENABLED": False,
        }
    )
    runner = application.test_cli_runner()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output

    with application.app_context():
        table_names = set(inspect(db.engine).get_table_names())
        assert {"user", "product", "inventory_movement", "alembic_version"} <= table_names

    downgrade = runner.invoke(args=["db", "downgrade", "base"])
    assert downgrade.exit_code != 0
    assert "destructive and prohibited" in downgrade.output
    with application.app_context():
        assert {"user", "product", "inventory_movement"} <= set(
            inspect(db.engine).get_table_names()
        )
