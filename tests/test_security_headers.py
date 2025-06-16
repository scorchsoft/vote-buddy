import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_csp_header_present():
    app = _setup_app()
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        resp = client.get('/')
        assert resp.headers.get('Content-Security-Policy') == (
            "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' https://unpkg.com"
        )

