"""Forms on the Settings page: edit profile and change password."""

from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.forms.auth_forms import clean_email, clean_text
from app.models import User
from app.utils import get_timezone_names


class ProfileForm(FlaskForm):
    full_name = StringField("Full name (optional)", filters=[clean_text], validators=[
        Length(max=100, message="Name must be 100 characters or fewer."),
    ])
    email = EmailField("Email", filters=[clean_email], validators=[
        DataRequired(message="Enter your email address."),
        Length(max=120, message="Email must be 120 characters or fewer."),
        Email(message="Enter a valid email address."),
    ])
    # A SelectField only accepts values from its list, so a made-up zone is rejected
    timezone = SelectField("Time zone", choices=get_timezone_names())
    save_profile = SubmitField("Save changes")

    def validate_email(self, field):
        # Keeping your own email is fine, so only OTHER users are checked
        taken = User.query.filter(User.email == field.data, User.id != current_user.id).first()
        if taken:
            raise ValidationError("An account with that email already exists.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[
        DataRequired(message="Enter your current password."),
    ])
    new_password = PasswordField("New password", validators=[
        DataRequired(message="Enter a new password."),
        Length(min=8, max=128, message="Password must be 8 to 128 characters."),
    ])
    confirm_new_password = PasswordField("Confirm new password", validators=[
        DataRequired(message="Enter your new password again."),
        EqualTo("new_password", message="The passwords don't match."),
    ])
    change_password = SubmitField("Change password")

    def validate_current_password(self, field):
        # Someone using a computer you left logged in can't change your password
        if not current_user.check_password(field.data):
            raise ValidationError("Your current password is incorrect.")

    def validate_new_password(self, field):
        if self.current_password.data == field.data:
            raise ValidationError("Choose a password different from your current one.")
