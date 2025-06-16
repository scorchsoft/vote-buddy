from markdown import markdown
from markupsafe import Markup
from flask import current_app
from .models import AppSetting
import json


def config_or_setting(
    config_key: str,
    default=None,
    db_key: str | None = None,
    parser=None,
) -> any:
    """Return value from AppSetting falling back to app.config.

    Parameters
    ----------
    config_key: str
        The name of the Flask config variable.
    default: any
        Default if neither setting nor config provides a value.
    db_key: str | None
        Key used in ``AppSetting`` table; defaults to ``config_key`` in
        lower-case.
    parser: callable | None
        Optional function to convert the stored value.
    """

    key = db_key or config_key.lower()
    value = AppSetting.get(key)
    if value is None:
        value = current_app.config.get(config_key, default)
    if parser:
        try:
            value = parser(value)
        except Exception:
            value = default
    return value


def markdown_to_html(text: str) -> Markup:
    """Convert Markdown text to safe HTML."""
    return Markup(markdown(text or ""))

