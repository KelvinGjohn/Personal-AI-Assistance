"""Day 3 - tests for the application factory, configuration and first routes."""

import pytest

from app import create_app


def test_testing_config_is_used(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Personal AI Assistant" in response.data
    assert b"The Flask application is running." in response.data


def test_health_check_returns_json(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok",
                                   "app": "Personal AI Assistant"}


def test_unknown_page_returns_404(client):
    assert client.get("/does-not-exist").status_code == 404


def test_unknown_config_name_is_rejected():
    with pytest.raises(ValueError):
        create_app("not-a-real-config")


def test_app_refuses_to_start_without_secret_key(monkeypatch):
    from config.settings import DevelopmentConfig

    monkeypatch.setattr(DevelopmentConfig, "SECRET_KEY", None)
    with pytest.raises(RuntimeError):
        create_app("development")
