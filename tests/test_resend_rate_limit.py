import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Meeting, Member


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['MAIL_SUPPRESS_SEND'] = True
    app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'
    app.config['TOKEN_SALT'] = 's'
    app.extensions['mail'].suppress = True
    app.extensions['mail'].default_sender = 'noreply@example.com'
    return app


def test_public_resend_is_rate_limited_per_email():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM', status='Stage 1')
        db.session.add(meeting)
        db.session.flush()
        member = Member(
            meeting_id=meeting.id,
            name='Alice',
            email='alice@example.com',
            member_number='123',
        )
        db.session.add(member)
        db.session.commit()

        client = app.test_client()
        data = {'email': member.email, 'member_number': '123'}
        for _ in range(5):
            resp = client.post(f'/public/meetings/{meeting.id}/resend', data=data)
            assert resp.status_code == 200

        resp = client.post(f'/public/meetings/{meeting.id}/resend', data=data)
        assert resp.status_code == 429

        other = {'email': 'other@example.com', 'member_number': '123'}
        resp = client.post(f'/public/meetings/{meeting.id}/resend', data=other)
        assert resp.status_code == 200


def test_public_resend_returns_generic_success():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM', status='Stage 1')
        db.session.add(meeting)
        db.session.flush()
        member = Member(
            meeting_id=meeting.id,
            name='Alice',
            email='alice@example.com',
            member_number='123',
        )
        db.session.add(member)
        db.session.commit()

        client = app.test_client()
        data = {'email': member.email, 'member_number': '123'}
        resp = client.post(f'/public/meetings/{meeting.id}/resend', data=data)
        assert resp.status_code == 200
        assert 'If the details are correct' in resp.get_data(as_text=True)

        wrong = {'email': 'bad@example.com', 'member_number': '999'}
        resp2 = client.post(f'/public/meetings/{meeting.id}/resend', data=wrong)
        assert resp2.status_code == 200
        assert resp.get_data(as_text=True) == resp2.get_data(as_text=True)
