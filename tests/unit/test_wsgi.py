import importlib


def test_wsgi_exposes_gunicorn_default_application(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-only-secret-key-long-enough")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    module = importlib.import_module("wsgi")
    module = importlib.reload(module)

    assert module.application is module.app
