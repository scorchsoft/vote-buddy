import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from unittest.mock import patch
import pytest
from werkzeug.exceptions import Forbidden

from app.models import Role, User, Permission
from app.admin.forms import UserCreateForm, RoleForm
from app.admin.routes import _save_user, _save_role, list_roles


def test_save_user_creates_record():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        role = Role(name='Admin')
        db.session.add(role)
        db.session.commit()

        with app.test_request_context('/'):
            form = UserCreateForm(meta={'csrf': False})
            form.email.data = 'new@example.com'
            form.password.data = 'secret'
            form.role_id.data = role.id
            form.is_active.data = True

            user = _save_user(form)
            assert user.id == 1
            assert user.email == 'new@example.com'
            assert user.role_id == role.id
            assert user.check_password('secret')
            assert User.query.count() == 1


def test_save_role_creates_record():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        perm = Permission(name='manage_users')
        db.session.add(perm)
        db.session.commit()

        with app.test_request_context('/'):
            form = RoleForm(meta={'csrf': False})
            form.name.data = 'Coordinator'
            form.permission_ids.data = [perm.id]

            role = _save_role(form)
            assert role.id == 1
            assert role.name == 'Coordinator'
            assert role.permissions[0].id == perm.id
            assert Role.query.count() == 1


def _make_user(has_permission: bool):
    perm = Permission(name='manage_users') if has_permission else None
    role = Role(permissions=[perm] if perm else [])
    user = User(role=role)
    user.is_active = True
    return user


def test_list_roles_requires_permission():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_request_context('/admin/roles'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                list_roles()

        with app.test_request_context('/admin/roles'):
            user = _make_user(False)
            with patch('flask_login.utils._get_user', return_value=user):
                with pytest.raises(Forbidden):
                    list_roles()
