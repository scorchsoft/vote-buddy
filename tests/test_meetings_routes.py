import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from werkzeug.exceptions import Forbidden
from flask import url_for

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Role,
    Permission,
    Meeting,
    VoteToken,
    Member,
    Motion,
    Amendment,
    Vote,
)
import io
from app.meetings import routes as meetings
from types import SimpleNamespace
from datetime import datetime, timedelta
from uuid6 import uuid7


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
                with patch('app.meetings.routes.flash'):
                    try:
                        meetings.list_meetings()
                    except Forbidden:
                        pass
                    else:
                        assert False, 'expected Forbidden'


def test_list_meetings_contains_create_link():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        with app.test_request_context('/meetings/'):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                html = meetings.list_meetings()
                href = url_for('meetings.create_meeting')
                assert href in html
                assert 'bp-btn-primary' in html


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
                with patch('app.meetings.routes.runoff.close_stage1', return_value=[]):
                    with patch('app.meetings.routes.send_stage2_invite') as mock_send:
                        meetings.close_stage1(meeting.id)
                        mock_send.assert_called_once()
                        assert (
                            VoteToken.query.filter_by(member_id=member.id, stage=2).count()
                            == 1
                        )


def test_close_stage1_runoff_triggers_emails_and_tokens():
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

        runoff_obj = SimpleNamespace(id=1)

        def _runoff_side_effect(mtg):
            token = VoteToken(token=str(uuid7()), member_id=member.id, stage=1)
            db.session.add(token)
            db.session.commit()
            return [runoff_obj]

        with app.test_request_context(
            f'/meetings/{meeting.id}/close-stage1', method='POST'
        ):
            user = _make_user(True)
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('app.meetings.routes.runoff.close_stage1', side_effect=_runoff_side_effect):
                    with patch('app.meetings.routes.send_runoff_invite') as mock_send:
                        meetings.close_stage1(meeting.id)
                        mock_send.assert_called_once()
                        assert (
                            VoteToken.query.filter_by(member_id=member.id, stage=1).count()
                            == 1
                        )


def test_add_amendment_validations():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='Test', opens_at_stage1=datetime.utcnow() + timedelta(days=30))
        db.session.add(meeting)
        db.session.flush()
        members = [
            Member(meeting_id=meeting.id, name='A', email='a@example.com'),
            Member(meeting_id=meeting.id, name='B', email='b@example.com'),
            Member(meeting_id=meeting.id, name='C', email='c@example.com'),
        ]
        for m in members:
            db.session.add(m)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title='M1',
            text_md='text',
            category='motion',
            threshold='normal',
            ordering=1,
        )
        db.session.add(motion)
        db.session.commit()

        user = _make_user(True)
        data = {
            'text_md': 'A1',
            'proposer_id': members[0].id,
            'seconder_id': members[1].id,
        }
        with app.test_request_context(f'/meetings/motions/{motion.id}/amendments/add', method='POST', data=data):
            with patch('flask_login.utils._get_user', return_value=user):
                meetings.add_amendment(motion.id)

        assert Amendment.query.count() == 1

        # fourth amendment by same proposer should fail
        for i in range(2,5):
            with app.test_request_context(
                f'/meetings/motions/{motion.id}/amendments/add',
                method='POST',
                data={'text_md': f'A{i}', 'proposer_id': members[0].id, 'seconder_id': members[2].id},
            ):
                with patch('flask_login.utils._get_user', return_value=user):
                    if i < 4:
                        meetings.add_amendment(motion.id)
                    else:
                        with patch('app.meetings.routes.flash') as fl:
                            meetings.add_amendment(motion.id)
                            fl.assert_called()

        assert Amendment.query.count() == 3

        # deadline validation
        meeting.opens_at_stage1 = datetime.utcnow() + timedelta(days=10)
        db.session.commit()
        with app.test_request_context(
            f'/meetings/motions/{motion.id}/amendments/add',
            method='POST',
            data={'text_md': 'late', 'proposer_id': members[2].id, 'seconder_id': members[1].id},
        ):
            with patch('flask_login.utils._get_user', return_value=user):
                with patch('app.meetings.routes.flash') as fl:
                    meetings.add_amendment(motion.id)
                    fl.assert_called()

        assert Amendment.query.count() == 3


def test_results_stage2_docx_returns_file():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title='M1',
            text_md='Motion text',
            category='motion',
            threshold='normal',
            ordering=1,
        )
        db.session.add(motion)
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.flush()
        Vote.record(member_id=member.id, motion_id=motion.id, choice='for', salt='s')

        user = _make_user(True)
        with app.test_request_context(f'/meetings/{meeting.id}/results-stage2.docx'):
            with patch('flask_login.utils._get_user', return_value=user):
                resp = meetings.results_stage2_docx(meeting.id)
                assert resp.mimetype == (
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
