import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db


def test_404_template_loads():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
    client = app.test_client()
    resp = client.get('/does-not-exist')
    assert resp.status_code == 404
    assert b'Page Not Found' in resp.data


def test_failed_login_shows_flash_message():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
    client = app.test_client()
    resp = client.post('/auth/login', data={
        'email': 'bad@example.com',
        'password': 'wrong'
    }, follow_redirects=True)
    assert b'Invalid credentials' in resp.data


def test_500_handler_renders_template():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['PROPAGATE_EXCEPTIONS'] = False
    with app.app_context():
        db.create_all()

        @app.route('/trigger-error')
        def trigger_error():
            raise Exception('boom')

    client = app.test_client()
    resp = client.get('/trigger-error')
    assert resp.status_code == 500
    assert b'Server Error' in resp.data
