"""The form for creating and editing a task."""

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    SelectChoice,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.forms.auth_forms import clean_text
from app.models.task import PRIORITIES

MIN_YEAR = 2000
MAX_YEAR = 2100


def check_year_range(field):
    """Stops extreme dates such as year 1, which can't be converted between time zones."""
    if field.data and not MIN_YEAR <= field.data.year <= MAX_YEAR:
        raise ValidationError(f"Enter a date between {MIN_YEAR} and {MAX_YEAR}.")


class TaskForm(FlaskForm):
    title = StringField("Title", filters=[clean_text], validators=[
        DataRequired(message="Enter a title."),
        Length(max=200, message="Title must be 200 characters or fewer."),
    ])
    description = TextAreaField("Description (optional)", filters=[clean_text], validators=[
        Length(max=5000, message="Description must be 5000 characters or fewer."),
    ])
    priority = SelectField("Priority", default="medium",
                           choices=[SelectChoice(name, name.capitalize()) for name in PRIORITIES])
    category = StringField("Category (optional)", filters=[clean_text], validators=[
        Length(max=50, message="Category must be 50 characters or fewer."),
    ])
    due_date = DateTimeLocalField("Due date (optional)", format="%Y-%m-%dT%H:%M",
                                  validators=[Optional()])
    submit = SubmitField("Save task")

    def validate_due_date(self, field):
        check_year_range(field)


class TaskRequestForm(FlaskForm):
    """A task described in plain words, for the AI to turn into a suggestion."""

    request = TextAreaField("Describe the task", filters=[clean_text], validators=[
        DataRequired(message="Describe the task first."),
        Length(max=1000, message="Please keep it to 1000 characters or fewer."),
    ])
    submit = SubmitField("Suggest task")
