from flask import Blueprint, render_template

bp = Blueprint('meetings', __name__, url_prefix='/meetings')

@bp.route('/')
def list_meetings():
    return render_template('meetings/list.html')
