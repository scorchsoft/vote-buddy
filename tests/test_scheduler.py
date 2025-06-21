import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db, scheduler
from app.models import Meeting, Member, VoteToken
from app.tasks import register_jobs, send_stage1_reminders, cleanup_vote_tokens


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 2
    app.config['REMINDER_COOLDOWN_HOURS'] = 24
    app.config['TOKEN_SALT'] = 's'
    return app


def test_register_jobs_adds_interval_job():
    with patch.object(scheduler, 'add_job') as add_job:
        register_jobs()
        assert add_job.call_count == 3


def test_send_stage1_reminders_sends_emails():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='M', closes_at_stage1=now + timedelta(hours=1), quorum=5)
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Ann', email='a@example.com')
        db.session.add(member)
        db.session.flush()
        token_hash = VoteToken._hash('tok', app.config['TOKEN_SALT'])
        token = VoteToken(token=token_hash, member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()
        with patch('app.tasks.send_stage1_reminder') as mock_send:
            send_stage1_reminders()
            assert mock_send.called
            assert meeting.stage1_reminder_sent_at is not None


def test_send_stage1_reminders_skips_voted_members():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='M', closes_at_stage1=now + timedelta(hours=1), quorum=5)
        db.session.add(meeting)
        db.session.flush()

        voted = Member(meeting_id=meeting.id, name='Ann', email='a@example.com')
        not_voted = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add_all([voted, not_voted])
        db.session.flush()

        token_voted = VoteToken(
            token=VoteToken._hash('tok1', app.config['TOKEN_SALT']),
            member_id=voted.id,
            stage=1,
            used_at=now,
        )
        token_unvoted = VoteToken(
            token=VoteToken._hash('tok2', app.config['TOKEN_SALT']),
            member_id=not_voted.id,
            stage=1,
        )
        db.session.add_all([token_voted, token_unvoted])
        db.session.commit()

        with patch('app.tasks.send_stage1_reminder') as mock_send:
            send_stage1_reminders()
            assert mock_send.call_count == 1
            assert mock_send.call_args.args[0].id == not_voted.id


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

        t_used = VoteToken(token=VoteToken._hash('used', app.config['TOKEN_SALT']), member_id=member1.id, stage=1, used_at=now)
        t_expired1 = VoteToken(token=VoteToken._hash('exp1', app.config['TOKEN_SALT']), member_id=member1.id, stage=1)
        t_expired2 = VoteToken(token=VoteToken._hash('exp2', app.config['TOKEN_SALT']), member_id=member1.id, stage=2)
        t_valid = VoteToken(token=VoteToken._hash('valid', app.config['TOKEN_SALT']), member_id=member2.id, stage=1)
        db.session.add_all([t_used, t_expired1, t_expired2, t_valid])
        db.session.commit()

        cleanup_vote_tokens()
        remaining = VoteToken.query.all()
        assert len(remaining) == 1
        assert remaining[0].token == t_valid.token
