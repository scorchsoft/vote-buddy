import os, sys
from datetime import datetime, timedelta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import Meeting, Role, Permission, User
from app.admin import routes as admin
from flask import url_for


def _make_user():
    perm = Permission(name='view_dashboard')
    role = Role(permissions=[perm])
    user = User(role=role)
    user.email = 'admin@example.com'
    user.is_active = True
    return user


def test_admin_dashboard_shows_countdown():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 6
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='AGM', closes_at_stage1=now + timedelta(hours=8))
        db.session.add(meeting)
        db.session.commit()
        user = _make_user()
        with app.test_request_context('/admin/'):
            with patch('flask_login.utils._get_user', return_value=user):
                html = admin.dashboard()
                assert 'Next reminder in' in html
                assert '2h' in html


def test_admin_dashboard_contains_create_link():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        user = _make_user()
        with app.test_request_context('/admin/'):
            with patch('flask_login.utils._get_user', return_value=user):
                html = admin.dashboard()
                href = url_for('meetings.create_meeting')
                assert href in html
                assert 'bp-btn-primary' in html


def test_dashboard_shows_objection_status():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        perm = Permission(name='view_dashboard')
        role = Role(permissions=[perm])
        user = User(role=role, is_active=True)
        user.email = 'admin@example.com'
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        # create amendment and objection
        from app.models import Amendment, AmendmentObjection, Member
        member = Member(meeting_id=meeting.id, name='A')
        db.session.add(member)
        amend = Amendment(meeting_id=meeting.id, motion_id=None, text_md='A', order=1, status='rejected')
        db.session.add(amend)
        db.session.flush()
        obj = AmendmentObjection(amendment_id=amend.id, member_id=member.id, confirmed_at=datetime.utcnow(), deadline_first=datetime.utcnow()+timedelta(days=1))
        db.session.add(obj)
        db.session.commit()
        with app.test_request_context('/admin/'):
            with patch('flask_login.utils._get_user', return_value=user):
                html = admin.dashboard()
                assert 'Objections' in html
