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
)
from app.voting import routes as voting
from unittest.mock import patch
from datetime import datetime, timedelta


def _setup_app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["VOTE_SALT"] = "salty"
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def test_ballot_token_not_found():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context("/vote/bad"):
            with pytest.raises(NotFound):
                voting.ballot_token("bad")


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
        token = VoteToken(token="tok123", member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()
        member_id = member.id

        with app.test_request_context(
            "/vote/tok123", method="POST", data={f"amend_{amendment.id}": "for"}
        ):
            voting.ballot_token("tok123")

        vote = Vote.query.first()
        token_db = VoteToken.query.filter_by(token="tok123").first()
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
        token = VoteToken(token="tok2", member_id=member.id, stage=2)
        db.session.add(token)
        db.session.commit()
        member_id = member.id

        with app.test_request_context(
            "/vote/tok2", method="POST", data={f"motion_{motion.id}": "against"}
        ):
            voting.ballot_token("tok2")

        vote = Vote.query.first()
        expected = hashlib.sha256(f"{member_id}againstsalty".encode()).hexdigest()
        assert vote.motion_id == motion.id
        assert vote.hash == expected
        assert token.used_at is not None


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
        token = VoteToken(token="tok-window", member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()

        before_open = opens - timedelta(minutes=5)
        after_close = closes + timedelta(minutes=5)

        with app.test_request_context("/vote/tok-window"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = before_open
                resp = voting.ballot_token("tok-window")
                assert resp[1] == 400
                assert token.used_at is None

        with app.test_request_context("/vote/tok-window"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = after_close
                resp = voting.ballot_token("tok-window")
                assert resp[1] == 400
                assert token.used_at is None


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
        token = VoteToken(token="cmb1", member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()

        with app.test_request_context(
            "/vote/cmb1",
            method="POST",
            data={f"amend_{amend.id}": "for", f"motion_{motion.id}": "for"},
        ):
            voting.ballot_token("cmb1")

        votes = Vote.query.order_by(Vote.id).all()
        assert len(votes) == 2
        assert votes[0].amendment_id == amend.id
        assert votes[1].motion_id == motion.id
        assert token.used_at is not None

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
        token = VoteToken(token="tok-stage2", member_id=member.id, stage=2)
        db.session.add(token)
        db.session.commit()

        before_open = opens - timedelta(minutes=5)
        after_close = closes + timedelta(minutes=5)

        with app.test_request_context("/vote/tok-stage2"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = before_open
                resp = voting.ballot_token("tok-stage2")
                assert resp[1] == 400
                assert token.used_at is None

        with app.test_request_context("/vote/tok-stage2"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = after_close
                resp = voting.ballot_token("tok-stage2")
                assert resp[1] == 400
                assert token.used_at is None

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
        token = VoteToken(token="proxy1", member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()

        with app.test_request_context(
            "/vote/proxy1",
            method="POST",
            data={f"amend_{amend.id}": "for"},
        ):
            voting.ballot_token("proxy1")

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
        token = VoteToken(token="s2", member_id=member.id, stage=2)
        db.session.add(token)
        db.session.commit()
        with app.test_request_context("/vote/s2"):
            html = voting.ballot_token("s2")
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
        token = VoteToken(token="s2", member_id=member.id, stage=2)
        db.session.add(token)
        db.session.commit()
        with app.test_request_context("/vote/s2"):
            html = voting.ballot_token("s2")
            assert "Merged" in html
