from flask import Blueprint, render_template
from flask_login import login_required
from ..models import User
from ..permissions import permission_required

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
@permission_required('view_dashboard')
def dashboard():
    return render_template('admin/dashboard.html')


@bp.route('/users')
@login_required
@permission_required('manage_users')
def list_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)
