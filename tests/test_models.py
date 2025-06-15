import sys, os; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models import User, Role, Permission


def test_set_password_and_check():
    user = User()
    user.set_password('secret')
    assert user.password_hash != 'secret'
    assert user.check_password('secret') is True
    assert user.check_password('wrong') is False


def test_has_permission():
    perm_view = Permission(name='view_dashboard')
    role = Role(permissions=[perm_view])
    user = User(role=role)

    assert user.has_permission('view_dashboard') is True
    assert user.has_permission('manage_users') is False


from datetime import datetime, timedelta
from app.extensions import db
from app import create_app
from app.models import Meeting, Member, VoteToken


def test_meeting_stage1_votes_count():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM', quorum=2)
        db.session.add(meeting)
        db.session.flush()
        m1 = Member(meeting_id=meeting.id, name='A')
        m2 = Member(meeting_id=meeting.id, name='B')
        db.session.add_all([m1, m2])
        db.session.flush()
        t1 = VoteToken(token=VoteToken._hash('t1', 's'), member_id=m1.id, stage=1, used_at=datetime.utcnow())
        t2 = VoteToken(token=VoteToken._hash('t2', 's'), member_id=m2.id, stage=1)
        db.session.add_all([t1, t2])
        db.session.commit()
        assert meeting.stage1_votes_count() == 1


def test_hours_until_next_reminder_first():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 6
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(title='AGM', closes_at_stage1=now + timedelta(hours=8))
        db.session.add(meeting)
        db.session.commit()
        assert meeting.hours_until_next_reminder(now=now) == 2


def test_hours_until_next_reminder_after_first():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REMINDER_HOURS_BEFORE_CLOSE'] = 6
    app.config['REMINDER_COOLDOWN_HOURS'] = 24
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title='AGM', closes_at_stage1=now + timedelta(hours=30),
            stage1_reminder_sent_at=now
        )
        db.session.add(meeting)
        db.session.commit()
        assert meeting.hours_until_next_reminder(now=now) == 24
