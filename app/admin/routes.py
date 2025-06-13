from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
def dashboard():
    return render_template('admin/dashboard.html')
