"""
Shared pytest fixtures.

A fixture is a helper that pytest passes into any test that names it as a
parameter. Here every test gets a fresh app using the testing settings.
"""

import pytest

from app import create_app


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    """A fake browser that sends requests to the app without starting a server."""
    return app.test_client()
