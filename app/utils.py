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
import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from uuid import uuid4


def hash_for_log(value: str) -> str:
    """Return abbreviated SHA-256 hash of value for logging."""
    if not value:
        return ""
    salt = current_app.config.get("TOKEN_SALT", "")
    digest = hashlib.sha256(f"{value}{salt}".encode()).hexdigest()
    return digest[:8]


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


def format_dt(dt: datetime, tz_name: str | None = None) -> str:
    """Return formatted datetime with timezone abbreviation.

    Parameters
    ----------
    dt: datetime
        Naive or aware datetime object.
    tz_name: str | None
        Optional timezone name; defaults to ``app.config['TIMEZONE']`` or ``UTC``.
    """

    if dt is None:
        return ""
    tz_name = tz_name or current_app.config.get("TIMEZONE", "UTC")
    tz = ZoneInfo(tz_name)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M %Z")



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


def generate_results_pdf(meeting, stage1_results, stage2_results) -> bytes:
    """Return PDF bytes summarising Stage 1 and Stage 2 results."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
    import io

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"{meeting.title} - Final Results", styles["Title"]), Spacer(1, 12)]

    # Stage 1 table
    story.append(Paragraph("Stage 1 Amendments", styles["Heading2"]))
    data = [["Amendment", "For", "Against", "Abstain"]]
    for amend, counts in stage1_results:
        text = getattr(amend, "text_md", "") or ""
        data.append([
            text,
            counts.get("for", 0),
            counts.get("against", 0),
            counts.get("abstain", 0),
        ])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.extend([table, Spacer(1, 24)])

    # Stage 2 table
    story.append(Paragraph("Stage 2 Motions", styles["Heading2"]))
    data2 = [["Motion", "For", "Against", "Abstain", "Outcome"]]
    for motion, counts in stage2_results:
        title = getattr(motion, "title", "") or ""
        data2.append([
            title,
            counts.get("for", 0),
            counts.get("against", 0),
            counts.get("abstain", 0),
            (getattr(motion, "status", "?") or "?").capitalize(),
        ])
    table2 = Table(data2, repeatRows=1)
    table2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.append(table2)

    doc.build(story)
    return buf.getvalue()
