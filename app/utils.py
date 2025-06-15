from markdown import markdown
from markupsafe import Markup


def markdown_to_html(text: str) -> Markup:
    """Convert Markdown text to safe HTML."""
    return Markup(markdown(text or ""))

