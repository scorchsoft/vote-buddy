import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db, mail
from app.models import User, PasswordResetToken, Role
from app.services.email import send_password_reset


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['MAIL_SUPPRESS_SEND'] = True
    app.config['TOKEN_SALT'] = 's'
    app.config['PASSWORD_RESET_EXPIRY_HOURS'] = 24
    return app


def test_send_password_reset_includes_link():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        user = User(email='a@example.com')
        db.session.add(user)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_password_reset(user, 'abc123', test_mode=False)
                mock_send.assert_called_once()
                msg = mock_send.call_args[0][0]
                assert '/auth/reset/abc123' in msg.body


def test_request_reset_creates_token_and_sends_email():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        role = Role(name='Admin')
        db.session.add(role)
        user = User(email='user@example.com', role=role, is_active=True)
        user.set_password('old')
        db.session.add(user)
        db.session.commit()
    client = app.test_client()
    with app.app_context():
        with patch.object(mail, 'send') as mock_send:
            resp = client.post('/auth/request-reset', data={'email': 'user@example.com'}, follow_redirects=False)
            assert resp.status_code == 302
            assert PasswordResetToken.query.count() == 1
            mock_send.assert_called_once()


def test_reset_password_updates_user():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        user = User(email='reset@example.com', is_active=True)
        user.set_password('oldpass')
        db.session.add(user)
        db.session.flush()
        user_id = user.id
        token_obj, plain = PasswordResetToken.create(
            user_id=user_id, salt=app.config['TOKEN_SALT']
        )
        db.session.commit()

    client = app.test_client()
    resp = client.post(f'/auth/reset/{plain}', data={'password': 'newpass'}, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        user_db = db.session.get(User, user_id)
        token_db = PasswordResetToken.verify(plain, app.config['TOKEN_SALT'])
        assert user_db.check_password('newpass')
        assert token_db.used_at is not None


def test_expired_token_is_rejected():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        user = User(email='expire@example.com', is_active=True)
        user.set_password('old')
        db.session.add(user)
        db.session.flush()
        token_obj, plain = PasswordResetToken.create(
            user_id=user.id, salt=app.config['TOKEN_SALT']
        )
        token_obj.created_at = datetime.utcnow() - timedelta(hours=25)
        db.session.commit()

    client = app.test_client()
    resp = client.get(f'/auth/reset/{plain}', follow_redirects=True)
    assert b'Reset link expired' in resp.data
