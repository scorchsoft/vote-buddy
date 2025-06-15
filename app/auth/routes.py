from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user

from ..models import User
from .utils import is_safe_url

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        next_page = request.form.get('next') or next_page
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            destination = next_page if is_safe_url(next_page) else url_for('admin.dashboard')
            return redirect(destination)
        flash('Invalid credentials')
    return render_template('auth/login.html', next=next_page)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
