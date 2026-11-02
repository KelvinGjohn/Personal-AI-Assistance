"""
Shared pytest fixtures.

A fixture is a helper that pytest passes into any test that names it as a
parameter. Every test gets a fresh app with its own empty in-memory database.
"""

import contextvars

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db as _db

TEST_PASSWORD = "correct-horse-battery"  # Only ever used in the temporary test database


class RealisticClient(FlaskClient):
    """
    Runs each request in its own empty context, like a real server does.

    Without this, every request would reuse the app context held open by the
    `app` fixture. Flask-Login caches the current user in that context's `g`,
    so a second user's request would wrongly see the first user.
    """

    def open(self, *args, **kwargs):
        return contextvars.Context().run(super().open, *args, **kwargs)


@pytest.fixture
def app():
    app = create_app("testing")
    app.test_client_class = RealisticClient
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

    def _make_user(username, email=None, password=TEST_PASSWORD):
        user = User(username=username, email=email or f"{username}@example.com")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture
def login():
    """Helper to log a test client in: login(client, "alice")."""

    def _login(test_client, identifier, password=TEST_PASSWORD, **extra):
        return test_client.post("/login", data={"identifier": identifier, "password": password, **extra})

    return _login


@pytest.fixture
def auth_client(client, make_user, login):
    """A fake browser that is already logged in as the user "tester"."""
    make_user("tester")
    login(client, "tester")
    return client
