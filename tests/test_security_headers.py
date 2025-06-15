import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


def test_csp_header_present():
    app = create_app()
    with app.test_client() as client:
        resp = client.get('/')
        assert resp.headers.get('Content-Security-Policy') == (
            "default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' https://unpkg.com"
        )

