import os, sys
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from werkzeug.exceptions import Forbidden
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import (
    Meeting,
    Member,
    VoteToken,
    Amendment,
    Motion,
    Vote,
    Role,
    Permission,
    User,
)
from app.ro import routes as ro


def _make_user():
    perm = Permission(name='manage_meetings')
    role = Role(permissions=[perm])
    user = User(role=role)
    user.is_active = True
    return user


def test_stage1_vote_count_helper():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM', quorum=2)
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.flush()
        token = VoteToken(token='t1', member_id=member.id, stage=1, used_at=datetime.utcnow())
        db.session.add(token)
        db.session.commit()
        assert ro._stage1_vote_count(meeting) == 1


def test_download_tallies_csv():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='T', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A', order=1)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.flush()
        Vote.record(member_id=member.id, amendment_id=amend.id, choice='for', salt='s')
        Vote.record(member_id=member.id, motion_id=motion.id, choice='against', salt='s')
        user = _make_user()
        with app.test_request_context(f'/ro/{meeting.id}/tallies.csv'):
            with patch('flask_login.utils._get_user', return_value=user):
                resp = ro.download_tallies(meeting.id)
                assert resp.status_code == 200
                assert b'amendment' in resp.data


def test_download_audit_log_csv():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title='M1',
            text_md='T',
            category='motion',
            threshold='normal',
            ordering=1,
        )
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A', order=1)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.flush()
        Vote.record(member_id=member.id, amendment_id=amend.id, choice='for', salt='s')
        Vote.record(member_id=member.id, motion_id=motion.id, choice='against', salt='s')
        user = _make_user()
        with app.test_request_context(f'/ro/{meeting.id}/audit_log.csv'):
            with patch('flask_login.utils._get_user', return_value=user):
                resp = ro.download_audit_log(meeting.id)
                assert resp.status_code == 200
                assert b'member_id' in resp.data

def test_dashboard_requires_permission():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.commit()
        user = User(role=Role(permissions=[]))
        user.is_active = True
        with app.test_request_context('/ro/'):
            with patch('flask_login.utils._get_user', return_value=user):
                try:
                    ro.dashboard()
                except Exception as exc:
                    assert isinstance(exc, Forbidden)
                else:
                    assert False, 'expected Forbidden'


def test_ro_dashboard_displays_countdown():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 6
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='AGM', closes_at_stage1=now + timedelta(hours=8))
        db.session.add(meeting)

def test_dashboard_shows_quorum_percentage():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(
            title='AGM',
            quorum=2,
            closes_at_stage1=datetime.utcnow().replace(microsecond=0) + timedelta(hours=1),
        )
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.flush()
        token = VoteToken(token='t1', member_id=member.id, stage=1, used_at=datetime.utcnow())
        db.session.add(token)
        db.session.commit()
        user = _make_user()
        with app.test_request_context('/ro/'):
            with patch('flask_login.utils._get_user', return_value=user):
                html = ro.dashboard()
                assert 'Next Reminder' in html
                # Default reminder config results in 0h when the meeting closes in 1 hour
                assert '0h' in html
                assert '50.0%' in html

