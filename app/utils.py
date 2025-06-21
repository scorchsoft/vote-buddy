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
from .models import AppSetting, Amendment
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


def generate_runoff_ics(meeting) -> bytes:
    """Return ICS file bytes for the run-off stage."""
    start = meeting.runoff_opens_at
    end = meeting.runoff_closes_at
    if not start or not end:
        raise ValueError("Run-off timestamps not set")

    def fmt(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//VoteBuddy//EN",
        "BEGIN:VEVENT",
        f"UID:{uuid4()}",
        f"DTSTAMP:{fmt(datetime.utcnow())}",
        f"DTSTART:{fmt(start)}",
        f"DTEND:{fmt(end)}",
        f"SUMMARY:{meeting.title} - Run-off Voting",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines).encode("utf-8")


def carried_amendment_summary(meeting: "Meeting", char_limit: int = 80) -> str | None:
    """Return Markdown bullet list summarising carried amendments.

    Each amendment text is truncated to ``char_limit`` characters.
    Returns ``None`` if no amendments were carried.
    """
    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id, status="carried")
        .order_by(Amendment.order)
        .all()
    )
    if not amendments:
        return None
    lines = []
    for amend in amendments:
        text = (amend.text_md or "").strip()
        if len(text) > char_limit:
            text = text[:char_limit].rstrip() + "..."
        lines.append(f"* {text}")
    return "\n".join(lines)


def motion_results_summary(meeting: "Meeting") -> str:
    """Return Markdown bullet list summarising motion outcomes."""
    from .models import Motion

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    lines = []
    for motion in motions:
        status = (motion.status or "?").capitalize()
        lines.append(f"* {motion.title}: {status}")
    return "\n".join(lines)
