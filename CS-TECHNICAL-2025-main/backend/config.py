# config.py
import os

def _csv_env(name: str, default: str = "") -> list[str]:
    val = os.getenv(name, default)
    # split only if non-empty; strip whitespace
    return [x.strip() for x in val.split(",")] if val else []

class BaseConfig:
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    PREFERRED_URL_SCHEME = "https"

    # Secrets (must be set in env for prod)
    SECRET_KEY = os.getenv("APP_SECRET_KEY") or "dev-only-secret-change-me"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "dev-only-jwt-secret-change-me"

    # CORS
    CORS_ORIGINS = _csv_env("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000")

    # Uploads
    ALLOWED_EXTS = {"pdf", "txt", "doc", "docx"}

class DevConfig(BaseConfig):
    DEBUG = True

class ProdConfig(BaseConfig):
    # # In production, fail if secrets are missing
    # SECRET_KEY = os.getenv("APP_SECRET_KEY")
    # JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    # if not SECRET_KEY or not JWT_SECRET_KEY:
    #     raise RuntimeError("APP_SECRET_KEY and JWT_SECRET_KEY must be set in production")
    pass

def validate_required_secrets():
    if os.getenv("ENV") == "prod":
        if not os.getenv("APP_SECRET_KEY") or not os.getenv("JWT_SECRET_KEY"):
            raise RuntimeError("APP_SECRET_KEY and JWT_SECRET_KEY must be set in production")