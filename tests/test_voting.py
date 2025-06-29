import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
import hashlib

import pytest
from werkzeug.exceptions import NotFound, Forbidden

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
    User,
    Role,
    Permission,
)
from app.voting import routes as voting
from unittest.mock import patch
from datetime import datetime, timedelta
from flask_login import AnonymousUserMixin


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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        amendment = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="Test",
            order=1,
            is_published=True,
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
        expected = hashlib.sha256(
            f"{member_id}{amendment.id}1for{app.config['VOTE_SALT']}".encode()
        ).hexdigest()
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
            is_published=True,
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
        expected = hashlib.sha256(
            f"{member_id}{motion.id}2against{app.config['VOTE_SALT']}".encode()
        ).hexdigest()
        assert vote.motion_id == motion.id
        assert vote.hash == expected
        assert token_obj.used_at is not None


def test_vote_hash_unique_per_motion():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        m1 = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        m2 = Motion(
            meeting_id=meeting.id,
            title="M2",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=2,
            is_published=True,
        )
        db.session.add_all([m1, m2])
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(
            f"/vote/{plain}",
            method="POST",
            data={f"motion_{m1.id}": "for", f"motion_{m2.id}": "for"},
        ):
            voting.ballot_token(plain)

        votes = Vote.query.order_by(Vote.motion_id).all()
        assert len(votes) == 2
        h1 = hashlib.sha256(
            f"{member.id}{m1.id}2for{app.config['VOTE_SALT']}".encode()
        ).hexdigest()
        h2 = hashlib.sha256(
            f"{member.id}{m2.id}2for{app.config['VOTE_SALT']}".encode()
        ).hexdigest()
        hashes = {votes[0].hash, votes[1].hash}
        assert hashes == {h1, h2}


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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(
            member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"]
        )
        db.session.add(token_obj)
        db.session.commit()
        
        with patch("app.voting.routes.send_vote_receipt") as mock_receipt:
            with app.test_request_context(
                f"/vote/{plain}",
                method="POST",
                data={f"motion_{motion.id}": "for"},
            ):
                voting.ballot_token(plain)
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
            is_published=True,
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


def test_ballot_token_before_open_shows_times():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        opens = datetime.utcnow() + timedelta(hours=1)
        closes = opens + timedelta(hours=2)
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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        before_open = opens - timedelta(minutes=5)

        with app.test_request_context(f"/vote/{plain}"):
            with patch("app.voting.routes.datetime") as mock_dt:
                mock_dt.utcnow.return_value = before_open
                resp = voting.ballot_token(plain)
                assert resp[1] == 400
                html = resp[0]
                assert opens.strftime("%Y-%m-%d %H:%M") in html
                assert closes.strftime("%Y-%m-%d %H:%M") in html


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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A1",
            order=1,
            is_published=True,
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
            is_published=True,
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

