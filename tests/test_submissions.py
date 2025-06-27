import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Meeting, Motion, Member, MotionSubmission, SubmissionToken


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

def test_preview_token_allows_submission():
    app = setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='T')
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='A', email='a@x.com')
        db.session.add(member)
        motion = Motion(meeting_id=meeting.id, title='M', text_md='t', category='motion', threshold='normal', ordering=1, is_published=True)
        db.session.add(motion)
        db.session.commit()
        meeting_id = meeting.id
    client = app.test_client()
    resp = client.get(f'/submit/preview/motion/{meeting_id}')
    assert resp.status_code == 200


def test_motion_submission_appends_preferences():
    app = setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='T')
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='A', email='a@x.com')
        db.session.add(member)
        db.session.flush()
        token_obj, plain = SubmissionToken.create(member.id, meeting.id, 's')
        db.session.commit()
        meeting_id = meeting.id
    client = app.test_client()
    data = {
        'name': 'A',
        'email': 'a@x.com',
        'title': 'M',
        'text_md': 'Text',
        'seconder_member_number': '1',
        'seconder_name': 'X',
        'allow_clerical': 'y',
        'allow_move': 'y',
    }
    resp = client.post(f'/submit/{plain}/motion/{meeting_id}', data=data)
    assert resp.status_code == 200
    with app.app_context():
        sub = MotionSubmission.query.first()
        assert 'Motion Handling Preferences' in sub.text_md
        assert 'The Board may correct typographical or numbering errors with no change to meaning.' in sub.text_md
        assert 'The Board may place this change in the Articles or Bylaws as most appropriate.' in sub.text_md
