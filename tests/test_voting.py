import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
import hashlib

import pytest
from werkzeug.exceptions import NotFound

from app import create_app
from app.extensions import db
from app.models import (
    Meeting,
    Member,
    VoteToken,
    Amendment,
    Motion,
    MotionOption,
    Vote,
    Runoff,
)
from app.voting import routes as voting
from unittest.mock import patch
from datetime import datetime, timedelta


def _setup_app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["VOTE_SALT"] = "salty"
    app.config["TOKEN_SALT"] = "salty"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["MAIL_SUPPRESS_SEND"] = True
    app.config["MAIL_DEFAULT_SENDER"] = "test@example.com"
    from app.extensions import mail
    mail.suppress = True
    app.extensions["mail"].default_sender = "test@example.com"
    app.extensions["mail"].suppress = True
    return app


def test_ballot_token_not_found():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context("/vote/bad"):
            resp = voting.ballot_token("bad")
            assert resp[1] == 404


def test_cast_vote_records_hash_and_marks_used():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        amendment = Amendment(
            meeting_id=meeting.id, motion_id=motion.id, text_md="Test", order=1
        )
        db.session.add(amendment)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()
        member_id = member.id

        with app.test_request_context(
            f"/vote/{plain}", method="POST", data={f"amend_{amendment.id}": "for"}
        ):
            voting.ballot_token(plain)

        vote = Vote.query.first()
        token_db = VoteToken.query.filter_by(token=token_obj.token).first()
        expected = hashlib.sha256(f"{member_id}forsalty".encode()).hexdigest()
    assert vote.hash == expected
    assert token_db.used_at is not None


def test_stage2_motion_vote():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()
        member_id = member.id

        with app.test_request_context(
            f"/vote/{plain}", method="POST", data={f"motion_{motion.id}": "against"}
        ):
            voting.ballot_token(plain)

        vote = Vote.query.first()
        expected = hashlib.sha256(f"{member_id}againstsalty".encode()).hexdigest()
        assert vote.motion_id == motion.id
        assert vote.hash == expected
        assert token_obj.used_at is not None


def test_receipt_email_sent_after_vote():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token = VoteToken(token="tok-receipt", member_id=member.id, stage=2)
        db.session.add(token)
        db.session.commit()
        with patch("app.voting.routes.send_vote_receipt") as mock_receipt:
            with app.test_request_context(
                "/vote/tok-receipt",
                method="POST",
                data={f"motion_{motion.id}": "for"},
            ):
                voting.ballot_token("tok-receipt")
            mock_receipt.assert_called_once()
            called_hashes = mock_receipt.call_args[0][2]
            vote = Vote.query.first()
            assert vote.hash in called_hashes


def test_ballot_token_outside_window_returns_error():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        opens = datetime.utcnow() + timedelta(hours=1)
        closes = opens + timedelta(hours=1)
        meeting = Meeting(title="AGM", opens_at_stage1=opens, closes_at_stage1=closes)
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        before_open = opens - timedelta(minutes=5)
        after_close = closes + timedelta(minutes=5)

        with app.test_request_context(f"/vote/{plain}"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = before_open
                resp = voting.ballot_token(plain)
                assert resp[1] == 400
                assert token_obj.used_at is None

        with app.test_request_context(f"/vote/{plain}"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = after_close
                resp = voting.ballot_token(plain)
                assert resp[1] == 400
                assert token_obj.used_at is None


def test_combined_ballot_records_votes():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", ballot_mode="combined")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A1",
            order=1,
        )
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name="Bob", email="b@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(
            f"/vote/{plain}",
            method="POST",
            data={f"amend_{amend.id}": "for", f"motion_{motion.id}": "for"},
        ):
            voting.ballot_token(plain)

        votes = Vote.query.order_by(Vote.id).all()
        assert len(votes) == 2
        assert votes[0].amendment_id == amend.id
        assert votes[1].motion_id == motion.id
        assert token_obj.used_at is not None