def test_proxy_vote_records_for_principal_only_and_blocks_second():
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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        amend = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A1",
            order=1,
            is_published=True,
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
        proxy_token, prox_plain = VoteToken.create(member_id=proxied.id, stage=1, salt=app.config["TOKEN_SALT"], proxy_holder_id=member.id)
        self_token, self_plain = VoteToken.create(member_id=proxied.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(
            f"/vote/{prox_plain}",
            method="POST",
            data={f"amend_{amend.id}": "for"},
        ):
            voting.ballot_token(prox_plain)

        votes = Vote.query.all()
        assert len(votes) == 1
        assert votes[0].member_id == proxied.id

        with app.test_request_context(f"/vote/{self_plain}"):
            resp = voting.ballot_token(self_plain)
            assert resp[1] == 400


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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        a1 = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A1",
            order=2,
            status="carried",
            is_published=True,
        )
        a2 = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="A2",
            order=1,
            status="carried",
            is_published=True,
        )
        a3 = Amendment(
            meeting_id=meeting.id,
            motion_id=motion.id,
            text_md="X",
            order=3,
            status="failed",
            is_published=True,
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
                is_published=True,
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
            is_published=True,
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


def test_stage2_ballot_includes_carried_summary():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        db.session.add(
            Amendment(
                meeting_id=meeting.id,
                motion_id=motion.id,
                text_md="Add something important",
                order=1,
                status="carried",
                is_published=True,
            )
        )
        member = Member(meeting_id=meeting.id, name="A", email="a@e.co")
        db.session.add(member)
        db.session.flush()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()
        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert "Add something important" in html


def test_stage2_ballot_links_results_when_no_summary():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", public_results=True)
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
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
            assert "/results/" in html


def test_multiple_choice_motion_vote_and_receipt():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="Colour",
            text_md="Pick a colour",
            category="multiple_choice",
            threshold="plurality",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        opt1 = MotionOption(motion_id=motion.id, text="Red")
        opt2 = MotionOption(motion_id=motion.id, text="Blue")
        db.session.add_all([opt1, opt2])
        member = Member(meeting_id=meeting.id, name="A", email="a@e.co")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert f'value="{opt1.text}"' in html
            assert f'value="{opt2.text}"' in html
            assert "Abstain" in html

        with patch("app.voting.routes.send_vote_receipt") as mock_receipt:
            with app.test_request_context(
                f"/vote/{plain}",
                method="POST",
                data={f"motion_{motion.id}": opt2.text},
            ):
                voting.ballot_token(plain)
            mock_receipt.assert_called_once()
            vote_hashes = mock_receipt.call_args[0][2]
            vote = Vote.query.first()
            expected = hashlib.sha256(
                f"{member.id}{motion.id}2{opt2.text}{app.config['VOTE_SALT']}".encode()
            ).hexdigest()
            assert vote.choice == opt2.text
            assert vote.hash == expected
            assert vote.hash in vote_hashes
            assert token_obj.used_at is not None


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
            is_published=True,
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
            is_published=True,
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
            is_published=True,
        )
        db.session.add(motion)
        db.session.flush()
        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A1", order=1, status="carried", is_published=True)
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A2", order=2, status="carried", is_published=True)
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
            is_published=True,
        )
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A1", order=1, is_published=True)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert 'bp-stepper-current" aria-current="step" data-step="1"' in html
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
            is_published=True,
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
            assert 'bp-stepper-current" aria-current="step" data-step="2"' in html


def test_stepper_combined_ballot_single_label():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", ballot_mode="combined")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        amend = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A1", order=1, is_published=True)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with app.test_request_context(f"/vote/{plain}"):
            html = voting.ballot_token(plain)
            assert 'Combined Ballot' in html
            assert 'bp-stepper-current' in html
            assert 'data-step="1"' in html
            assert 'Stage 2' not in html


def test_verify_receipt_found():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        member = Member(meeting_id=meeting.id, name="A", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        vote = Vote.record(
            member_id=member.id,
            motion_id=motion.id,
            choice="for",
            salt=app.config["VOTE_SALT"],
        )
        vote_hash = vote.hash

    client = app.test_client()
    resp = client.post("/vote/verify-receipt", data={"hash": vote_hash})
    assert resp.status_code == 200
    assert b"Vote Details" in resp.data
    assert b"M1" in resp.data


def test_verify_receipt_not_found():
    app = _setup_app()
    with app.app_context():
        db.create_all()
    client = app.test_client()
    resp = client.post("/vote/verify-receipt", data={"hash": "bad"})
    assert resp.status_code == 200
    assert b"No vote found" in resp.data
    assert b"Contact support" in resp.data


def test_verify_receipt_multiple_matches():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        member = Member(meeting_id=meeting.id, name="A", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        Vote.record(
            member_id=member.id,
            motion_id=motion.id,
            choice="for",
            salt=app.config["VOTE_SALT"],
        )
        Vote.record(
            member_id=member.id,
            motion_id=motion.id,
            choice="for",
            salt=app.config["VOTE_SALT"],
        )
        vote_hash = hashlib.sha256(
            f"{member.id}{motion.id}for{app.config['VOTE_SALT']}".encode()
        ).hexdigest()

    client = app.test_client()
    resp = client.post("/vote/verify-receipt", data={"hash": vote_hash})
    assert resp.status_code == 200
    assert b"Multiple votes share this hash" in resp.data
    assert b"Contact support" in resp.data


def test_confirmation_shows_change_vote_link_when_revoting_enabled():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", revoting_allowed=True)
        db.session.add(meeting)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=None, text_md="A1", order=1, is_published=True)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with patch("app.voting.routes.send_vote_receipt"):
            with app.test_request_context(
                f"/vote/{plain}", method="POST", data={f"amend_{amend.id}": "for"}
            ):
                html = voting.ballot_token(plain)

        assert "Change your vote" in html
        assert f"/vote/{plain}" in html


def test_confirmation_hides_change_vote_link_when_disabled():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=None, text_md="A1", order=1, is_published=True)
        db.session.add(amend)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=1, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with patch("app.voting.routes.send_vote_receipt"):
            with app.test_request_context(
                f"/vote/{plain}", method="POST", data={f"amend_{amend.id}": "for"}
            ):
                html = voting.ballot_token(plain)

        assert "Change your vote" not in html


