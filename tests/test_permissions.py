import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from werkzeug.exceptions import Forbidden
from flask import abort
from app import create_app
from unittest.mock import patch
from flask_login import AnonymousUserMixin

from app.permissions import permission_required
from app.models import User, Role, Permission


@permission_required('view_dashboard')
def _protected():
    return 'ok'


def test_permission_required_allows_when_has_permission():
    perm = Permission(name='view_dashboard')
    user = User(role=Role(permissions=[perm]))
    user.is_active = True
    with patch('flask_login.utils._get_user', return_value=user):
        assert _protected() == 'ok'


def test_permission_required_forbidden_when_missing():
    user = User(role=Role(permissions=[]))
    user.is_active = True
    with patch('flask_login.utils._get_user', return_value=user):
        with pytest.raises(Forbidden):
            _protected()


def test_permission_required_forbidden_when_anonymous():
    anon = AnonymousUserMixin()
    with patch('flask_login.utils._get_user', return_value=anon):
        with pytest.raises(Forbidden):
            _protected()


def test_403_template_loads():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    @app.route('/deny')
    def deny():
        abort(403)

    client = app.test_client()
    response = client.get('/deny')
    assert response.status_code == 403
    assert b'Access Denied' in response.data
