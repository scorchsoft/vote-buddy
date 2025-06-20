from unittest.mock import patch
import pytest
from flask_login import AnonymousUserMixin
from flask import render_template

from app import create_app
from app.extensions import db
from app.models import AppSetting, Role, Permission, User
from app.admin.routes import manage_settings


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def _make_user(has_permission: bool):
    perm = Permission(name='manage_settings') if has_permission else None
    role = Role(permissions=[perm] if perm else [])
    user = User(role=role)
    user.email = 'admin@example.com'
    user.is_active = True
    return user


def test_manage_settings_permission_required():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context('/admin/settings'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                manage_settings()
        with app.test_request_context('/admin/settings'):
            user = _make_user(False)
            with patch('flask_login.utils._get_user', return_value=user):
                with pytest.raises(Exception):
                    manage_settings()


def test_site_title_used_in_template():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        AppSetting.set('site_title', 'My Vote')
        anon = AnonymousUserMixin()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                assert '<title>My Vote</title>' in html
