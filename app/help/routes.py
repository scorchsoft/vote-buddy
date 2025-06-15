from flask import Blueprint, render_template, current_app
from markupsafe import Markup
from pathlib import Path
import markdown

bp = Blueprint('help', __name__)

@bp.route('/help')
def show_help():
    docs_path = Path(current_app.root_path).parent / 'docs' / 'help-voting.md'
    with open(docs_path, 'r', encoding='utf-8') as f:
        content_md = f.read()
    html_content = Markup(markdown.markdown(content_md))
    return render_template('help/help.html', content=html_content)
