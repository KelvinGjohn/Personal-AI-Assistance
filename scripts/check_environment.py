"""
Day 2 - Development environment check.

Run this after installing the requirements to make sure every library
the project needs is installed and working:

    py scripts/check_environment.py      (or: python scripts/check_environment.py inside the venv)
"""

import sys
from importlib.metadata import version, PackageNotFoundError

# The packages listed in requirements.txt
REQUIRED_PACKAGES = [
    "Flask",
    "Flask-SQLAlchemy",
    "SQLAlchemy",
    "Flask-Login",
    "Flask-WTF",
    "email-validator",
    "python-dotenv",
    "requests",
    "pytest",
]


def check_python_version():
    """The project needs Python 3.10 or newer."""
    ok = sys.version_info >= (3, 10)
    print(f"[{'OK' if ok else 'FAIL'}] Python {sys.version.split()[0]}")
    return ok


def check_packages():
    """Check that each required package is installed."""
    all_ok = True
    for package in REQUIRED_PACKAGES:
        try:
            print(f"[OK] {package} {version(package)}")
        except PackageNotFoundError:
            print(f"[FAIL] {package} is not installed")
            all_ok = False
    return all_ok


def check_flask_and_database():
    """Start a tiny Flask app with an in-memory SQLite database to prove they work together."""
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        from sqlalchemy import text

        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        db = SQLAlchemy(app)

        with app.app_context():
            result = db.session.execute(text("SELECT 1")).scalar()

        ok = result == 1
        print(f"[{'OK' if ok else 'FAIL'}] Flask + SQLAlchemy + SQLite connection")
        return ok
    except Exception as error:
        print(f"[FAIL] Flask + SQLAlchemy + SQLite connection: {error}")
        return False


if __name__ == "__main__":
    print("Checking development environment...\n")
    results = [check_python_version(), check_packages(), check_flask_and_database()]

    if all(results):
        print("\nEnvironment is ready.")
    else:
        print("\nSome checks failed. Run: pip install -r requirements.txt")
        sys.exit(1)
