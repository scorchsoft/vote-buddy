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
    AppSetting,
)
from app.services import runoff as ro
from app.voting import routes as voting
from unittest.mock import patch
import json


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

        with patch("app.services.runoff.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now
            ro.close_stage1(meeting)

        assert Runoff.query.count() == 1
        assert meeting.runoff_opens_at == now
        assert meeting.runoff_closes_at == now + timedelta(minutes=60)
        assert meeting.opens_at_stage2 == now + timedelta(minutes=60)
        assert meeting.closes_at_stage2 == now + timedelta(hours=1) + timedelta(minutes=60)
        assert VoteToken.query.filter_by(member_id=member.id, stage=1).count() == 1


def test_close_stage1_sets_closes_after_open_when_previous_close_none():
    app = _setup()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            opens_at_stage1=now,
            closes_at_stage1=now,
            opens_at_stage2=now,
            closes_at_stage2=None,
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

        with patch("app.services.runoff.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now
            ro.close_stage1(meeting)

        assert Runoff.query.count() == 1
        expect_open = now + timedelta(minutes=60)
        expect_close = expect_open + timedelta(minutes=60)
        assert meeting.runoff_opens_at == now
        assert meeting.runoff_closes_at == now + timedelta(minutes=60)
        assert meeting.opens_at_stage2 == expect_open
        assert meeting.closes_at_stage2 == expect_close


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

        with patch("app.services.runoff.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now
            ro.close_stage1(meeting)

        assert Runoff.query.count() == 0
        assert meeting.runoff_opens_at is None
        assert meeting.runoff_closes_at is None
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


def test_close_stage1_tie_from_setting():
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

        AppSetting.set('tie_break_decisions', json.dumps({str(a1.id): {'result': 'carried', 'method': 'chair'}}))

        ro.close_stage1(meeting)

        assert a1.status == 'carried'
        assert a1.tie_break_method == 'chair'
        assert a2.status == 'failed'
        assert a2.tie_break_method == 'order'


def test_close_runoff_stage_updates_amendments_and_tokens():
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

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='carried')
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2, status='carried')
        db.session.add_all([a1, a2])
        db.session.flush()

        Runoff.query.delete()
        r = Runoff(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id)
        db.session.add(r)
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='against', salt='s')

        VoteToken.create(member_id=member.id, stage=1, salt='s')
        db.session.commit()

        ro.close_runoff_stage(meeting)

        assert a1.status == 'carried'
        assert a2.status == 'failed'
        assert VoteToken.query.count() == 0


def test_close_runoff_stage_b_wins():
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

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='carried')
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2, status='carried')
        db.session.add_all([a1, a2])
        db.session.flush()

        Runoff.query.delete()
        r = Runoff(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id)
        db.session.add(r)
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='against', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')

        ro.close_runoff_stage(meeting)

        assert a1.status == 'failed'
        assert a2.status == 'carried'


def test_close_runoff_stage_tie_chair_decision():
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

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='carried')
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2, status='carried')
        db.session.add_all([a1, a2])
        db.session.flush()

        Runoff.query.delete()
        r = Runoff(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id, tie_break_method='chair')
        db.session.add(r)
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')

        a1.status = 'carried'
        a2.status = 'failed'
        db.session.commit()

        ro.close_runoff_stage(meeting)

        assert a1.status == 'carried'
        assert a2.status == 'failed'
        assert r.tie_break_method == 'chair'


def test_close_runoff_stage_tie_order_default():
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

        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='carried')
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A2', order=2, status='carried')
        db.session.add_all([a1, a2])
        db.session.flush()

        Runoff.query.delete()
        r = Runoff(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id)
        db.session.add(r)
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.flush()

        Vote.record(member_id=member.id, amendment_id=a1.id, choice='for', salt='s')
        Vote.record(member_id=member.id, amendment_id=a2.id, choice='for', salt='s')

        ro.close_runoff_stage(meeting)

        assert a1.status == 'carried'
        assert a2.status == 'failed'
        assert r.tie_break_method == 'order'


def test_runoff_ballot_window_enforced():
    app = _setup()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='AGM', opens_at_stage1=now, closes_at_stage1=now)
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

        with patch('app.services.runoff.datetime') as mock_dt:
            mock_dt.utcnow.return_value = now
            _, tokens = ro.close_stage1(meeting)

        plain = tokens[0][2]

        token_obj = VoteToken.verify(plain, app.config['TOKEN_SALT'])

        before = meeting.runoff_opens_at - timedelta(seconds=1)
        after = meeting.runoff_closes_at + timedelta(seconds=1)

        with app.test_request_context(f'/runoff/{plain}'):
            with patch('app.voting.routes.datetime') as mock_dt:
                mock_dt.utcnow.return_value = before
                resp = voting.runoff_ballot(plain)
                assert resp[1] == 400
                assert token_obj.used_at is None

        with app.test_request_context(f'/runoff/{plain}'):
            with patch('app.voting.routes.datetime') as mock_dt:
                mock_dt.utcnow.return_value = after
                resp = voting.runoff_ballot(plain)
                assert resp[1] == 400
                assert token_obj.used_at is None

