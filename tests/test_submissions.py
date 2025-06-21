import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Meeting, Motion


def setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_submit_pages_load():
    app = setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='T')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M', text_md='t', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        db.session.commit()
    client = app.test_client()
    resp = client.get(f'/submit/motion/{meeting.id}')
    assert resp.status_code == 200
    resp = client.get(f'/submit/amendment/{motion.id}')
    assert resp.status_code == 200
