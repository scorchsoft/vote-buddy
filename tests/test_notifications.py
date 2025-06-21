import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from unittest.mock import patch
from app import create_app
from app.extensions import db, mail
from app.models import Member, Meeting, UnsubscribeToken
from app.services.email import send_vote_invite


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['MAIL_SUPPRESS_SEND'] = True
    return app


def test_unsubscribe_token_created_and_link_in_email():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        member = Member(name='A', email='a@example.com', meeting_id=1)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_vote_invite(member, 'tok', meeting, test_mode=False)
                mock_send.assert_called_once()
                token = UnsubscribeToken.query.filter_by(member_id=member.id).first()
                assert token is not None
                sent = mock_send.call_args[0][0]
                assert f'/unsubscribe/{token.token}' in sent.body
                assert f'/resubscribe/{token.token}' in sent.body


def test_unsubscribe_route_marks_opt_out():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='M')
        db.session.add(meeting)
        member = Member(name='B', email='b@example.com', meeting_id=1)
        db.session.add(member)
        token = UnsubscribeToken(token='t1', member_id=1)
        db.session.add(token)
        db.session.commit()
        client = app.test_client()
        resp = client.get(f'/unsubscribe/{token.token}')
        assert resp.status_code == 200
        assert db.session.get(Member, 1).email_opt_out is True


def test_resubscribe_route_clears_opt_out():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='M')
        db.session.add(meeting)
        member = Member(name='D', email='d@example.com', meeting_id=1, email_opt_out=True)
        db.session.add(member)
        token = UnsubscribeToken(token='t2', member_id=1)
        db.session.add(token)
        db.session.commit()
        client = app.test_client()
        resp = client.get(f'/resubscribe/{token.token}')
        assert resp.status_code == 200
        assert db.session.get(Member, 1).email_opt_out is False


def test_email_not_sent_when_opted_out():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        member = Member(name='C', email='c@example.com', meeting_id=1, email_opt_out=True)
        db.session.add(member)
        db.session.commit()
        with app.test_request_context('/'):
            with patch.object(mail, 'send') as mock_send:
                send_vote_invite(member, 'tok', meeting, test_mode=False)
                mock_send.assert_not_called()