def test_stage2_token_window_enforcement():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        opens = datetime.utcnow() + timedelta(hours=1)
        closes = opens + timedelta(hours=1)
        meeting = Meeting(title="AGM", opens_at_stage2=opens, closes_at_stage2=closes)
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        before_open = opens - timedelta(minutes=5)
        after_close = closes + timedelta(minutes=5)

        with app.test_request_context(f"/vote/{plain}"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = before_open
                resp = voting.ballot_token(plain)
                assert resp[1] == 400
                assert token_obj.used_at is None

        with app.test_request_context(f"/vote/{plain}"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = after_close
                resp = voting.ballot_token(plain)
                assert resp[1] == 400
                assert token_obj.used_at is None

def test_proxy_vote_creates_two_records():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A1",
            order=1,
        )
        db.session.add(amend)
        proxied = Member(meeting_id=meeting.id, name="Bob", email="b@example.com")
        db.session.add(proxied)
        db.session.flush()
        member = Member(
            meeting_id=meeting.id,
            name="Alice",
            email="a@example.com",
            proxy_for=str(proxied.id),
        )
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(
            f"/vote/{plain}",
            method="POST",
            data={f"amend_{amend.id}": "for"},
        ):
            voting.ballot_token(plain)

        votes = Vote.query.order_by(Vote.member_id).all()
        assert len(votes) == 2
        assert {v.member_id for v in votes} == {member.id, proxied.id}
        expected_alice = hashlib.sha256(f"{member.id}forsalty".encode()).hexdigest()
        expected_bob = hashlib.sha256(f"{proxied.id}forsalty".encode()).hexdigest()
        assert {votes[0].hash, votes[1].hash} == {expected_alice, expected_bob}


def test_compile_motion_text_orders_carried_amendments():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Base",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        a1 = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A1",
            order=2,
            status="carried",
        )
        a2 = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A2",
            order=1,
            status="carried",
        )
        a3 = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="X",
            order=3,
            status="failed",
        )
        db.session.add_all([a1, a2, a3])
        db.session.commit()
        result = voting.compile_motion_text(motion)
        assert result == "Base\n\nA2\n\nA1"


def test_stage2_ballot_displays_compiled_text():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Base",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        db.session.add(
            Amendment(
                meeting_id=meeting.id,
                motion_id=motion.id,
                text_md="Add",
                order=1,
                status="carried",
            )
        )
        db.session.commit()
        member = Member(meeting_id=meeting.id, name="A", email="a@e.co")
        db.session.add(member)
        db.session.flush()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()
        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert "Add" in html


def test_stage2_ballot_uses_final_text():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Base",
            final_text_md="Merged",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@e.co")
        db.session.add(member)
        db.session.flush()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()
        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert "Merged" in html


def test_stage1_locked_rejects_vote():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", stage1_locked=True)
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@e.co")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            resp = voting.ballot_token(plain)
            assert resp[1] == 400
            assert token_obj.used_at is None


def test_stage2_locked_rejects_vote():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", stage2_locked=True)
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Text",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="A", email="a@e.co")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            resp = voting.ballot_token(plain)
            assert resp[1] == 400
            assert token_obj.used_at is None


def test_runoff_ballot_display_and_submit():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        db.session.flush()
        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A1", order=1, status="carried")
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A2", order=2, status="carried")
        db.session.add_all([a1, a2])
        db.session.flush()
        rof = Runoff(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id)
        db.session.add(rof)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/runoff/{plain}"):
            html = voting.runoff_ballot(plain)
            assert "A1" in html
            assert "A2" in html

        with app.test_request_context(
            f"/runoff/{plain}", method="POST", data={f"runoff_{rof.id}": "a"}
        ):
            voting.runoff_ballot(plain)

        votes = Vote.query.order_by(Vote.amendment_id).all()
        assert len(votes) == 2
        assert votes[0].choice == ("for" if votes[0].amendment_id == a1.id else "against")
        assert token_obj.used_at is not None


def test_stepper_shows_stage1_current():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A1", order=1)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert 'bp-stepper-current" data-step="1"' in html
            assert 'data-step="2"' in html
            assert 'bp-stepper-complete' not in html


def test_stepper_shows_stage2_current_and_stage1_complete():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion",
            category="motion",
            threshold="normal",
            ordering=1,
        )
        db.session.add(motion)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert 'bp-stepper-complete" data-step="1"' in html
            assert 'bp-stepper-current" data-step="2"' in html

