import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Meeting, Member, Motion, Amendment, AmendmentObjection, Role, Permission, User
from app.meetings import routes as meetings
from app.admin import routes as admin
from unittest.mock import patch
import pytest
from datetime import datetime


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def _make_admin():
    perm = Permission(name='manage_meetings')
    role = Role(permissions=[perm])
    user = User(role=role)
    user.is_active = True
    return user


def test_submit_objection_creates_record():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='A')
        db.session.add(member)
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='x', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='rejected')
        db.session.add(amend)
        db.session.commit()

        data = {'member_id': member.id, 'email': 'x@example.com'}
        with patch('app.meetings.routes.send_objection_confirmation') as mock_send:
            with app.test_request_context(f'/meetings/amendments/{amend.id}/object', method='POST', data=data):
                meetings.submit_objection(amend.id)
                obj = AmendmentObjection.query.first()
                assert obj.email == 'x@example.com'
                assert obj.token is not None
                assert not obj.confirmed
                mock_send.assert_called_once()


def test_reinstate_amendment_when_threshold_met():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='x', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='rejected')
        db.session.add(amend)
        members = []
        for i in range(25):
            m = Member(meeting_id=meeting.id, name=f'M{i}')
            db.session.add(m)
            db.session.flush()
            db.session.add(AmendmentObjection(amendment_id=amend.id, member_id=m.id))
            members.append(m)
        db.session.commit()

        with app.test_request_context(f'/admin/objections/{amend.id}/reinstate', method='POST'):
            user = _make_admin()
            with patch('flask_login.utils._get_user', return_value=user):
                admin.reinstate_amendment(amend.id)
                assert amend.status is None


def test_reinstate_requires_permission():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='x', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1, status='rejected')
        db.session.add(amend)
        db.session.commit()

        with app.test_request_context(f'/admin/objections/{amend.id}/reinstate', method='POST'):
            user = User(role=Role(permissions=[]))
            user.is_active = True
            with patch('flask_login.utils._get_user', return_value=user):
                with pytest.raises(Exception):
                    admin.reinstate_amendment(amend.id)
