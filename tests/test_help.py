import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_help_page_loads():
    app = _setup_app()
    with app.app_context():
        db.create_all()
    client = app.test_client()
    resp = client.get('/help')
    assert resp.status_code == 200
    assert b'Voting Help' in resp.data


def test_help_page_strips_script_tags():
    app = _setup_app()
    with app.app_context():
        db.create_all()
    client = app.test_client()
    malicious_md = '# Title\n<script>alert(1)</script>'
    from unittest.mock import mock_open, patch
    with patch('app.help.routes.open', mock_open(read_data=malicious_md), create=True):
        resp = client.get('/help')
    assert b'<script>' not in resp.data

