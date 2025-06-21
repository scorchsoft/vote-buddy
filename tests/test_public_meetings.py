import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from flask import render_template, url_for
from flask_login import AnonymousUserMixin
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import Meeting, Member
from app import routes as main


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TOKEN_SALT'] = 's'
    return app


def test_public_meetings_list_renders():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        m = Meeting(title='AGM', status='Stage 1')
        db.session.add(m)
        db.session.commit()
        with app.test_request_context('/public/meetings'):
            html = main.public_meetings()
            assert 'AGM' in html


def test_nav_uses_public_link_when_anonymous():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        anon = AnonymousUserMixin()
        with app.test_request_context('/'):
            with patch('flask_login.utils._get_user', return_value=anon):
                html = render_template('base.html')
                href = url_for('main.public_meetings')
                assert href in html


def test_public_meeting_detail_includes_timezone():
    app = _setup_app()
    with app.app_context():
        app.config['TIMEZONE'] = 'UTC'
        db.create_all()
        meeting = Meeting(
            title='AGM',
            opens_at_stage1=datetime(2030, 1, 1, 9),
            closes_at_stage1=datetime(2030, 1, 1, 10),
            runoff_opens_at=datetime(2030, 1, 1, 11),
            runoff_closes_at=datetime(2030, 1, 1, 12),
            opens_at_stage2=datetime(2030, 1, 2, 9),
            closes_at_stage2=datetime(2030, 1, 2, 10),
        )
        db.session.add(meeting)
        db.session.commit()
        with app.test_request_context(f'/public/meetings/{meeting.id}'):
            html = main.public_meeting_detail(meeting.id)
            assert html.count('UTC') >= 3
