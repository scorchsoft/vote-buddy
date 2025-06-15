import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import User


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

