import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import User
from app.auth.utils import is_safe_url


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_login_ignores_external_next_url():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        user = User(email='foo@example.com')
        user.set_password('secret')
        user.is_active = True
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    resp = client.post('/auth/login?next=http://evil.com', data={
        'email': 'foo@example.com',
        'password': 'secret'
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/admin/')


def test_is_safe_url_valid_cases():
    assert is_safe_url('/admin/')
    assert is_safe_url('login')
    assert is_safe_url('https:/admin')


def test_is_safe_url_rejects_dangerous():
    assert not is_safe_url('javascript:alert(1)')
    assert not is_safe_url('http://evil.com')

