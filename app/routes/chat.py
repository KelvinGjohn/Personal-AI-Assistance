"""Chat routes: the page where the user talks to the AI."""

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.forms.chat_forms import MAX_MESSAGE_LENGTH, ChatForm
from app.services.ai_service import AIServiceError, is_fallback_mode
from app.services.chat_service import (
    get_latest_conversation,
    get_user_conversation_or_404,
    is_fallback_message,
    send_message,
)
from app.services.personal_data import MAX_NOTES, build_personal_context

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def chat_page(conversation):
    """Show a chat and handle a sent message. conversation is None for a new chat."""
    form = ChatForm()
    ai_error = None
    if form.validate_on_submit():
        # Built only when ticked, and only from the logged-in user's own records
        context = build_personal_context(current_user) if form.use_my_data.data else None
        try:
            conversation = send_message(current_user.id, conversation, form.message.data, context)
        except AIServiceError as error:
            # Nothing was saved, and the form still holds the text so it can be sent again
            ai_error = str(error)
        else:
            # Redirecting means refreshing the page won't send the message twice.
            # The address remembers the tick box for the next message.
            options = {"use_my_data": 1} if form.use_my_data.data else {}
            return redirect(url_for("chat.conversation", conversation_id=conversation.id, **options))
    elif request.method == "GET":
        form.use_my_data.data = request.args.get("use_my_data") == "1"

    return render_template(
        "chat/index.html",
        form=form,
        conversation=conversation,
        ai_error=ai_error,
        fallback_mode=is_fallback_mode(),
        is_fallback_message=is_fallback_message,
        max_message_length=MAX_MESSAGE_LENGTH,
        max_notes=MAX_NOTES,
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
