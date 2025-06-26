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
        csp_header = resp.headers.get('Content-Security-Policy')
        # Check that the CSP contains the expected directives (nonce will be dynamic)
        assert "default-src 'self'" in csp_header
        assert "script-src 'self' https://unpkg.com 'nonce-" in csp_header
        assert "style-src 'self' https://unpkg.com 'unsafe-inline'" in csp_header
        assert "font-src 'self' https://unpkg.com" in csp_header
        assert "img-src 'self' data:" in csp_header
        assert "connect-src 'self'" in csp_header

