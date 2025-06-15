import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import render_template
from app import create_app
from app.extensions import db
from app.models import Role
from app.admin.forms import UserCreateForm
from app.meetings.forms import MeetingForm


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_admin_user_form_has_labels():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        role = Role(name='Admin')
        db.session.add(role)
        db.session.commit()
        with app.test_request_context('/admin/users/create'):
            form = UserCreateForm()
            form.role_id.choices = [(role.id, role.name)]
            html = render_template('admin/user_form.html', form=form, user=None)
            assert f'for="{form.email.id}"' in html
            assert f'for="{form.password.id}"' in html
            assert f'for="{form.role_id.id}"' in html
            assert f'for="{form.is_active.id}"' in html


def test_meeting_form_has_labels():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context('/meetings/create'):
            form = MeetingForm()
            html = render_template('meetings/meetings_form.html', form=form, meeting=None)
            assert f'for="{form.title.id}"' in html
            assert f'for="{form.type.id}"' in html
            assert f'for="{form.opens_at_stage1.id}"' in html
            assert f'for="{form.revoting_allowed.id}"' in html

