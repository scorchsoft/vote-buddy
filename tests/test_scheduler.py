import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from datetime import datetime, timedelta

from app import create_app
from app.extensions import db, scheduler
from app.models import Meeting, Member, VoteToken
from app.tasks import register_jobs, send_stage1_reminders


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 2
    app.config['REMINDER_COOLDOWN_HOURS'] = 24
    return app


def test_register_jobs_adds_interval_job():
    with patch.object(scheduler, 'add_job') as add_job:
        register_jobs()
        add_job.assert_called_once()


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
        token = VoteToken(token='tok', member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()
        with patch('app.tasks.send_stage1_reminder') as mock_send:
            send_stage1_reminders()
            assert mock_send.called
            assert meeting.stage1_reminder_sent_at is not None
