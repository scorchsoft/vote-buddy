import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Meeting, Motion, Member, SubmissionToken


def setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TOKEN_SALT'] = 's'
    return app


def test_submit_pages_load():
    app = setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='T')
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Alice', email='a@example.com')
        db.session.add(member)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M', text_md='t', category='motion', threshold='normal', ordering=1, is_published=True)
        db.session.add(motion)
        db.session.commit()
        token_obj, plain = SubmissionToken.create(member.id, meeting.id, 's')
        db.session.commit()
        meeting_id = meeting.id
        motion_id = motion.id
        member_id = member.id
    client = app.test_client()
    resp = client.get(f'/submit/{plain}/motion/{meeting_id}')
    assert resp.status_code == 200
    with app.app_context():
        token_obj2, plain2 = SubmissionToken.create(member_id, meeting_id, 's')
        db.session.commit()
    resp = client.get(f'/submit/{plain2}/amendment/{motion_id}')
    assert resp.status_code == 200
