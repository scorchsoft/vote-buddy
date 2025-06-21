import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from flask import render_template
from flask_login import AnonymousUserMixin

from app import create_app
from app.extensions import db
from app.models import Meeting, Member, Motion, Amendment, VoteToken
from app.voting import routes as voting


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TOKEN_SALT'] = 's'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_sticky_footer_rendered():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='T', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name='Alice', email='a@e.co')
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config['TOKEN_SALT'])
        db.session.commit()

        with app.test_request_context(f'/vote/{plain}'):
            html = voting.ballot_token(plain)
            assert 'id="vote-footer"' in html
            assert 'Submit vote' in html


def test_ballot_templates_include_help_link():
    """Ensure all ballot templates have a Need help? link."""
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='T', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='A1', order=1)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name='Alice', email='a@e.co')
        db.session.add(member)
        db.session.commit()

        _, stage1_plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config['TOKEN_SALT'])
        _, stage2_plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config['TOKEN_SALT'])
        db.session.commit()

        with app.test_request_context(f'/vote/{stage1_plain}'):
            html = voting.ballot_token(stage1_plain)
            assert 'Need help?' in html
            assert '/help' in html

        meeting.ballot_mode = 'combined'
        db.session.commit()
        with app.test_request_context(f'/vote/{stage1_plain}'):
            html = voting.ballot_token(stage1_plain)
            assert 'Need help?' in html

        with app.test_request_context(f'/vote/{stage2_plain}'):
            html = voting.ballot_token(stage2_plain)
            assert 'Need help?' in html


def test_theme_toggle_button_present():
    """Render base.html and check the dark mode toggle is included.

    The template is rendered server-side only, so the JavaScript that reads or
    writes `localStorage` isn't executed here.
    """
    app = _setup_app()
    with app.app_context():
        db.create_all()
        anon = AnonymousUserMixin()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                assert '<button id="theme-toggle"' in html
                assert 'aria-label="Switch to dark mode"' in html
                assert 'id="theme-icon"' in html


def test_footer_admin_login_link_for_anonymous():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        anon = AnonymousUserMixin()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                assert 'Admin Login' in html
                assert 'Logout' not in html


def test_footer_no_admin_login_when_authenticated():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        from app.models import User, Role
        role = Role(name='Admin')
        db.session.add(role)
        user = User(email='test@example.com', role=role)
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=user):
                html = render_template('base.html')
                assert 'Admin Login' not in html
                assert 'Logout' in html


def test_footer_includes_receipt_link():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        anon = AnonymousUserMixin()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                assert 'href="/vote/verify-receipt"' in html

