"""Authentication routes: register, log in and log out."""

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.auth_forms import LoginForm, RegistrationForm
from app.models import User

auth_bp = Blueprint("auth", __name__)


def is_safe_redirect(target):
    """
    Only allow redirects to pages on this site.

    The "next" address comes from the URL, so an attacker could send someone a
    login link with next=https://evil.example. Without this check, the user
    would land on the attacker's site right after logging in.
    """
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    # validate_on_submit() is True only for a POST that passes every validator
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            # Two people submitted the same name at the same moment: the database's
            # UNIQUE rule catches what the form check could not.
            db.session.rollback()
            flash("That username or email was just taken. Please try another.", "danger")
            return render_template("auth/register.html", form=form), 409

        login_user(user)
        flash(f"Welcome, {user.username}! Your account has been created.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.lower()
        user = User.query.filter(
            or_(func.lower(User.username) == identifier, User.email == identifier)
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return redirect(next_page if is_safe_redirect(next_page) else url_for("main.index"))

        # The same message for both cases, so nobody can use this page to
        # find out which usernames and emails have accounts.
        flash("Incorrect username, email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """POST only, so another website can't log you out with just a link or image."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
