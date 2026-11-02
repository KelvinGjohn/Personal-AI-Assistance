"""
Flask extensions, created once and shared by the whole app.

They are created here WITHOUT an app and connected later in create_app()
with init_app(). This avoids circular imports: models can import `db`
from here without importing the app itself.
"""

import sqlite3

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()

# Remembers who is logged in between requests, using a signed session cookie
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # where @login_required sends visitors
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"

# Rejects any POST request that doesn't carry a valid CSRF token
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    SQLite ignores foreign keys unless this is switched on for every connection.
    With it on, the database itself refuses e.g. a task whose user_id doesn't exist.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
