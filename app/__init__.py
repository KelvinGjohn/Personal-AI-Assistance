"""
The application factory.

create_app() builds and returns a new Flask app. Using a function instead of
one global app object means tests can create their own app with test settings.
"""

import os

from dotenv import load_dotenv
from flask import Flask

# Read the .env file into environment variables BEFORE the config is imported,
# so config/settings.py can see SECRET_KEY, DATABASE_URL, etc.
load_dotenv()

from config import config_by_name  # noqa: E402  (must come after load_dotenv)


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    if config_name not in config_by_name:
        raise ValueError(f"Unknown configuration '{config_name}'. "
                         f"Use one of: {', '.join(config_by_name)}")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Refuse to start without a secret key instead of running insecurely.
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env "
                           "and give SECRET_KEY a value.")

    init_database(app)
    register_blueprints(app)
    return app


def init_database(app):
    """Connect SQLAlchemy to the app and create any missing tables."""
    from app.extensions import db
    from app import models  # noqa: F401  (registers every model with SQLAlchemy)

    db.init_app(app)
    with app.app_context():
        # Creates tables that don't exist yet. It never deletes or changes existing data.
        db.create_all()


def register_blueprints(app):
    """Connect each group of routes (Blueprint) to the app."""
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
