"""The form for sending a chat message."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.forms.auth_forms import clean_text

MAX_MESSAGE_LENGTH = 4000


class ChatForm(FlaskForm):
    message = TextAreaField("Your message", filters=[clean_text], validators=[
        DataRequired(message="Please enter a message."),
        Length(max=MAX_MESSAGE_LENGTH,
               message=f"Message must be {MAX_MESSAGE_LENGTH} characters or fewer."),
    ])
    # Off unless the user ticks it, because it sends their data to the AI provider
    use_my_data = BooleanField("Use my tasks, reminders and notes")
