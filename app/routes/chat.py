"""Chat routes: the page where the user talks to the AI."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.forms.chat_forms import MAX_MESSAGE_LENGTH, ChatForm
from app.services.ai_service import AIServiceError, is_fallback_mode
from app.services.chat_service import (
    get_latest_conversation,
    get_user_conversation_or_404,
    is_fallback_message,
    send_message,
)

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def chat_page(conversation):
    """Show a chat and handle a sent message. conversation is None for a new chat."""
    form = ChatForm()
    if form.validate_on_submit():
        try:
            conversation = send_message(current_user.id, conversation, form.message.data)
        except AIServiceError as error:
            # Nothing was saved, and the form still holds the text so it can be sent again
            flash(str(error), "danger")
        else:
            # Redirecting means refreshing the page won't send the message twice
            return redirect(url_for("chat.conversation", conversation_id=conversation.id))

    return render_template(
        "chat/index.html",
        form=form,
        conversation=conversation,
        fallback_mode=is_fallback_mode(),
        is_fallback_message=is_fallback_message,
        max_message_length=MAX_MESSAGE_LENGTH,
    )


@chat_bp.route("")
@login_required
def index():
    """Open the most recent chat, or a new one if there are none."""
    latest = get_latest_conversation(current_user.id)
    if latest is None:
        return redirect(url_for("chat.new"))
    return redirect(url_for("chat.conversation", conversation_id=latest.id))


@chat_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    return chat_page(None)


@chat_bp.route("/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def conversation(conversation_id):
    return chat_page(get_user_conversation_or_404(current_user.id, conversation_id))
