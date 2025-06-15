from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Meeting,
    Motion,
    Amendment,
    AmendmentConflict,
    Member,
    VoteToken,
    Runoff,
    Vote,
)
from app.services import runoff as ro
from app.meetings import routes as meetings
from tests.test_meetings_routes import _make_user
from unittest.mock import patch


def _setup():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['RUNOFF_EXTENSION_MINUTES'] = 60  # 1 hour for test
    return app


def test_close_stage1_creates_runoff_and_extends_stage2():
    app = _setup()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            opens_at_stage1=now,
            closes_at_stage1=now,
            opens_at_stage2=now,
            closes_at_stage2=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        db.session.flush()

        motion = Motion(
            meeting_id=meeting.id,
            title='M',
            text_md='x',
            category='motion',
            threshold='normal',
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1)
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2)
        db.session.add_all([a1, a2])
        db.session.flush()

        db.session.add(AmendmentConflict(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id))
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')

        ro.close_stage1(meeting)

        assert Runoff.query.count() == 1
        assert meeting.opens_at_stage2 == now + timedelta(minutes=60)
        assert meeting.closes_at_stage2 == now + timedelta(hours=1) + timedelta(minutes=60)


def test_close_stage1_no_runoff_no_extension():
    app = _setup()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            opens_at_stage1=now,
            closes_at_stage1=now,
            opens_at_stage2=now,
            closes_at_stage2=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        db.session.flush()

        motion = Motion(
            meeting_id=meeting.id,
            title='M',
            text_md='x',
            category='motion',
            threshold='normal',
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1)
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2)
        db.session.add_all([a1, a2])
        db.session.flush()

        db.session.add(AmendmentConflict(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id))
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='against', salt='s')

        ro.close_stage1(meeting)

        assert Runoff.query.count() == 0
        assert meeting.opens_at_stage2 == now
        assert meeting.closes_at_stage2 == now + timedelta(hours=1)


def test_close_stage1_route_creates_runoff_and_extends_stage1():
    app = _setup()
    app.config['MAIL_SUPPRESS_SEND'] = True
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            opens_at_stage1=now,
            closes_at_stage1=now,
            opens_at_stage2=now,
            closes_at_stage2=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        db.session.flush()

        motion = Motion(
            meeting_id=meeting.id,
            title='M',
            text_md='x',
            category='motion',
            threshold='normal',
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1)
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2)
        db.session.add_all([a1, a2])
        db.session.flush()

        db.session.add(AmendmentConflict(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id))
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')

        with app.test_request_context(f'/meetings/{meeting.id}/close-stage1', method='POST'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('app.meetings.routes.send_stage2_invite') as mock_send:
                    meetings.close_stage1(meeting.id)
                    assert mock_send.call_count == 0

        assert Runoff.query.count() == 1
        assert meeting.opens_at_stage2 == now + timedelta(minutes=60)
        assert meeting.closes_at_stage2 == now + timedelta(hours=1) + timedelta(minutes=60)
        assert VoteToken.query.filter_by(stage=2).count() == 0
