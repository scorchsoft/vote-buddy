import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Role, User
from app.admin.forms import UserCreateForm
from app.admin.routes import _save_user


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
