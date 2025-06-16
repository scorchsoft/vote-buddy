import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils import markdown_to_html
from markupsafe import Markup


def test_markdown_to_html_sanitizes_and_marks_safe():
    md = '# Title\n<script>alert(1)</script>'
    html = markdown_to_html(md)
    assert '<script>' not in html
    assert '<h1>' in html
    assert isinstance(html, Markup)
from dataclasses import dataclass
from datetime import datetime
import pytest
from app.utils import generate_stage_ics


@dataclass
class DummyMeeting:
    title: str
    opens_at_stage1: datetime | None = None
    closes_at_stage1: datetime | None = None
    opens_at_stage2: datetime | None = None
    closes_at_stage2: datetime | None = None


def test_generate_stage1_ics_contains_calendar_and_title():
    meeting = DummyMeeting(
        title="Test Meeting",
        opens_at_stage1=datetime(2030, 1, 1, 9),
        closes_at_stage1=datetime(2030, 1, 1, 10),
    )
    ics = generate_stage_ics(meeting, 1)
    text = ics.decode()
    assert "BEGIN:VCALENDAR" in text
    assert "Test Meeting" in text


def test_generate_stage2_ics_contains_calendar_and_title():
    meeting = DummyMeeting(
        title="Test Meeting",
        opens_at_stage2=datetime(2030, 1, 2, 9),
        closes_at_stage2=datetime(2030, 1, 2, 10),
    )
    ics = generate_stage_ics(meeting, 2)
    text = ics.decode()
    assert "BEGIN:VCALENDAR" in text
    assert "Test Meeting" in text


def test_generate_stage_ics_missing_timestamps_raises_error():
    meeting = DummyMeeting(title="Broken")
    with pytest.raises(ValueError):
        generate_stage_ics(meeting, 2)

