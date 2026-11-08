import os

from sqlalchemy.engine import make_url


def normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql+psycopg://", 1)
    elif value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)

    url = make_url(value)
    if url.get_backend_name() == "postgresql":
        query = dict(url.query)
        query.setdefault("sslmode", "require")
        value = url.set(query=query).render_as_string(hide_password=False)
    return value


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite:///inventory.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    WTF_CSRF_ENABLED = True
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
