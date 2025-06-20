import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db, mail
from app.models import Member, Meeting
from app.services.email import (
    send_vote_invite,
    send_runoff_invite,
    send_stage1_reminder,
    send_stage2_invite,
    send_vote_receipt,
    send_quorum_failure,
)


def test_send_vote_invite_sends_mail():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['MAIL_SUPPRESS_SEND'] = True
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='Test Meeting',
            opens_at_stage1=now,
            closes_at_stage1=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        member = Member(name='Alice', email='alice@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_vote_invite(member, 'abc123', meeting, test_mode=False)
                mock_send.assert_called_once()
                sent_msg = mock_send.call_args[0][0]
                assert '/vote/abc123' in sent_msg.body
                assert any(a.filename == 'stage1.ics' for a in sent_msg.attachments)


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['MAIL_SUPPRESS_SEND'] = True
    app.config['TOKEN_SALT'] = 's'
    return app


def test_send_runoff_invite_uses_token_url():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        member = Member(name='Bob', email='bob@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_runoff_invite(member, 'abc123', meeting, test_mode=False)
                mock_send.assert_called_once()
                sent_msg = mock_send.call_args[0][0]
                assert '/vote/runoff/abc123' in sent_msg.body


def test_send_stage1_reminder_uses_token_url():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        member = Member(name='Cathy', email='c@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_stage1_reminder(member, 'abc123', meeting, test_mode=False)
                mock_send.assert_called_once()
                sent_msg = mock_send.call_args[0][0]
                assert '/vote/abc123' in sent_msg.body


def test_send_stage2_invite_has_calendar_attachment():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            opens_at_stage2=now,
            closes_at_stage2=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        member = Member(name='Eve', email='e@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_stage2_invite(member, 'abc123', meeting, test_mode=False)
                mock_send.assert_called_once()
                sent_msg = mock_send.call_args[0][0]
                assert any(a.filename == 'stage2.ics' for a in sent_msg.attachments)
                assert '/results/' in sent_msg.body


def test_send_vote_receipt_includes_hash():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        member = Member(name='Deb', email='d@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_vote_receipt(member, meeting, ['abc123'], test_mode=False)
                mock_send.assert_called_once()
                sent_msg = mock_send.call_args[0][0]
                assert 'abc123' in sent_msg.body
                assert '/unsubscribe/' in sent_msg.body


def test_send_quorum_failure_email():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        member = Member(name='Fran', email='f@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_quorum_failure(member, meeting, test_mode=False)
                mock_send.assert_called_once()
                sent_msg = mock_send.call_args[0][0]
                assert 'Stage 1 vote void' in sent_msg.subject
