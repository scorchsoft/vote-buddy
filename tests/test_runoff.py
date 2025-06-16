from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Meeting,
    Motion,
    Amendment,
    AmendmentConflict,
    Member,
    Runoff,
    VoteToken,
    Vote,
)
from app.services import runoff as ro


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
        assert VoteToken.query.filter_by(member_id=member.id, stage=1).count() == 1


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
        assert VoteToken.query.count() == 0


def test_close_stage1_tie_resolved_by_chair():
    app = _setup()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
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

        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        # tie votes on both amendments
        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a1.id, choice='against', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='against', salt='s')

        a1.status = 'carried'
        a1.tie_break_method = 'chair'
        db.session.commit()

        ro.close_stage1(meeting)

        assert a1.status == 'carried'
        assert a1.tie_break_method == 'chair'
        assert a2.status == 'failed'
        assert a2.tie_break_method == 'order'


def test_close_stage1_tie_resolved_by_order():
    app = _setup()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
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

        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a1.id, choice='against', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='against', salt='s')

        ro.close_stage1(meeting)

        assert a1.status == 'carried'
        assert a1.tie_break_method == 'order'
        assert a2.status == 'failed'
        assert a2.tie_break_method == 'order'
