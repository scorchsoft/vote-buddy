import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import Role, Permission, User, Meeting, AdminLog
from app.admin import routes as admin


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_create_user_logged():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        perm = Permission(name='manage_users')
        role = Role(name='Admin', permissions=[perm])
        db.session.add_all([perm, role])
        db.session.commit()
        admin_user = User(email='root@example.com', role=role, is_active=True)
        db.session.add(admin_user)
        db.session.commit()
        data = {'email': 'new@example.com', 'password': 'pw', 'role_id': role.id, 'is_active': 'y'}
        with app.test_request_context('/admin/users/create', method='POST', data=data):
            with patch('flask_login.utils._get_user', return_value=admin_user):
                admin.create_user()
        log = AdminLog.query.filter_by(action='create_user').first()
        assert log is not None
        assert log.user_id == admin_user.id


def test_toggle_public_results_logged():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        perm = Permission(name='manage_meetings')
        role = Role(name='Coordinator', permissions=[perm])
        user = User(email='c@example.com', role=role, is_active=True)
        meeting = Meeting(title='AGM')
        db.session.add_all([perm, role, user, meeting])
        db.session.commit()
        with app.test_request_context(f'/admin/meetings/{meeting.id}/toggle-public', method='POST'):
            with patch('flask_login.utils._get_user', return_value=user):
                admin.toggle_public_results(meeting.id)
        log = AdminLog.query.filter_by(action='toggle_public_results').first()
        assert log and str(meeting.id) in log.details


def test_update_settings_logged():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        perm = Permission(name='manage_settings')
        role = Role(name='Root', permissions=[perm])
        user = User(email='root@example.com', role=role, is_active=True)
        db.session.add_all([perm, role, user])
        db.session.commit()
        data = {
            'site_title': 'VoteBuddy',
            'site_logo': '',
            'from_email': 'a@example.com',
            'runoff_extension_minutes': '10',
            'reminder_hours_before_close': '1',
            'reminder_cooldown_hours': '1',
            'reminder_template': 'email/reminder',
            'tie_break_decisions': '',
            'clerical_text': '',
            'move_text': '',
            'manual_email_mode': 'y',
            'contact_url': 'https://example.com',
        }
        with app.test_request_context('/admin/settings', method='POST', data=data):
            with patch('flask_login.utils._get_user', return_value=user):
                admin.manage_settings()
        log = AdminLog.query.filter_by(action='update_settings').first()
        assert log is not None

