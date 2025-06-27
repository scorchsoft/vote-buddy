from app.services.email import auto_send_enabled
from app import create_app
from app.extensions import db
from app.models import Meeting, EmailSetting, AppSetting
from app.meetings import routes as meetings_routes
from datetime import datetime, timedelta


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


def test_email_schedule_two_stage_includes_stage2():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            ballot_mode='two-stage',
            notice_date=now,
            closes_at_stage1=now + timedelta(days=1),
            opens_at_stage2=now + timedelta(days=2),
            closes_at_stage2=now + timedelta(days=3),
        )
        schedule = meetings_routes._email_schedule(meeting)
        assert set(schedule.keys()) == {
            'submission_invite',
            'review_invite',
            'amendment_review_invite',
            'stage1_invite',
            'stage1_reminder',
            'stage2_invite',
            'stage2_reminder',
        }


def test_email_schedule_combined_excludes_stage2():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM',
            ballot_mode='combined',
            notice_date=now,
            closes_at_stage1=now + timedelta(days=1),
        )
        schedule = meetings_routes._email_schedule(meeting)
        assert set(schedule.keys()) == {
            'submission_invite',
            'review_invite',
            'amendment_review_invite',
            'stage1_invite',
            'stage1_reminder',
        }
