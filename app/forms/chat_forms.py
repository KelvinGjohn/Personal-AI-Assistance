"""Chat forms: sending a message and renaming a chat."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
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


class ConversationTitleForm(FlaskForm):
    """Renaming a chat."""

    title = StringField("Chat name", filters=[clean_text], validators=[
        DataRequired(message="Enter a name for the chat."),
        Length(max=200, message="Name must be 200 characters or fewer."),
    ])
    submit = SubmitField("Save name")
