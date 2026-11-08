"""The form for creating and editing a reminder."""

from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from app.forms.auth_forms import clean_text
from app.forms.task_forms import check_year_range
from app.utils import user_time_to_utc, utc_now, whole_minute


class ReminderForm(FlaskForm):
    title = StringField("Title", filters=[clean_text], validators=[
        DataRequired(message="Enter a title."),
        Length(max=200, message="Title must be 200 characters or fewer."),
    ])
    description = TextAreaField("Description (optional)", filters=[clean_text], validators=[
        Length(max=5000, message="Description must be 5000 characters or fewer."),
    ])
    remind_at = DateTimeLocalField("Remind me at", format="%Y-%m-%dT%H:%M", validators=[
        DataRequired(message="Enter a valid date and time."),
    ])
    submit = SubmitField("Save reminder")

    def __init__(self, *args, saved_time=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_time = whole_minute(saved_time) if saved_time else None

    def validate_remind_at(self, field):
        check_year_range(field)
        # A reminder in the past would be pointless, but an old reminder must
        # still be editable: fixing a typo in its title shouldn't be refused.
        new_time = user_time_to_utc(field.data)
        if new_time <= utc_now() and new_time != self.saved_time:
            raise ValidationError("Choose a time in the future.")


class ReminderRequestForm(FlaskForm):
    """A reminder described in plain words, for the AI to turn into a suggestion."""

    request = TextAreaField("Describe the reminder", filters=[clean_text], validators=[
        DataRequired(message="Describe the reminder first."),
        Length(max=1000, message="Please keep it to 1000 characters or fewer."),
    ])
    submit = SubmitField("Suggest reminder")
