"""
Turns the Markdown in AI answers into safe HTML.

AI answers often use Markdown: **bold**, lists, `code` and tables. Showing it
as HTML looks much better, but an answer could also contain HTML of its own,
for example a <script> copied from a question. So there are two steps:

1. markdown turns the text into HTML. It lets any HTML in the text through.
2. nh3 removes everything that isn't on the short list below.

Only assistant answers go through this. User messages are always shown as plain text.
"""

import markdown
import nh3
from markupsafe import Markup

MARKDOWN_EXTENSIONS = [
    "fenced_code",  # ``` code blocks
    "tables",
    "sane_lists",
    "nl2br",        # a single line break stays a line break, as in a chat
]

ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "b", "em", "i", "del", "blockquote",
    "ul", "ol", "li", "code", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td",
    "a",
}
# No images: an image loads from another website, which could track who reads the answer
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}
# Only normal web and email links. This blocks "javascript:" links.
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_markdown(text):
    """Markdown text in, safe HTML out. Markup tells Jinja not to escape it again."""
    html = markdown.markdown(text or "", extensions=MARKDOWN_EXTENSIONS)
    clean = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        # Links to pages of this app (like "/logout") are removed too, so an
        # answer can't trick someone into clicking something inside the app
        url_relative="deny",
        link_rel="noopener noreferrer nofollow",
    )
    return Markup(clean)
