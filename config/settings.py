"""
Application configuration.

Each class is a group of settings. The app picks one of them when it starts
(development, testing or production). Secret values are NOT written here:
they are read from environment variables, which come from the .env file.
"""

import os


class Config:
    """Settings shared by every environment."""

    # Used by Flask to sign session cookies and CSRF tokens. Must stay secret.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Cookie safety: JavaScript can't read the cookies (HttpOnly) and other
    # websites' forms don't send them (SameSite)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Where the SQLite database lives (used from Day 4).
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///assistant.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI provider settings (used from Day 12). "fallback" means no real AI.
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "fallback")
    AI_API_KEY = os.environ.get("AI_API_KEY", "")
    AI_MODEL = os.environ.get("AI_MODEL", "")

    APP_NAME = "Personal AI Assistant"


class DevelopmentConfig(Config):
    """Used on your own computer while coding. Shows detailed error pages."""

    DEBUG = True


class TestingConfig(Config):
    """Used by pytest. Uses a temporary in-memory database."""

    TESTING = True
    SECRET_KEY = "test-only-secret-key"  # Not a real secret: only used inside tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # Tests post forms directly; test_auth.py switches it on to test it


class ProductionConfig(Config):
    """Used on the live server (Day 28)."""

    DEBUG = False
    # Live site uses HTTPS, so cookies must never travel over plain HTTP
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


# Lets create_app("development") find the right class by name
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
