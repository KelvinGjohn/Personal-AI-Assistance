"""Day 2 - automated check that the development environment works."""

import sys
from pathlib import Path

# Let the test import the script from the scripts/ folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_environment


def test_python_version_is_supported():
    assert check_environment.check_python_version()


def test_all_required_packages_installed():
    assert check_environment.check_packages()


def test_flask_can_talk_to_sqlite():
    assert check_environment.check_flask_and_database()
