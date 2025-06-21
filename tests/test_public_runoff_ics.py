import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import pytest
from werkzeug.exceptions import NotFound

from app import create_app
from app.extensions import db
from app.models import Meeting
from app import routes as main


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_public_runoff_ics_downloads_when_timestamps_set():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            runoff_opens_at=now,
            runoff_closes_at=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        db.session.commit()
        with app.test_request_context(f'/public/meetings/{meeting.id}/runoff.ics'):
            resp = main.public_runoff_ics(meeting.id)
            assert resp.mimetype == 'text/calendar'
            cd = resp.headers['Content-Disposition']
            assert 'runoff.ics' in cd


def test_public_runoff_ics_missing_timestamps_returns_404():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.commit()
        with app.test_request_context(f'/public/meetings/{meeting.id}/runoff.ics'):
            with pytest.raises(NotFound):
                main.public_runoff_ics(meeting.id)
