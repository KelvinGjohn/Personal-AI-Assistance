"""
Shared pytest fixtures.

A fixture is a helper that pytest passes into any test that names it as a
parameter. Every test gets a fresh app with its own empty in-memory database.
"""

import contextvars

import pytest
from flask import has_app_context
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db as _db

TEST_PASSWORD = "correct-horse-battery"  # Only ever used in the temporary test database

# Hashing is slow on purpose, so tests reuse one hash. test_auth.py tests real hashing.
TEST_PASSWORD_HASH = generate_password_hash(TEST_PASSWORD)


class RealisticClient(FlaskClient):
    """
    Runs each request in its own empty context, like a real server does.

    Without this, every request would reuse the app context held open by the
    `app` fixture. Flask-Login caches the current user in that context's `g`,
    so a second user's request would wrongly see the first user.

    The test's own database session is then told to forget what it has loaded.
    Otherwise it would keep old copies of records, and a check that something
    "did not change" could pass without really looking at the database.
    """

    def open(self, *args, **kwargs):
        response = contextvars.Context().run(super().open, *args, **kwargs)
        # Followed redirects call open() again inside the empty context, where there is no session
        if has_app_context():
            _db.session.expire_all()
        return response


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
        if password == TEST_PASSWORD:
            user.password_hash = TEST_PASSWORD_HASH
        else:
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
def auth_client(client, make_user):
    """
    A fake browser that is already logged in as the user "tester".

    It writes the login directly into the session, which skips the slow password
    check. The real login page is tested in test_auth.py.
    """
    user = make_user("tester")
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    return client
