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
