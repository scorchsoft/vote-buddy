from markdown import markdown
from markupsafe import Markup
import bleach

ALLOWED_TAGS = (
    bleach.sanitizer.ALLOWED_TAGS
    | {
        'p',
        'pre',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'br',
    }
)
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
    raw_html = markdown(text or "")
    cleaned = bleach.clean(raw_html, tags=ALLOWED_TAGS, strip=True)
    return Markup(cleaned)

from uuid import uuid4
from datetime import datetime


def generate_stage_ics(meeting, stage: int) -> bytes:
    """Return ICS file bytes for the given meeting stage."""
    if stage == 1:
        start = meeting.opens_at_stage1
        end = meeting.closes_at_stage1
    else:
        start = meeting.opens_at_stage2
        end = meeting.closes_at_stage2

    if not start or not end:
        raise ValueError("Stage timestamps not set")

    def fmt(dt: datetime) -> str:
        return dt.strftime('%Y%m%dT%H%M%SZ')

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//VoteBuddy//EN",
        "BEGIN:VEVENT",
        f"UID:{uuid4()}",
        f"DTSTAMP:{fmt(datetime.utcnow())}",
        f"DTSTART:{fmt(start)}",
        f"DTEND:{fmt(end)}",
        f"SUMMARY:{meeting.title} - Stage {stage} Voting",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines).encode("utf-8")
