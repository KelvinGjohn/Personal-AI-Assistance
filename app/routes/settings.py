"""Settings page: the logged-in user edits their profile and password."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.settings_forms import ChangePasswordForm, ProfileForm

settings_bp = Blueprint("settings", __name__)


def build_form(form_class, button_name, **kwargs):
    """
    The page has two forms. Only the form whose button was pressed reads the
    submitted data; the other one just shows its normal values.
    """
    if button_name in request.form:
        return form_class(**kwargs)
    return form_class(formdata=None, **kwargs)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def index():
    profile_form = build_form(ProfileForm, "save_profile", obj=current_user)
    password_form = build_form(ChangePasswordForm, "change_password")

    if "save_profile" in request.form and profile_form.validate_on_submit():
        # Every change goes to current_user, so nobody can edit another account
        current_user.full_name = profile_form.full_name.data or None
        current_user.email = profile_form.email.data
        current_user.timezone = profile_form.timezone.data
        try:
            db.session.commit()
        except IntegrityError:
            # Someone else took this email at the same moment
            db.session.rollback()
            flash("That email was just taken. Please try another.", "danger")
            return render_template("settings.html", profile_form=profile_form,
                                   password_form=password_form), 409

        flash("Your profile has been updated.", "success")
        # Redirecting means refreshing the page won't submit the form twice
        return redirect(url_for("settings.index"))

    if "change_password" in request.form and password_form.validate_on_submit():
        current_user.set_password(password_form.new_password.data)
        db.session.commit()
        flash("Your password has been changed.", "success")
        return redirect(url_for("settings.index"))

    return render_template("settings.html", profile_form=profile_form, password_form=password_form)
