from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from ..extensions import db
from ..models import Meeting, User, Role
from .forms import UserForm, UserCreateForm

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


def _save_user(form: UserForm, user: User | None = None) -> User:
    """Populate User from form and persist."""
    if user is None:
        user = User()

    user.email = form.email.data
    user.role_id = form.role_id.data
    user.is_active = form.is_active.data
    if form.password.data:
        user.set_password(form.password.data)

    db.session.add(user)
    db.session.commit()
    return user


@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def create_user():
    form = UserCreateForm()
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name)]
    if form.validate_on_submit():
        _save_user(form)
        return redirect(url_for('admin.list_users'))
    return render_template('admin/user_form.html', form=form, user=None)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name)]
    if form.validate_on_submit():
        _save_user(form, user)
        return redirect(url_for('admin.list_users'))
    return render_template('admin/user_form.html', form=form, user=user)
