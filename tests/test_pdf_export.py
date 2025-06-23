from dataclasses import dataclass
import pytest

from werkzeug.exceptions import NotFound

from app.utils import generate_results_pdf
from app import create_app, routes as main
from app.extensions import db
from app.models import Meeting, Amendment, Motion, Member, Vote


def test_generate_results_pdf_starts_with_pdf_header():
    @dataclass
    class Amend:
        text_md: str

    @dataclass
    class Mot:
        title: str
        status: str

    meeting = type("M", (), {"title": "AGM"})()
    amendments = [(Amend("A1"), {"for": 1, "against": 0, "abstain": 0})]
    motions = [(Mot("M1", "carried"), {"for": 1, "against": 0, "abstain": 0})]

    pdf = generate_results_pdf(meeting, amendments, motions)
    assert pdf.startswith(b"%PDF")


def _setup_app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["VOTE_SALT"] = "s"
    return app


import werkzeug.utils


@pytest.mark.parametrize(
    "title",
    [
        "AGM",
        "O'Connor's AGM",
        '"Quote" Meeting',
        "Line\nBreak",
    ],
)
def test_public_results_pdf_route(title):
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title=title)
        db.session.add(meeting)
        db.session.commit()

        with app.test_request_context(f"/results/{meeting.id}/final.pdf"):
            with pytest.raises(NotFound):
                main.public_results_pdf(meeting.id)

        meeting.public_results = True
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name="Alice")
        db.session.add(member)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, text_md="A1", order=1)
        motion = Motion(
            meeting_id=meeting.id,
            title="M1",
            text_md="T",
            category="motion",
            threshold="normal",
            ordering=1,
            status="carried",
        )
        db.session.add_all([amend, motion])
        db.session.commit()
        Vote.record(member_id=member.id, amendment_id=amend.id, choice="for", salt="s")
        Vote.record(member_id=member.id, motion_id=motion.id, choice="for", salt="s")

        with app.test_request_context(f"/results/{meeting.id}/final.pdf"):
            resp = main.public_results_pdf(meeting.id)
            assert resp.mimetype == "application/pdf"
            cd = resp.headers["Content-Disposition"]
            safe = werkzeug.utils.secure_filename(title)
            assert f"{safe}_final_results.pdf" in cd
            resp.direct_passthrough = False
            data = resp.get_data()
            assert data.startswith(b"%PDF")

