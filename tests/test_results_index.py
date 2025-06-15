import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Meeting
from app import routes as main


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_results_index_lists_only_public():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        m1 = Meeting(title='AGM', public_results=True)
        m2 = Meeting(title='EGM', public_results=False)
        db.session.add_all([m1, m2])
        db.session.commit()
        with app.test_request_context('/results'):
            html = main.results_index()
            assert 'AGM' in html
            assert 'EGM' not in html
