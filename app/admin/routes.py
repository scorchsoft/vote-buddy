from flask import Blueprint, render_template, request
from flask_login import login_required
from ..models import Meeting, User

from ..permissions import permission_required

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@login_required
@permission_required('view_dashboard')
def dashboard():
    meetings = Meeting.query.all()
    return render_template('admin/dashboard.html', meetings=meetings)


@bp.route('/users')
@login_required
@permission_required('manage_users')
def list_users():
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'email')
    direction = request.args.get('direction', 'asc')

    query = User.query
    if q:
        search = f"%{q}%"
        query = query.filter(User.email.ilike(search))

    if sort == 'created_at':
        order_attr = User.created_at
    else:
        order_attr = User.email
    query = query.order_by(
        order_attr.asc() if direction == 'asc' else order_attr.desc()
    )

    users = query.all()

    template = (
        'admin/_user_rows.html' if request.headers.get('HX-Request')
        else 'admin/users.html'
    )
    return render_template(
        template,
        users=users,
        q=q,
        sort=sort,
        direction=direction,
    )
