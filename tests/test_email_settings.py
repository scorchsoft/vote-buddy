from app.services.email import auto_send_enabled
from app import create_app
from app.extensions import db
from app.models import Meeting, EmailSetting, AppSetting


def test_auto_send_disabled_via_setting():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='M')
        db.session.add(meeting)
        db.session.commit()
        es = EmailSetting(meeting_id=meeting.id, email_type='stage1_invite', auto_send=False)
        db.session.add(es)
        db.session.commit()
        assert auto_send_enabled(meeting, 'stage1_invite') is False


def test_auto_send_disabled_global():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='M')
        db.session.add(meeting)
        db.session.commit()
        AppSetting.set('manual_email_mode', '1')
        assert auto_send_enabled(meeting, 'stage1_invite') is False
