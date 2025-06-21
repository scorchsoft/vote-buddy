import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Meeting, Member, Motion, VoteToken, Comment
from app.comments import routes as comments


def _setup_app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TOKEN_SALT"] = "salty"
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def test_add_comment_records_text():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", comments_enabled=True)
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@example.com")
        db.session.add(member)
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt="salty")
        db.session.commit()
        with app.test_request_context(
            f"/comments/{plain}/motion/{motion.id}", method="POST", data={"text": "Hi"}
        ):
            comments.add_motion_comment(plain, motion.id)
        c = Comment.query.first()
        assert c.text_md == "Hi"
        assert c.member_id == member.id


def test_flash_message_after_comment_post():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", comments_enabled=True)
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@example.com")
        db.session.add(member)
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="t",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt="salty")
        db.session.commit()
        client = app.test_client()
        resp = client.post(
            f"/comments/{plain}/motion/{motion.id}",
            data={"text": "Hi"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Comment posted" in resp.data


def test_add_comment_disallowed_when_disabled():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", comments_enabled=False)
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@example.com")
        db.session.add(member)
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="t",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt="salty")
        db.session.commit()
        with app.test_request_context(
            f"/comments/{plain}/motion/{motion.id}", method="POST", data={"text": "Hi"}
        ):
            try:
                comments.add_motion_comment(plain, motion.id)
            except Exception as e:
                assert e.code == 403
            else:
                assert False, "expected 403"
        assert Comment.query.count() == 0


def test_toggle_member_commenting_flips_flag():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", comments_enabled=True)
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        assert member.can_comment is True
        with app.test_request_context(
            f"/comments/member/{member.id}/toggle", method="POST"
        ):
            comments.toggle_member_commenting.__wrapped__.__wrapped__(member.id)
        db.session.refresh(member)
        assert member.can_comment is False
