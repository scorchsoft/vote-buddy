import sys, os; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models import User, Role, Permission


def test_set_password_and_check():
    user = User()
    user.set_password('secret')
    assert user.password_hash != 'secret'
    assert user.check_password('secret') is True
    assert user.check_password('wrong') is False


def test_has_permission():
    perm_view = Permission(name='view_dashboard')
    role = Role(permissions=[perm_view])
    user = User(role=role)

    assert user.has_permission('view_dashboard') is True
    assert user.has_permission('manage_users') is False

