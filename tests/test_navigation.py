import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from flask import render_template
import re
from flask_login import AnonymousUserMixin

from app import create_app
from app.extensions import db
from app.models import User, Role


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_nav_shows_user_email_and_role():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        role = Role(name='Admin')
        db.session.add(role)
        db.session.commit()
        user = User(email='alice@example.com', role=role)
        user.is_active = True
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=user):
                html = render_template('base.html')
                assert 'alice@example.com' in html
                assert '<span class="bp-badge bp-badge-secondary">Admin</span>' in html
                assert 'Dashboard' in html
                assert 'Logout' in html


def test_nav_shows_login_when_anonymous():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        anon = AnonymousUserMixin()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                assert 'href="/auth/login"' in html
                assert 'Dashboard' not in html


def test_nav_highlights_current_page():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        anon = AnonymousUserMixin()
        with app.test_request_context('/meetings/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                assert re.search(r'<a[^>]*href="/meetings/"[^>]*aria-current="page"', html)
