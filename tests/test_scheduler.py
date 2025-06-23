import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db, scheduler
from app.models import Meeting, Member, VoteToken, EmailSetting
from app.tasks import (
    register_jobs,
    send_stage1_reminders,
    send_stage2_reminders,
    cleanup_vote_tokens,
    send_submission_invites,
)


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 2
    app.config['REMINDER_COOLDOWN_HOURS'] = 24
    app.config['STAGE2_REMINDER_HOURS_BEFORE_CLOSE'] = 2
    app.config['STAGE2_REMINDER_COOLDOWN_HOURS'] = 24
    app.config['TOKEN_SALT'] = 's'
    return app


def test_register_jobs_adds_interval_job():
    with patch.object(scheduler, 'add_job') as add_job:
        register_jobs()
        assert add_job.call_count == 5


def test_send_stage1_reminders_sends_only_unvoted():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='M', closes_at_stage1=now + timedelta(hours=1), quorum=5)
        db.session.add(meeting)
        db.session.flush()
        m1 = Member(meeting_id=meeting.id, name='Ann', email='a@example.com')
        m2 = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add_all([m1, m2])
        db.session.flush()
        t1, _ = VoteToken.create(member_id=m1.id, stage=1, salt=app.config['TOKEN_SALT'])
        t2, _ = VoteToken.create(member_id=m2.id, stage=1, salt=app.config['TOKEN_SALT'])
        t2.used_at = now
        db.session.add_all([t1, t2])
        db.session.commit()
        with patch('app.tasks.send_stage1_reminder') as mock_send:
            send_stage1_reminders()
            assert mock_send.call_count == 1
            assert mock_send.call_args.args[0].id == m1.id
            assert meeting.stage1_reminder_sent_at is not None


def test_send_stage2_reminders_sends_only_unvoted():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='M', closes_at_stage2=now + timedelta(hours=1))
        db.session.add(meeting)
        db.session.flush()
        m1 = Member(meeting_id=meeting.id, name='Ann', email='a@example.com')
        m2 = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add_all([m1, m2])
        db.session.flush()
        token_hash1 = VoteToken._hash('tok1', app.config['TOKEN_SALT'])
        token1 = VoteToken(token=token_hash1, member_id=m1.id, stage=2)
        token_hash2 = VoteToken._hash('tok2', app.config['TOKEN_SALT'])
        token2 = VoteToken(token=token_hash2, member_id=m2.id, stage=2)
        token2.used_at = now
        db.session.add_all([token1, token2])
        db.session.commit()
        with patch('app.tasks.send_stage2_reminder') as mock_send:
            send_stage2_reminders()
            assert mock_send.call_count == 1
            assert mock_send.call_args.args[0].id == m1.id
            assert meeting.stage2_reminder_sent_at is not None


def test_cleanup_vote_tokens_removes_expired_and_used():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        m1 = Meeting(
            title='M1',
            closes_at_stage1=now - timedelta(hours=1),
            closes_at_stage2=now - timedelta(hours=1),
            runoff_closes_at=now - timedelta(hours=1),
        )
        m2 = Meeting(title='M2', closes_at_stage1=now + timedelta(hours=1))
        db.session.add_all([m1, m2])
        db.session.flush()

        member1 = Member(meeting_id=m1.id, name='Ann')
        member2 = Member(meeting_id=m2.id, name='Bob')
        db.session.add_all([member1, member2])
        db.session.flush()

        t_used, _ = VoteToken.create(member_id=member1.id, stage=1, salt=app.config['TOKEN_SALT'])
        t_used.used_at = now
        t_expired1, _ = VoteToken.create(member_id=member1.id, stage=1, salt=app.config['TOKEN_SALT'])
        t_expired2, _ = VoteToken.create(member_id=member1.id, stage=2, salt=app.config['TOKEN_SALT'])
        t_valid, _ = VoteToken.create(member_id=member2.id, stage=1, salt=app.config['TOKEN_SALT'])
        db.session.add_all([t_used, t_expired1, t_expired2, t_valid])
        db.session.commit()

        cleanup_vote_tokens()
        remaining = VoteToken.query.all()
        assert len(remaining) == 1
        assert remaining[0].token == t_valid.token


def test_send_submission_invites_respects_setting():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM', motions_opens_at=now - timedelta(minutes=5)
        )
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Ann', email='a@example.com')
        db.session.add(member)
        setting = EmailSetting(
            meeting_id=meeting.id,
            email_type='submission_invite',
            auto_send=False,
        )
        db.session.add(setting)
        db.session.commit()

        with patch('app.tasks.send_submission_invite') as mock_send:
            send_submission_invites()
            assert mock_send.call_count == 0


def test_send_submission_invites_sends_when_enabled():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM', motions_opens_at=now - timedelta(minutes=5)
        )
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.commit()

        with patch('app.tasks.send_submission_invite') as mock_send:
            send_submission_invites()
            mock_send.assert_called_once()
