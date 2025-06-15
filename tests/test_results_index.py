import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import render_template, url_for
from app import create_app
from app.extensions import db
from app.models import Meeting
from app import routes as main


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_results_index_lists_public_only():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        pub = Meeting(title='Public', public_results=True)
        priv = Meeting(title='Private', public_results=False)
        db.session.add_all([pub, priv])
        db.session.commit()
        with app.test_request_context('/results'):
            html = main.results_index()
            assert 'Public' in html
            assert 'Private' not in html


def test_nav_link_points_to_results_index():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context('/'):
            html = render_template('index.html')
            href = url_for('main.results_index')
            assert href in html

