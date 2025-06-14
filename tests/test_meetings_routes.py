import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from werkzeug.exceptions import Forbidden

from app import create_app
from app.extensions import db
from app.models import User, Role, Permission
from app.meetings import routes as meetings


def _make_user(has_permission: bool):
    perm = Permission(name='manage_meetings') if has_permission else None
    role = Role(permissions=[perm] if perm else [])
    user = User(role=role)
    user.is_active = True
    return user


def test_list_meetings_requires_permission():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_request_context('/meetings/'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                meetings.list_meetings()

        with app.test_request_context('/meetings/'):
            user = _make_user(False)
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('flask.flash'):
                    try:
                        meetings.list_meetings()
                    except Forbidden:
                        pass
                    else:
                        assert False, 'expected Forbidden'
