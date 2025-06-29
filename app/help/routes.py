from flask import Blueprint, render_template, current_app
from pathlib import Path

from app.utils import markdown_to_html

bp = Blueprint('help', __name__)

@bp.route('/help')
def show_help():
    docs_path = Path(current_app.root_path).parent / 'docs' / 'help-voting.md'
    with open(docs_path, 'r', encoding='utf-8') as f:
        content_md = f.read()
    html_content = markdown_to_html(content_md)
    return render_template('help/help.html', content=html_content)
