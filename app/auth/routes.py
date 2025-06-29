from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_user, logout_user
from ..extensions import limiter, db

from ..models import User, PasswordResetToken
from ..services.email import send_password_reset
from datetime import datetime, timedelta
from .utils import is_safe_url

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def login():
    next_page = request.args.get('next')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        next_page = request.form.get('next') or next_page
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully', 'success')
            destination = next_page if is_safe_url(next_page) else url_for('admin.dashboard')
            return redirect(destination)
        flash('Invalid credentials', 'error')
    return render_template('auth/login.html', next=next_page)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/request-reset', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def request_reset():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.is_active:
            token_obj, plain = PasswordResetToken.create(
                user_id=user.id, salt=current_app.config["TOKEN_SALT"]
            )
            db.session.commit()
            send_password_reset(user, plain)
        flash('If that email exists, you\'ll receive a reset link shortly.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/request_reset.html')


@bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    prt = PasswordResetToken.verify(token, current_app.config["TOKEN_SALT"])
    if prt is None:
        abort(404)
    if prt.used_at:
        flash('Reset link already used', 'error')
        return redirect(url_for('auth.login'))
    expiry_hours = current_app.config.get("PASSWORD_RESET_EXPIRY_HOURS", 24)
    if datetime.utcnow() - prt.created_at > timedelta(hours=expiry_hours):
        flash('Reset link expired', 'error')
        return redirect(url_for('auth.request_reset'))
    if request.method == 'POST':
        password = request.form.get('password')
        if password:
            user = db.session.get(User, prt.user_id)
            user.set_password(password)
            prt.used_at = datetime.utcnow()
            db.session.commit()
            flash('Password updated, please log in.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_form.html')
