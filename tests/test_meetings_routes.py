import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from werkzeug.exceptions import Forbidden

from app import create_app
from app.extensions import db
from app.models import User, Role, Permission, Meeting, Member, VoteToken
import io
from app.meetings import routes as meetings
from types import SimpleNamespace


def _make_user(has_permission: bool):
    perm = Permission(name='manage_meetings') if has_permission else None
    role = Role(permissions=[perm] if perm else [])
    user = User(role=role)
    user.is_active = True
    return user


def test_list_meetings_requires_permission():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_request_context('/meetings/'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                meetings.list_meetings()

        with app.test_request_context('/meetings/'):
            user = _make_user(False)
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('flask.flash'):
                    try:
                        meetings.list_meetings()
                    except Forbidden:
                        pass
                    else:
                        assert False, 'expected Forbidden'


def test_import_members_sends_invites_and_tokens():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='Test')
        db.session.add(meeting)
        db.session.commit()

        csv_content = (
            "member_id,name,email,vote_weight,proxy_for\n"
            "1,Alice,alice@example.com,1,\n"
        )
        data = {
            'csv_file': (io.BytesIO(csv_content.encode()), 'members.csv')
        }
        with app.test_request_context(
            f'/meetings/{meeting.id}/import-members', method='POST', data=data
        ):
            user = _make_user(True)
            dummy_form = SimpleNamespace(
                csv_file=SimpleNamespace(data=io.BytesIO(csv_content.encode()))
            )
            dummy_form.validate_on_submit = lambda: True
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('app.meetings.routes.MemberImportForm', return_value=dummy_form):
                    with patch('app.meetings.routes.send_vote_invite') as mock_send:
                        meetings.import_members(meeting.id)
                        mock_send.assert_called_once()
                        assert VoteToken.query.count() == 1


def test_close_stage1_creates_stage2_tokens_and_emails():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['MAIL_SUPPRESS_SEND'] = True
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='Test')
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Bob', email='b@example.com')
        db.session.add(member)
        db.session.commit()

        with app.test_request_context(
            f'/meetings/{meeting.id}/close-stage1', method='POST'
        ):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('app.meetings.routes.send_stage2_invite') as mock_send:
                    meetings.close_stage1(meeting.id)
                    mock_send.assert_called_once()
                    assert (
                        VoteToken.query.filter_by(member_id=member.id, stage=2).count()
                        == 1
                    )

