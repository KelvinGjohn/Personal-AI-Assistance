"""The form for creating and editing a note."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.forms.auth_forms import clean_text


class NoteForm(FlaskForm):
    title = StringField("Title", filters=[clean_text], validators=[
        DataRequired(message="Enter a title."),
        Length(max=200, message="Title must be 200 characters or fewer."),
    ])
    content = TextAreaField("Content (optional)", filters=[clean_text], validators=[
        Length(max=50000, message="Content must be 50000 characters or fewer."),
    ])
    category = StringField("Category (optional)", filters=[clean_text], validators=[
        Length(max=50, message="Category must be 50 characters or fewer."),
    ])
    submit = SubmitField("Save note")
