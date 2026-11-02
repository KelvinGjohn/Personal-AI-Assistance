"""
Registration and login forms.

Validation happens on the server, because anything in the browser can be
bypassed. FlaskForm also adds a hidden CSRF token to every form.
"""

from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError

from app.models import User


def clean_text(value):
    """Remove spaces around the input."""
    return value.strip() if value else value


def clean_email(value):
    """Emails are saved in lower case so Alice@x.com and alice@x.com count as the same."""
    return value.strip().lower() if value else value


class RegistrationForm(FlaskForm):
    username = StringField("Username", filters=[clean_text], validators=[
        DataRequired(message="Enter a username."),
        Regexp(r"^[A-Za-z0-9_]{3,30}$",
               message="Use 3 to 30 letters, numbers or underscores."),
    ])
    email = EmailField("Email", filters=[clean_email], validators=[
        DataRequired(message="Enter your email address."),
        Length(max=120, message="Email must be 120 characters or fewer."),
        Email(message="Enter a valid email address."),
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Enter a password."),
        Length(min=8, max=128, message="Password must be 8 to 128 characters."),
    ])
    confirm_password = PasswordField("Confirm password", validators=[
        DataRequired(message="Enter your password again."),
        EqualTo("password", message="The passwords don't match."),
    ])
    submit = SubmitField("Create account")

    # WTForms automatically runs methods named validate_<fieldname>
    def validate_username(self, field):
        if User.query.filter(func.lower(User.username) == field.data.lower()).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("An account with that email already exists.")


class LoginForm(FlaskForm):
    identifier = StringField("Username or email", filters=[clean_text], validators=[
        DataRequired(message="Enter your username or email."),
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Enter your password."),
    ])
    remember = BooleanField("Keep me logged in")
    submit = SubmitField("Log in")
