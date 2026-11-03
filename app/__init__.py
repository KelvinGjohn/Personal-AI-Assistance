"""
The application factory.

create_app() builds and returns a new Flask app. Using a function instead of
one global app object means tests can create their own app with test settings.
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template

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
    init_security(app)
    register_blueprints(app)
    register_template_helpers(app)
    register_error_handlers(app)
    return app


def init_database(app):
    """Connect SQLAlchemy to the app and create any missing tables."""
    from app.extensions import db
    from app import models  # noqa: F401  (registers every model with SQLAlchemy)

    db.init_app(app)
    with app.app_context():
        # Creates tables that don't exist yet. It never deletes or changes existing data.
        db.create_all()


def init_security(app):
    """Connect login sessions and CSRF protection to the app."""
    from app.extensions import csrf, login_manager

    login_manager.init_app(app)
    csrf.init_app(app)


def register_blueprints(app):
    """Connect each group of routes (Blueprint) to the app."""
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.settings import settings_bp
    from app.routes.tasks import tasks_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(tasks_bp)


def register_template_helpers(app):
    """Make the sidebar and header data, and our filters, available to every template."""
    from app.navigation import inject_layout_data
    from app.utils import datetime_short

    app.context_processor(inject_layout_data)
    app.add_template_filter(datetime_short)


def register_error_handlers(app):
    """Show friendly error pages that use the normal layout."""
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        # Usually a form left open too long, so its security token has expired
        return render_template("errors/400.html"), 400

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("errors/500.html"), 500
