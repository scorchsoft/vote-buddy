from flask import Blueprint, render_template

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html')