def test_second_submission_overwrites_first_when_revoting_allowed():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", revoting_allowed=True)
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with patch("app.voting.routes.send_vote_receipt"):
            with app.test_request_context(
                f"/vote/{plain}", method="POST", data={f"motion_{motion.id}": "for"}
            ):
                voting.ballot_token(plain)

            with app.test_request_context(
                f"/vote/{plain}", method="POST", data={f"motion_{motion.id}": "against"}
            ):
                voting.ballot_token(plain)

        votes = Vote.query.filter_by(member_id=member.id, motion_id=motion.id).all()
        assert len(votes) == 1
        assert votes[0].choice == "against"


def test_confirmation_links_to_public_results_after_stage2():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM", public_results=True, status="Completed")
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion text",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        member = Member(meeting_id=meeting.id, name="Alice", email="a@example.com")
        db.session.add(member)
        db.session.commit()
        token_obj, plain = VoteToken.create(member_id=member.id, stage=2, salt=app.config["TOKEN_SALT"])
        db.session.commit()

        with patch("app.voting.routes.send_vote_receipt"):
            with app.test_request_context(
                f"/vote/{plain}", method="POST", data={f"motion_{motion.id}": "for"}
            ):
                html = voting.ballot_token(plain)

        assert f"href=\"/results/{meeting.id}\"" in html
        assert "View results" in html


def _make_admin_user():
    perm = Permission(name="manage_meetings")
    role = Role(permissions=[perm])
    user = User(role=role)
    user.email = "admin@example.com"
    user.is_active = True
    return user


def test_preview_ballot_token_requires_permission():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.commit()
        with app.test_request_context(f"/vote/preview?meeting_id={meeting.id}&stage=1"):
            anon = AnonymousUserMixin()
            with patch("flask_login.utils._get_user", return_value=anon):
                with pytest.raises(Forbidden):
                    voting.ballot_token("preview")


def test_preview_ballot_token_renders_stage():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="Motion",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        db.session.commit()
        with app.test_request_context(f"/vote/preview?meeting_id={meeting.id}&stage=2"):
            user = _make_admin_user()
            with patch("flask_login.utils._get_user", return_value=user):
                html = voting.ballot_token("preview")
                assert "Stage 2" in html


def test_preview_runoff_ballot():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        meeting = Meeting(
            title="AGM",
            runoff_opens_at=now,
            runoff_closes_at=now + timedelta(hours=1),
        )
        db.session.add(meeting)
        motion = Motion(
            meeting_id=meeting.id,
            title="M",
            text_md="x",
            category="motion",
            threshold="normal",
            ordering=1,
            is_published=True,
        )
        db.session.add(motion)
        a1 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A1", order=1, is_published=True)
        a2 = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md="A2", order=2, is_published=True)
        db.session.add_all([a1, a2])
        db.session.flush()
        db.session.add(Runoff(meeting_id=meeting.id, amendment_a_id=a1.id, amendment_b_id=a2.id))
        db.session.commit()
        with app.test_request_context(f"/vote/runoff/preview?meeting_id={meeting.id}"):
            user = _make_admin_user()
            with patch("flask_login.utils._get_user", return_value=user):
                html = voting.runoff_ballot("preview")
                assert "Run-off Vote" in html

