from app import create_app
from app.extensions import db
from unittest.mock import patch
import pytest
from werkzeug.exceptions import Forbidden
from flask import url_for

from app.models import Permission, Role, User
from app.admin.forms import PermissionForm
from app.admin import routes as admin
from app.admin.routes import _save_permission, list_permissions


def test_save_permission_creates_record():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_request_context('/'):
            form = PermissionForm(meta={'csrf': False})
            form.name.data = 'manage_permissions'
            perm = _save_permission(form)
            assert perm.id == 1
            assert perm.name == 'manage_permissions'
            assert Permission.query.count() == 1


def _make_user(has_permission: bool):
    perm = Permission(name='manage_users') if has_permission else None
    role = Role(permissions=[perm] if perm else [])
    user = User(role=role)
    user.email = 'admin@example.com'
    user.is_active = True
    return user


def test_list_permissions_requires_permission():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_request_context('/admin/permissions'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                list_permissions()

        with app.test_request_context('/admin/permissions'):
            user = _make_user(False)
            with patch('flask_login.utils._get_user', return_value=user):
                with pytest.raises(Forbidden):
                    list_permissions()


def test_list_permissions_contains_create_and_edit_links():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        perm = Permission(name='view_dashboard')
        db.session.add(perm)
        db.session.commit()
        admin_perm = Permission(name='manage_users')
        role = Role(name='Admin', permissions=[admin_perm])
        db.session.add_all([admin_perm, role])
        db.session.commit()

        with app.test_request_context('/admin/permissions'):
            admin_user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=admin_user):
                html = admin.list_permissions()
                assert url_for('admin.create_permission') in html
                assert url_for('admin.edit_permission', permission_id=perm.id) in html

