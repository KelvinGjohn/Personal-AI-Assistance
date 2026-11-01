"""
Shared pytest fixtures.

A fixture is a helper that pytest passes into any test that names it as a
parameter. Every test gets a fresh app with its own empty in-memory database.
"""

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    app = create_app("testing")
    # An app context lets tests use the database directly (db.session, Model.query)
    with app.app_context():
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """A fake browser that sends requests to the app without starting a server."""
    return app.test_client()


@pytest.fixture
def db(app):
    """The database, ready to use inside a test."""
    return _db


@pytest.fixture
def make_user(db):
    """Helper to create a user quickly: make_user("alice")."""
    from app.models import User

    def _make_user(username, email=None):
        user = User(username=username,
                    email=email or f"{username}@example.com",
                    password_hash="not-a-real-hash")
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user
